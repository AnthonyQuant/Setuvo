"""services/inventory_service.py

Atomic inventory management, stock adjustment audit logging, low-stock
monitoring, and catalog administration service for Setuvo.
"""

import json
import sqlite3
from typing import Any, Dict, List, Mapping, Optional, Sequence

from config import Config
from database.db_manager import DatabaseManager
from models.entities import Product
from services.exceptions import (
    InsufficientStockError,
    OutOfStockError,
    ProductNotFoundError,
    ValidationError,
)


class InventoryService:
    """Manages atomic stock mutations, audit trails, and product availability."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db: DatabaseManager = db_manager

    # ------------------------------------------------------------------
    # Internal Audit & Row Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _log_adjustment(
        conn: sqlite3.Connection,
        product_id: int,
        change_amount: int,
        previous_stock: int,
        new_stock: int,
        reason: str,
        reference_code: str = "",
    ) -> None:
        conn.execute(
            """
            INSERT INTO stock_adjustments (
                product_id, change_amount, previous_stock, new_stock,
                reason, reference_code
            )
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                int(product_id),
                int(change_amount),
                int(previous_stock),
                int(new_stock),
                str(reason or "Stock adjustment").strip(),
                str(reference_code or "").strip(),
            ),
        )

    @staticmethod
    def _fetch_product_in_conn(
        conn: sqlite3.Connection, product_id: int
    ) -> Optional[sqlite3.Row]:
        return conn.execute(
            """
            SELECT
                p.*,
                c.name AS category_name,
                c.slug AS category_slug
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.id = ?;
            """,
            (int(product_id),),
        ).fetchone()

    # ------------------------------------------------------------------
    # Transactional Checkout & Cancellation Stock Hooks
    # ------------------------------------------------------------------
    def deduct_stock_in_transaction(
        self,
        conn: sqlite3.Connection,
        items: Sequence[Mapping[str, Any]],
        reference_code: str = "",
    ) -> List[Dict[str, Any]]:
        """Atomically verifies and deducts stock for order items inside an active transaction."""
        if not items:
            raise ValidationError("Cannot deduct stock for an empty item list.")

        # Aggregate quantities by product_id in case duplicate lines exist
        requested_by_id: Dict[int, int] = {}
        for entry in items:
            pid = int(entry["product_id"])
            qty = int(entry["quantity"])
            if qty <= 0:
                raise ValidationError("Item quantity must be at least 1.")
            requested_by_id[pid] = requested_by_id.get(pid, 0) + qty

        deductions: List[Dict[str, Any]] = []
        for pid, qty in requested_by_id.items():
            row = self._fetch_product_in_conn(conn, pid)
            if row is None or not bool(row["is_active"]):
                raise ProductNotFoundError(identifier=str(pid))

            product_name = str(row["name"])
            sku = str(row["sku"])
            current_stock = int(row["stock"])

            if current_stock <= 0:
                raise OutOfStockError(product_name=product_name, sku=sku)

            if qty > current_stock:
                raise InsufficientStockError(
                    product_name=product_name,
                    requested=qty,
                    available=current_stock,
                    sku=sku,
                )

            new_stock = current_stock - qty
            conn.execute(
                "UPDATE products SET stock = ? WHERE id = ?;",
                (new_stock, pid),
            )
            self._log_adjustment(
                conn=conn,
                product_id=pid,
                change_amount=-qty,
                previous_stock=current_stock,
                new_stock=new_stock,
                reason="Order checkout",
                reference_code=reference_code,
            )
            deductions.append(
                {
                    "product_id": pid,
                    "sku": sku,
                    "name": product_name,
                    "deducted": qty,
                    "previous_stock": current_stock,
                    "new_stock": new_stock,
                    "is_low_stock": 0 < new_stock <= Config.LOW_STOCK_THRESHOLD,
                }
            )

        return deductions

    def restore_stock_in_transaction(
        self,
        conn: sqlite3.Connection,
        items: Sequence[Mapping[str, Any]],
        reference_code: str = "",
    ) -> List[Dict[str, Any]]:
        """Restores stock quantities inside an active transaction when an order is cancelled."""
        restored: List[Dict[str, Any]] = []
        for entry in items:
            pid = int(entry["product_id"])
            qty = int(entry["quantity"])
            if qty <= 0:
                continue

            row = self._fetch_product_in_conn(conn, pid)
            if row is None:
                continue

            current_stock = int(row["stock"])
            new_stock = current_stock + qty
            conn.execute(
                "UPDATE products SET stock = ? WHERE id = ?;",
                (new_stock, pid),
            )
            self._log_adjustment(
                conn=conn,
                product_id=pid,
                change_amount=qty,
                previous_stock=current_stock,
                new_stock=new_stock,
                reason="Order cancelled restock",
                reference_code=reference_code,
            )
            restored.append(
                {
                    "product_id": pid,
                    "sku": str(row["sku"]),
                    "name": str(row["name"]),
                    "restored": qty,
                    "previous_stock": current_stock,
                    "new_stock": new_stock,
                }
            )
        return restored

    # ------------------------------------------------------------------
    # Standalone Administrative Stock & Catalog Operations
    # ------------------------------------------------------------------
    def adjust_stock(
        self,
        product_id: int,
        delta: int,
        reason: str = "Manual stock adjustment",
        reference_code: str = "",
    ) -> Dict[str, Any]:
        """Applies a signed stock delta (+restock or -writeoff) atomically with audit logging."""
        try:
            change = int(delta)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Stock adjustment delta must be a whole number.") from exc

        if change == 0:
            raise ValidationError("Stock adjustment delta cannot be zero.")

        with self.db.transaction() as conn:
            row = self._fetch_product_in_conn(conn, int(product_id))
            if row is None:
                raise ProductNotFoundError(identifier=str(product_id))

            previous_stock = int(row["stock"])
            new_stock = previous_stock + change
            if new_stock < 0:
                raise ValidationError(
                    f"Cannot reduce stock for '{row['name']}' below 0 "
                    f"(current stock: {previous_stock}, requested change: {change})."
                )

            conn.execute(
                "UPDATE products SET stock = ? WHERE id = ?;",
                (new_stock, int(product_id)),
            )
            self._log_adjustment(
                conn=conn,
                product_id=int(product_id),
                change_amount=change,
                previous_stock=previous_stock,
                new_stock=new_stock,
                reason=reason,
                reference_code=reference_code,
            )
            updated_row = self._fetch_product_in_conn(conn, int(product_id))

        product = Product.from_row(updated_row)  # type: ignore[arg-type]
        return {
            "product": product,
            "previous_stock": previous_stock,
            "change_amount": change,
            "new_stock": new_stock,
            "reason": reason,
        }

    def set_stock_level(
        self,
        product_id: int,
        new_stock: int,
        reason: str = "Physical stock reconciliation",
        reference_code: str = "",
    ) -> Dict[str, Any]:
        """Sets an exact non-negative stock quantity and records the delta."""
        try:
            target = int(new_stock)
        except (TypeError, ValueError) as exc:
            raise ValidationError("New stock quantity must be a whole number.") from exc

        if target < 0:
            raise ValidationError("Stock quantity cannot be negative.")

        with self.db.transaction() as conn:
            row = self._fetch_product_in_conn(conn, int(product_id))
            if row is None:
                raise ProductNotFoundError(identifier=str(product_id))

            previous_stock = int(row["stock"])
            delta = target - previous_stock
            conn.execute(
                "UPDATE products SET stock = ? WHERE id = ?;",
                (target, int(product_id)),
            )
            if delta != 0:
                self._log_adjustment(
                    conn=conn,
                    product_id=int(product_id),
                    change_amount=delta,
                    previous_stock=previous_stock,
                    new_stock=target,
                    reason=reason,
                    reference_code=reference_code,
                )
            updated_row = self._fetch_product_in_conn(conn, int(product_id))

        product = Product.from_row(updated_row)  # type: ignore[arg-type]
        return {
            "product": product,
            "previous_stock": previous_stock,
            "change_amount": delta,
            "new_stock": target,
            "reason": reason,
        }

    def update_product_price(self, product_id: int, new_price: float) -> Product:
        """Updates a product's catalogue price without altering historical order snapshots."""
        try:
            clean_price = round(float(new_price), 2)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Price must be a valid number in Naira.") from exc

        if clean_price <= 0:
            raise ValidationError("Product price must be greater than ₦0.00.")

        with self.db.transaction() as conn:
            row = self._fetch_product_in_conn(conn, int(product_id))
            if row is None:
                raise ProductNotFoundError(identifier=str(product_id))

            conn.execute(
                "UPDATE products SET price = ? WHERE id = ?;",
                (clean_price, int(product_id)),
            )
            updated_row = self._fetch_product_in_conn(conn, int(product_id))

        return Product.from_row(updated_row)  # type: ignore[arg-type]

    def set_product_active(self, product_id: int, is_active: bool) -> Product:
        """Activates or deactivates a product in the public storefront."""
        flag = 1 if bool(is_active) else 0
        with self.db.transaction() as conn:
            row = self._fetch_product_in_conn(conn, int(product_id))
            if row is None:
                raise ProductNotFoundError(identifier=str(product_id))

            conn.execute(
                "UPDATE products SET is_active = ? WHERE id = ?;",
                (flag, int(product_id)),
            )
            updated_row = self._fetch_product_in_conn(conn, int(product_id))

        return Product.from_row(updated_row)  # type: ignore[arg-type]

    def add_product(
        self,
        category_slug: str,
        sku: str,
        name: str,
        price: float,
        stock: int = 0,
        brand: str = "Setuvo Select",
        subcategory: str = "",
        description: str = "",
        specifications: Optional[Dict[str, Any]] = None,
        use_cases: Optional[Sequence[str]] = None,
        is_featured: bool = False,
        is_bestseller: bool = False,
    ) -> Product:
        """Creates a new catalog product and logs initial opening stock if > 0."""
        clean_sku = (sku or "").strip().upper()
        clean_name = (name or "").strip()
        clean_cat = (category_slug or "").strip().lower()

        if not clean_sku or not clean_name:
            raise ValidationError("Both product SKU and product name are required.")

        try:
            clean_price = round(float(price), 2)
            clean_stock = int(stock)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Price and stock must be valid numbers.") from exc

        if clean_price <= 0:
            raise ValidationError("Product price must be greater than ₦0.00.")
        if clean_stock < 0:
            raise ValidationError("Initial stock cannot be negative.")

        specs_json = json.dumps(specifications or {}, ensure_ascii=False)
        cases_str = (
            ",".join(str(c).strip() for c in use_cases if str(c).strip())
            if use_cases
            else "general_productivity"
        )

        with self.db.transaction() as conn:
            cat_row = conn.execute(
                "SELECT id FROM categories WHERE LOWER(slug) = ?;",
                (clean_cat,),
            ).fetchone()
            if cat_row is None:
                raise ValidationError(f"Unknown category slug: '{category_slug}'.")

            existing_sku = conn.execute(
                "SELECT id FROM products WHERE UPPER(sku) = ?;",
                (clean_sku,),
            ).fetchone()
            if existing_sku is not None:
                raise ValidationError(f"A product with SKU '{clean_sku}' already exists.")

            cur = conn.execute(
                """
                INSERT INTO products (
                    category_id, sku, name, brand, subcategory, description,
                    specifications_json, use_cases, price, stock,
                    is_featured, is_bestseller, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
                """,
                (
                    int(cat_row["id"]),
                    clean_sku,
                    clean_name,
                    (brand or "Setuvo Select").strip(),
                    (subcategory or "").strip(),
                    (description or "").strip(),
                    specs_json,
                    cases_str,
                    clean_price,
                    clean_stock,
                    1 if is_featured else 0,
                    1 if is_bestseller else 0,
                ),
            )
            new_id = int(cur.lastrowid)
            if clean_stock > 0:
                self._log_adjustment(
                    conn=conn,
                    product_id=new_id,
                    change_amount=clean_stock,
                    previous_stock=0,
                    new_stock=clean_stock,
                    reason="Initial opening stock",
                    reference_code=clean_sku,
                )
            created_row = self._fetch_product_in_conn(conn, new_id)

        return Product.from_row(created_row)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Low-Stock Alerts & Audit Trail Queries
    # ------------------------------------------------------------------
    def get_low_stock_products(
        self,
        threshold: Optional[int] = None,
        include_inactive: bool = False,
    ) -> List[Product]:
        """Returns products with stock > 0 and stock <= threshold, ordered lowest first."""
        limit_val = (
            Config.LOW_STOCK_THRESHOLD if threshold is None else max(0, int(threshold))
        )
        active_clause = "" if include_inactive else "AND p.is_active = 1"
        rows = self.db.fetch_all(
            f"""
            SELECT
                p.*,
                c.name AS category_name,
                c.slug AS category_slug
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.stock > 0 AND p.stock <= ? {active_clause}
            ORDER BY p.stock ASC, p.name ASC;
            """,
            (limit_val,),
        )
        return [Product.from_row(r) for r in rows]

    def get_out_of_stock_products(
        self, include_inactive: bool = False
    ) -> List[Product]:
        """Returns products currently at 0 stock."""
        active_clause = "" if include_inactive else "AND p.is_active = 1"
        rows = self.db.fetch_all(
            f"""
            SELECT
                p.*,
                c.name AS category_name,
                c.slug AS category_slug
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.stock = 0 {active_clause}
            ORDER BY p.name ASC;
            """
        )
        return [Product.from_row(r) for r in rows]

    def get_recent_adjustments(
        self, limit: int = 20, product_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Returns recent stock adjustment audit rows joined with product SKU and name."""
        params: List[Any] = []
        where_clause = ""
        if product_id is not None:
            where_clause = "WHERE sa.product_id = ?"
            params.append(int(product_id))

        params.append(max(1, int(limit)))
        rows = self.db.fetch_all(
            f"""
            SELECT
                sa.id,
                sa.product_id,
                p.sku,
                p.name AS product_name,
                sa.change_amount,
                sa.previous_stock,
                sa.new_stock,
                sa.reason,
                sa.reference_code,
                sa.created_at
            FROM stock_adjustments sa
            JOIN products p ON sa.product_id = p.id
            {where_clause}
            ORDER BY sa.id DESC
            LIMIT ?;
            """,
            params,
        )
        return [dict(r) for r in rows]