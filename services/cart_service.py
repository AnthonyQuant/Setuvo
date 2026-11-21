"""services/cart_service.py

Session-backed Shopping Cart, Nigerian delivery zone fee calculator, and
Wishlist service for Setuvo. Enforces live SQLite stock limits on every
cart mutation and reconciles quantities prior to checkout.
"""

from collections.abc import MutableMapping
from typing import Any, Dict, List, Optional, Sequence

from config import Config
from database.db_manager import DatabaseManager
from models.entities import CartItem, Product, format_naira
from services.exceptions import (
    InsufficientStockError,
    OutOfStockError,
    ProductNotFoundError,
    ValidationError,
)
from services.product_service import ProductService

SessionStore = MutableMapping[str, Any]


def _mark_modified(session_store: SessionStore) -> None:
    """Marks a Flask session dictionary as modified when supported."""
    if hasattr(session_store, "modified"):
        setattr(session_store, "modified", True)


class CartService:
    """Manages session cart state, delivery zone fees, and session wishlist."""

    CART_KEY: str = "setuvo_cart"
    WISHLIST_KEY: str = "setuvo_wishlist"
    ZONE_KEY: str = "setuvo_delivery_zone"
    DEFAULT_ZONE: str = "edo_local"

    def __init__(
        self,
        db_manager: DatabaseManager,
        product_service: Optional[ProductService] = None,
    ) -> None:
        self.db: DatabaseManager = db_manager
        self.product_service: ProductService = product_service or ProductService(db_manager)

    # ------------------------------------------------------------------
    # Nigerian Delivery Zone & Fee Helpers
    # ------------------------------------------------------------------
    def normalize_delivery_zone(self, zone: Optional[str]) -> str:
        """Returns a valid delivery zone key from Config.DELIVERY_ZONES."""
        clean = (zone or "").strip().lower()
        if clean in Config.DELIVERY_ZONES:
            return clean
        return self.DEFAULT_ZONE

    def get_delivery_zone(self, session_store: SessionStore) -> str:
        """Reads the active delivery zone from the session."""
        raw = session_store.get(self.ZONE_KEY)
        return self.normalize_delivery_zone(raw)

    def set_delivery_zone(self, session_store: SessionStore, zone: str) -> str:
        """Validates and stores the selected delivery zone in the session."""
        clean = (zone or "").strip().lower()
        if clean not in Config.DELIVERY_ZONES:
            raise ValidationError(f"Unsupported delivery zone: '{zone}'.")
        session_store[self.ZONE_KEY] = clean
        _mark_modified(session_store)
        return clean

    def get_delivery_fee(self, zone: Optional[str]) -> float:
        """Returns the NGN shipping fee for a delivery zone."""
        zone_key = self.normalize_delivery_zone(zone)
        return round(float(Config.DELIVERY_ZONES[zone_key]["fee"]), 2)

    def get_delivery_zone_options(self) -> List[Dict[str, Any]]:
        """Returns ordered Nigerian delivery zones with formatted Naira fees."""
        options: List[Dict[str, Any]] = []
        for slug, meta in Config.DELIVERY_ZONES.items():
            fee = round(float(meta["fee"]), 2)
            options.append(
                {
                    "slug": slug,
                    "label": str(meta["label"]),
                    "fee": fee,
                    "formatted_fee": "Free" if fee == 0 else format_naira(fee),
                    "eta": str(meta["eta"]),
                }
            )
        return options

    # ------------------------------------------------------------------
    # Internal Raw Cart Helpers
    # ------------------------------------------------------------------
    def _get_raw_cart(self, session_store: SessionStore) -> Dict[str, int]:
        raw = session_store.get(self.CART_KEY)
        if not isinstance(raw, dict):
            raw = {}
            session_store[self.CART_KEY] = raw
        cleaned: Dict[str, int] = {}
        for k, v in raw.items():
            try:
                pid = int(k)
                qty = int(v)
                if pid > 0 and qty > 0:
                    cleaned[str(pid)] = qty
            except (TypeError, ValueError):
                continue
        return cleaned

    def _save_raw_cart(
        self, session_store: SessionStore, cart_map: Dict[str, int]
    ) -> None:
        session_store[self.CART_KEY] = dict(cart_map)
        _mark_modified(session_store)

    # ------------------------------------------------------------------
    # Shopping Cart Mutations & Stock Enforcement
    # ------------------------------------------------------------------
    def add_item(
        self,
        session_store: SessionStore,
        product_id: int,
        quantity: int = 1,
    ) -> Dict[str, Any]:
        """Adds quantity of a product to the session cart after checking live stock."""
        try:
            qty_to_add = int(quantity)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Quantity must be a positive whole number.") from exc

        if qty_to_add <= 0:
            raise ValidationError("Quantity to add must be at least 1.")

        product = self.product_service.get_product_by_id(
            int(product_id), include_inactive=False
        )
        if not product.is_available:
            raise OutOfStockError(product.name, product.sku)

        cart_map = self._get_raw_cart(session_store)
        key = str(product.id)
        existing_qty = int(cart_map.get(key, 0))
        new_qty = existing_qty + qty_to_add

        if new_qty > product.stock:
            raise InsufficientStockError(
                product_name=product.name,
                requested=new_qty,
                available=product.stock,
                sku=product.sku,
            )

        cart_map[key] = new_qty
        self._save_raw_cart(session_store, cart_map)
        return self.get_cart_summary(session_store)

    def add_multiple_items(
        self,
        session_store: SessionStore,
        product_ids: Sequence[int],
        quantity_each: int = 1,
    ) -> Dict[str, Any]:
        """Atomically validates and adds multiple products (e.g., from Setup Builder)."""
        if quantity_each <= 0:
            raise ValidationError("Quantity must be at least 1.")

        ordered_ids: List[int] = []
        for raw_id in product_ids:
            try:
                pid = int(raw_id)
                if pid > 0 and pid not in ordered_ids:
                    ordered_ids.append(pid)
            except (TypeError, ValueError):
                continue

        if not ordered_ids:
            raise ValidationError("No valid products were selected to add to cart.")

        products = self.product_service.get_products_by_ids(
            ordered_ids, include_inactive=False
        )
        by_id = {p.id: p for p in products}
        if len(by_id) != len(ordered_ids):
            missing = next(pid for pid in ordered_ids if pid not in by_id)
            raise ProductNotFoundError(identifier=str(missing))

        cart_map = self._get_raw_cart(session_store)
        planned_map = dict(cart_map)

        # Validate all items first so a stock failure leaves the cart untouched
        for pid in ordered_ids:
            prod = by_id[pid]
            if not prod.is_available:
                raise OutOfStockError(prod.name, prod.sku)
            target_qty = int(planned_map.get(str(pid), 0)) + int(quantity_each)
            if target_qty > prod.stock:
                raise InsufficientStockError(
                    product_name=prod.name,
                    requested=target_qty,
                    available=prod.stock,
                    sku=prod.sku,
                )
            planned_map[str(pid)] = target_qty

        self._save_raw_cart(session_store, planned_map)
        return self.get_cart_summary(session_store)

    def update_item_quantity(
        self,
        session_store: SessionStore,
        product_id: int,
        quantity: int,
    ) -> Dict[str, Any]:
        """Updates an existing cart item's quantity, or removes it if quantity <= 0."""
        try:
            clean_qty = int(quantity)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Quantity must be a valid integer.") from exc

        pid = int(product_id)
        if clean_qty <= 0:
            self.remove_item(session_store, pid)
            return self.get_cart_summary(session_store)

        product = self.product_service.get_product_by_id(pid, include_inactive=False)
        if not product.is_available:
            self.remove_item(session_store, pid)
            raise OutOfStockError(product.name, product.sku)

        if clean_qty > product.stock:
            raise InsufficientStockError(
                product_name=product.name,
                requested=clean_qty,
                available=product.stock,
                sku=product.sku,
            )

        cart_map = self._get_raw_cart(session_store)
        cart_map[str(pid)] = clean_qty
        self._save_raw_cart(session_store, cart_map)
        return self.get_cart_summary(session_store)

    def remove_item(self, session_store: SessionStore, product_id: int) -> bool:
        """Removes a product line from the session cart."""
        cart_map = self._get_raw_cart(session_store)
        key = str(int(product_id))
        if key in cart_map:
            del cart_map[key]
            self._save_raw_cart(session_store, cart_map)
            return True
        return False

    def clear_cart(self, session_store: SessionStore) -> None:
        """Empties all items from the session cart."""
        session_store[self.CART_KEY] = {}
        _mark_modified(session_store)

    def get_cart_count(self, session_store: SessionStore) -> int:
        """Returns total unit count currently stored in the cart."""
        cart_map = self._get_raw_cart(session_store)
        return sum(cart_map.values())

    def get_cart_summary(
        self,
        session_store: SessionStore,
        delivery_zone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Builds a reconciled cart summary with live stock, subtotals, and delivery fees."""
        if delivery_zone is not None:
            active_zone = self.set_delivery_zone(session_store, delivery_zone)
        else:
            active_zone = self.get_delivery_zone(session_store)

        zone_meta = Config.DELIVERY_ZONES[active_zone]
        cart_map = self._get_raw_cart(session_store)

        ordered_ids = [int(k) for k in cart_map.keys()]
        products = self.product_service.get_products_by_ids(
            ordered_ids, include_inactive=False
        )
        by_id = {p.id: p for p in products}

        reconciled_map: Dict[str, int] = {}
        cart_items: List[CartItem] = []
        adjustment_notices: List[str] = []
        mutated = False

        for pid in ordered_ids:
            requested_qty = cart_map[str(pid)]
            product = by_id.get(pid)
            if product is None or not product.is_available:
                mutated = True
                if product is not None:
                    adjustment_notices.append(
                        f"'{product.name}' went out of stock and was removed from your cart."
                    )
                continue

            if requested_qty > product.stock:
                mutated = True
                final_qty = product.stock
                adjustment_notices.append(
                    f"Adjusted '{product.name}' quantity from {requested_qty} to "
                    f"{final_qty} based on available stock."
                )
            else:
                final_qty = requested_qty

            reconciled_map[str(pid)] = final_qty
            cart_items.append(CartItem(product=product, quantity=final_qty))

        if mutated:
            self._save_raw_cart(session_store, reconciled_map)

        subtotal = round(sum(item.line_total for item in cart_items), 2)
        delivery_fee = round(float(zone_meta["fee"]), 2) if cart_items else 0.0
        total_amount = round(subtotal + delivery_fee, 2)
        total_units = sum(item.quantity for item in cart_items)

        return {
            "items": [item.to_dict() for item in cart_items],
            "cart_item_objects": cart_items,
            "is_empty": len(cart_items) == 0,
            "distinct_items": len(cart_items),
            "total_units": total_units,
            "subtotal": subtotal,
            "formatted_subtotal": format_naira(subtotal),
            "delivery_zone": active_zone,
            "delivery_zone_label": str(zone_meta["label"]),
            "delivery_eta": str(zone_meta["eta"]),
            "delivery_fee": delivery_fee,
            "formatted_delivery_fee": "Free" if delivery_fee == 0 else format_naira(delivery_fee),
            "total_amount": total_amount,
            "formatted_total_amount": format_naira(total_amount),
            "adjustment_notices": adjustment_notices,
        }

    # ------------------------------------------------------------------
    # Session-Backed Wishlist Management
    # ------------------------------------------------------------------
    def get_wishlist_ids(self, session_store: SessionStore) -> List[int]:
        """Returns deduplicated product IDs saved in the visitor's session wishlist."""
        raw = session_store.get(self.WISHLIST_KEY)
        if not isinstance(raw, list):
            return []
        ids: List[int] = []
        for entry in raw:
            try:
                pid = int(entry)
                if pid > 0 and pid not in ids:
                    ids.append(pid)
            except (TypeError, ValueError):
                continue
        return ids

    def _save_wishlist_ids(
        self, session_store: SessionStore, ids: List[int]
    ) -> None:
        session_store[self.WISHLIST_KEY] = list(ids)
        _mark_modified(session_store)

    def get_wishlist_count(self, session_store: SessionStore) -> int:
        return len(self.get_wishlist_ids(session_store))

    def is_in_wishlist(self, session_store: SessionStore, product_id: int) -> bool:
        return int(product_id) in self.get_wishlist_ids(session_store)

    def add_to_wishlist(self, session_store: SessionStore, product_id: int) -> bool:
        """Saves an active product to the session wishlist. Returns True if newly added."""
        product = self.product_service.get_product_by_id(
            int(product_id), include_inactive=False
        )
        ids = self.get_wishlist_ids(session_store)
        if product.id in ids:
            return False
        ids.append(product.id)
        self._save_wishlist_ids(session_store, ids)
        return True

    def remove_from_wishlist(self, session_store: SessionStore, product_id: int) -> bool:
        """Removes a product ID from the session wishlist."""
        pid = int(product_id)
        ids = self.get_wishlist_ids(session_store)
        if pid in ids:
            ids.remove(pid)
            self._save_wishlist_ids(session_store, ids)
            return True
        return False

    def toggle_wishlist(self, session_store: SessionStore, product_id: int) -> bool:
        """Toggles a product in the wishlist; returns True if saved, False if removed."""
        pid = int(product_id)
        if self.is_in_wishlist(session_store, pid):
            self.remove_from_wishlist(session_store, pid)
            return False
        self.add_to_wishlist(session_store, pid)
        return True

    def get_wishlist_products(self, session_store: SessionStore) -> List[Product]:
        """Returns active Product objects currently saved in the session wishlist."""
        ids = self.get_wishlist_ids(session_store)
        if not ids:
            return []
        products = self.product_service.get_products_by_ids(ids, include_inactive=False)
        valid_ids = [p.id for p in products]
        if valid_ids != ids:
            self._save_wishlist_ids(session_store, valid_ids)
        return products

    def move_wishlist_to_cart(
        self, session_store: SessionStore, product_id: int
    ) -> Dict[str, Any]:
        """Adds 1 unit of a wishlisted product to the cart and removes it from wishlist."""
        pid = int(product_id)
        summary = self.add_item(session_store, pid, quantity=1)
        self.remove_from_wishlist(session_store, pid)
        return summary