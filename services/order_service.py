"""services/order_service.py

Guest checkout processing, historical order-item price snapshot persistence,
atomic stock deduction, order tracking, and lifecycle status updates for Setuvo.
"""

from datetime import datetime, timezone
import secrets
import sqlite3
from typing import Any, Dict, List, Optional

from config import Config
from database.db_manager import DatabaseManager
from models.entities import Order, OrderItem
from services.cart_service import CartService, SessionStore
from services.email_service import EmailService
from services.exceptions import (
    EmptyCartError,
    OrderNotFoundError,
    ValidationError,
)
from services.inventory_service import InventoryService


class OrderService:
    """Coordinates guest checkout, order persistence, tracking, and status updates."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        cart_service: Optional[CartService] = None,
        inventory_service: Optional[InventoryService] = None,
        email_service: Optional[EmailService] = None,
    ) -> None:
        self.db: DatabaseManager = db_manager
        self.cart_service: CartService = cart_service or CartService(db_manager)
        self.inventory_service: InventoryService = (
            inventory_service or InventoryService(db_manager)
        )
        self.email_service: EmailService = email_service or EmailService()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _generate_unique_order_number(conn: sqlite3.Connection) -> str:
        """Generates a collision-free STV-YYYYMMDD-XXXX order reference."""
        date_stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        for _ in range(25):
            suffix = secrets.randbelow(9000) + 1000
            candidate = f"STV-{date_stamp}-{suffix}"
            existing = conn.execute(
                "SELECT id FROM orders WHERE order_number = ?;",
                (candidate,),
            ).fetchone()
            if existing is None:
                return candidate
        raise RuntimeError("Unable to generate a unique Setuvo order number.")

    @staticmethod
    def _validate_customer_payload(
        full_name: str,
        email: str,
        phone: str,
        address: str,
        delivery_zone: str,
    ) -> Dict[str, str]:
        clean_name = str(full_name or "").strip()
        clean_email = str(email or "").strip().lower()
        clean_phone = str(phone or "").strip()
        clean_address = str(address or "").strip()
        clean_zone = str(delivery_zone or "").strip().lower()

        if len(clean_name) < 2:
            raise ValidationError("Please enter your full name (at least 2 characters).")
        if "@" not in clean_email or "." not in clean_email.split("@")[-1]:
            raise ValidationError("Please enter a valid email address.")
        if len(clean_phone) < 7:
            raise ValidationError("Please enter a valid contact phone number.")
        if len(clean_address) < 5:
            raise ValidationError("Please enter a complete delivery street or campus address.")
        if clean_zone not in Config.DELIVERY_ZONES:
            raise ValidationError("Please select a valid Nigerian delivery zone.")

        return {
            "full_name": clean_name,
            "email": clean_email,
            "phone": clean_phone,
            "address": clean_address,
            "delivery_zone": clean_zone,
        }

    def _hydrate_order(
        self, order_row: sqlite3.Row, conn: Optional[sqlite3.Connection] = None
    ) -> Order:
        """Attaches OrderItem line snapshots to an Order row."""
        order_id = int(order_row["id"])
        query = """
            SELECT *
            FROM order_items
            WHERE order_id = ?
            ORDER BY id ASC;
        """
        if conn is not None:
            item_rows = conn.execute(query, (order_id,)).fetchall()
        else:
            item_rows = self.db.fetch_all(query, (order_id,))

        items = [OrderItem.from_row(r) for r in item_rows]
        return Order.from_row(order_row, items=items)

    def _fetch_order_row_in_conn(
        self, conn: sqlite3.Connection, order_number: str
    ) -> Optional[sqlite3.Row]:
        return conn.execute(
            """
            SELECT
                o.*,
                cu.full_name,
                cu.email,
                cu.phone
            FROM orders o
            JOIN customers cu ON o.customer_id = cu.id
            WHERE UPPER(o.order_number) = ?;
            """,
            (str(order_number or "").strip().upper(),),
        ).fetchone()

    # ------------------------------------------------------------------
    # Guest Checkout Execution
    # ------------------------------------------------------------------
    def place_guest_order(
        self,
        session_store: SessionStore,
        full_name: str,
        email: str,
        phone: str,
        address: str,
        delivery_zone: str,
        notes: str = "",
        payment_method: str = "Pay on Delivery (Demo)",
    ) -> Dict[str, Any]:
        """Validates cart & guest details, persists order + price snapshots, and deducts stock."""
        customer = self._validate_customer_payload(
            full_name=full_name,
            email=email,
            phone=phone,
            address=address,
            delivery_zone=delivery_zone,
        )
        clean_notes = str(notes or "").strip()
        clean_payment = (
            str(payment_method or "Pay on Delivery (Demo)").strip()
            or "Pay on Delivery (Demo)"
        )

        # Reconcile cart against active catalog and apply chosen delivery zone
        cart_summary = self.cart_service.get_cart_summary(
            session_store, delivery_zone=customer["delivery_zone"]
        )
        cart_items = cart_summary["cart_item_objects"]
        if not cart_items:
            raise EmptyCartError()

        zone_meta = Config.DELIVERY_ZONES[customer["delivery_zone"]]
        delivery_fee = round(float(zone_meta["fee"]), 2)
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        with self.db.transaction() as conn:
            order_number = self._generate_unique_order_number(conn)

            # Re-read live product prices inside the transaction for exact snapshot integrity
            snapshot_lines: List[Dict[str, Any]] = []
            subtotal = 0.0
            for cart_item in cart_items:
                prod_row = conn.execute(
                    "SELECT id, sku, name, price FROM products WHERE id = ?;",
                    (cart_item.product.id,),
                ).fetchone()
                if prod_row is None:
                    raise ValidationError(
                        f"Product '{cart_item.product.name}' is no longer available."
                    )
                unit_price = round(float(prod_row["price"]), 2)
                qty = int(cart_item.quantity)
                line_total = round(unit_price * qty, 2)
                subtotal = round(subtotal + line_total, 2)
                snapshot_lines.append(
                    {
                        "product_id": int(prod_row["id"]),
                        "product_sku": str(prod_row["sku"]),
                        "product_name": str(prod_row["name"]),
                        "quantity": qty,
                        "unit_price": unit_price,
                        "line_total": line_total,
                    }
                )

            # Atomically verify and reduce inventory before recording order
            self.inventory_service.deduct_stock_in_transaction(
                conn=conn,
                items=snapshot_lines,
                reference_code=order_number,
            )

            cust_cur = conn.execute(
                """
                INSERT INTO customers (
                    full_name, email, phone, address, delivery_zone, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    customer["full_name"],
                    customer["email"],
                    customer["phone"],
                    customer["address"],
                    customer["delivery_zone"],
                    now_ts,
                ),
            )
            customer_id = int(cust_cur.lastrowid)

            total_amount = round(subtotal + delivery_fee, 2)
            order_cur = conn.execute(
                """
                INSERT INTO orders (
                    order_number, customer_id, delivery_zone, delivery_address,
                    subtotal, delivery_fee, total_amount, status,
                    payment_method, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Order placed', ?, ?, ?, ?);
                """,
                (
                    order_number,
                    customer_id,
                    customer["delivery_zone"],
                    customer["address"],
                    subtotal,
                    delivery_fee,
                    total_amount,
                    clean_payment,
                    clean_notes,
                    now_ts,
                    now_ts,
                ),
            )
            order_id = int(order_cur.lastrowid)

            for line in snapshot_lines:
                conn.execute(
                    """
                    INSERT INTO order_items (
                        order_id, product_id, product_name, product_sku,
                        quantity, unit_price, line_total
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        order_id,
                        line["product_id"],
                        line["product_name"],
                        line["product_sku"],
                        line["quantity"],
                        line["unit_price"],
                        line["line_total"],
                    ),
                )

            saved_row = self._fetch_order_row_in_conn(conn, order_number)
            order = self._hydrate_order(saved_row, conn=conn)  # type: ignore[arg-type]

        # Clear session cart after SQLite commit succeeds
        self.cart_service.clear_cart(session_store)

        # Dispatch confirmation emails non-fatally
        email_result = self.email_service.send_order_notifications(
            order, raise_on_error=False
        )

        return {
            "order": order,
            "email_result": email_result,
        }

    # ------------------------------------------------------------------
    # Customer Order Tracking & Administrative Queries
    # ------------------------------------------------------------------
    def track_order(self, order_number: str, email: str) -> Order:
        """Retrieves an Order matching both order number and customer email address."""
        clean_number = str(order_number or "").strip().upper()
        clean_email = str(email or "").strip().lower()

        if not clean_number or not clean_email:
            raise ValidationError(
                "Please enter both your order number and email address."
            )

        row = self.db.fetch_one(
            """
            SELECT
                o.*,
                cu.full_name,
                cu.email,
                cu.phone
            FROM orders o
            JOIN customers cu ON o.customer_id = cu.id
            WHERE UPPER(o.order_number) = ?
              AND LOWER(cu.email) = ?;
            """,
            (clean_number, clean_email),
        )
        if row is None:
            raise OrderNotFoundError(order_number=clean_number)

        return self._hydrate_order(row)

    def get_order_by_number(self, order_number: str) -> Order:
        """Fetches any order by order number (for confirmation pages and admin CLI)."""
        clean_number = str(order_number or "").strip().upper()
        if not clean_number:
            raise OrderNotFoundError(order_number="")

        row = self.db.fetch_one(
            """
            SELECT
                o.*,
                cu.full_name,
                cu.email,
                cu.phone
            FROM orders o
            JOIN customers cu ON o.customer_id = cu.id
            WHERE UPPER(o.order_number) = ?;
            """,
            (clean_number,),
        )
        if row is None:
            raise OrderNotFoundError(order_number=clean_number)

        return self._hydrate_order(row)

    def get_all_orders(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[Order]:
        """Returns orders ordered newest first, optionally filtered by status."""
        params: List[Any] = []
        where_clause = ""
        clean_status = (status or "").strip()
        if clean_status and clean_status.lower() != "all":
            where_clause = "WHERE o.status = ?"
            params.append(clean_status)

        params.append(max(1, int(limit)))
        rows = self.db.fetch_all(
            f"""
            SELECT
                o.*,
                cu.full_name,
                cu.email,
                cu.phone
            FROM orders o
            JOIN customers cu ON o.customer_id = cu.id
            {where_clause}
            ORDER BY o.created_at DESC, o.id DESC
            LIMIT ?;
            """,
            params,
        )
        return [self._hydrate_order(row) for row in rows]

    def update_order_status(self, order_number: str, new_status: str) -> Order:
        """Updates an order's lifecycle status and restocks inventory if cancelled."""
        clean_number = str(order_number or "").strip().upper()
        clean_status = str(new_status or "").strip()

        if clean_status not in Config.ORDER_STATUSES:
            raise ValidationError(
                f"Invalid order status '{clean_status}'. Valid statuses: "
                f"{', '.join(Config.ORDER_STATUSES)}."
            )

        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        with self.db.transaction() as conn:
            row = self._fetch_order_row_in_conn(conn, clean_number)
            if row is None:
                raise OrderNotFoundError(order_number=clean_number)

            current_status = str(row["status"])
            if current_status == clean_status:
                return self._hydrate_order(row, conn=conn)

            if current_status == "Cancelled" and clean_status != "Cancelled":
                raise ValidationError(
                    "Cancelled orders cannot be reopened after inventory has been restocked."
                )

            if clean_status == "Cancelled" and current_status != "Cancelled":
                item_rows = conn.execute(
                    "SELECT product_id, quantity FROM order_items WHERE order_id = ?;",
                    (int(row["id"]),),
                ).fetchall()
                self.inventory_service.restore_stock_in_transaction(
                    conn=conn,
                    items=[dict(r) for r in item_rows],
                    reference_code=clean_number,
                )

            conn.execute(
                """
                UPDATE orders
                SET status = ?, updated_at = ?
                WHERE id = ?;
                """,
                (clean_status, now_ts, int(row["id"])),
            )
            updated_row = self._fetch_order_row_in_conn(conn, clean_number)
            return self._hydrate_order(updated_row, conn=conn)  # type: ignore[arg-type]