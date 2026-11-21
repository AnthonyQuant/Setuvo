"""models/entities.py

Object-oriented domain entities for Setuvo demonstrating inheritance
(CatalogItem -> Product, Bundle) alongside CartItem, OrderItem, and Order
models with Naira formatting, stock status badges, and SQLite row mapping.
"""

from abc import ABC, abstractmethod
import json
import sqlite3
from typing import Any, Dict, List, Mapping, Optional, Union

from config import Config

RowLike = Union[sqlite3.Row, Mapping[str, Any]]


def format_naira(amount: Optional[float]) -> str:
    """Formats a numeric amount in Nigerian Naira (e.g., ₦24,500.00)."""
    if amount is None:
        return f"{Config.CURRENCY_SYMBOL}0.00"
    return f"{Config.CURRENCY_SYMBOL}{float(amount):,.2f}"


class CatalogItem(ABC):
    """Abstract base class for sellable catalog entities (products and bundles)."""

    def __init__(
        self,
        item_id: int,
        name: str,
        description: str,
        price: float,
        is_active: bool = True,
    ) -> None:
        self.id: int = int(item_id)
        self.name: str = str(name).strip()
        self.description: str = str(description or "").strip()
        self._price: float = round(float(price), 2)
        self.is_active: bool = bool(is_active)

    @property
    def price(self) -> float:
        """Returns the effective unit price in NGN."""
        return self._price

    @property
    def formatted_price(self) -> str:
        """Returns the Naira-formatted price string."""
        return format_naira(self.price)

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Indicates whether the item is active and purchasable."""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serializes the entity into a template- and JSON-friendly dictionary."""


class Product(CatalogItem):
    """Represents a single workstation product in the Setuvo catalogue."""

    def __init__(
        self,
        item_id: int,
        category_id: int,
        sku: str,
        name: str,
        brand: str,
        subcategory: str,
        description: str,
        specifications: Dict[str, Any],
        use_cases: List[str],
        price: float,
        stock: int,
        image_url: str = "/static/images/product_placeholder.svg",
        is_featured: bool = False,
        is_bestseller: bool = False,
        is_active: bool = True,
        category_name: str = "",
        category_slug: str = "",
        created_at: str = "",
    ) -> None:
        super().__init__(
            item_id=item_id,
            name=name,
            description=description,
            price=price,
            is_active=is_active,
        )
        self.category_id: int = int(category_id)
        self.category_name: str = str(category_name or "").strip()
        self.category_slug: str = str(category_slug or "").strip()
        self.sku: str = str(sku).strip().upper()
        self.brand: str = str(brand or "Setuvo Select").strip()
        self.subcategory: str = str(subcategory or "").strip()
        self.specifications: Dict[str, Any] = dict(specifications or {})
        self.use_cases: List[str] = list(use_cases or [])
        self.stock: int = max(0, int(stock))
        self.image_url: str = (
            str(image_url or "").strip() or "/static/images/product_placeholder.svg"
        )
        self.is_featured: bool = bool(is_featured)
        self.is_bestseller: bool = bool(is_bestseller)
        self.created_at: str = str(created_at or "")

    @property
    def is_available(self) -> bool:
        return self.is_active and self.stock > 0

    @property
    def stock_status(self) -> str:
        """Returns customer-facing stock availability label."""
        if not self.is_active or self.stock <= 0:
            return "Out of stock"
        if self.stock <= Config.LOW_STOCK_THRESHOLD:
            return "Low stock"
        return "In stock"

    @property
    def stock_badge_class(self) -> str:
        """Returns semantic CSS modifier for stock indicator pills."""
        status = self.stock_status
        if status == "In stock":
            return "in-stock"
        if status == "Low stock":
            return "low-stock"
        return "out-of-stock"

    @classmethod
    def from_row(cls, row: RowLike) -> "Product":
        """Constructs a Product instance from a SQLite Row or dictionary."""
        data = dict(row)
        raw_specs = data.get("specifications_json") or "{}"
        if isinstance(raw_specs, dict):
            specs = raw_specs
        else:
            try:
                parsed = json.loads(str(raw_specs))
                specs = parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                specs = {}

        raw_cases = data.get("use_cases") or ""
        if isinstance(raw_cases, list):
            cases = [str(c).strip() for c in raw_cases if str(c).strip()]
        else:
            cases = [c.strip() for c in str(raw_cases).split(",") if c.strip()]

        return cls(
            item_id=int(data["id"]),
            category_id=int(data["category_id"]),
            sku=str(data["sku"]),
            name=str(data["name"]),
            brand=str(data.get("brand") or "Setuvo Select"),
            subcategory=str(data.get("subcategory") or ""),
            description=str(data.get("description") or ""),
            specifications=specs,
            use_cases=cases,
            price=float(data["price"]),
            stock=int(data.get("stock", 0)),
            image_url=str(
                data.get("image_url") or "/static/images/product_placeholder.svg"
            ),
            is_featured=bool(data.get("is_featured", 0)),
            is_bestseller=bool(data.get("is_bestseller", 0)),
            is_active=bool(data.get("is_active", 1)),
            category_name=str(data.get("category_name") or ""),
            category_slug=str(data.get("category_slug") or ""),
            created_at=str(data.get("created_at") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category_id": self.category_id,
            "category_name": self.category_name,
            "category_slug": self.category_slug,
            "sku": self.sku,
            "name": self.name,
            "brand": self.brand,
            "subcategory": self.subcategory,
            "description": self.description,
            "specifications": self.specifications,
            "use_cases": self.use_cases,
            "price": self.price,
            "formatted_price": self.formatted_price,
            "stock": self.stock,
            "stock_status": self.stock_status,
            "stock_badge_class": self.stock_badge_class,
            "is_available": self.is_available,
            "image_url": self.image_url,
            "is_featured": self.is_featured,
            "is_bestseller": self.is_bestseller,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


class Bundle(CatalogItem):
    """Represents a preconfigured workstation kit with automatic bundle savings."""

    def __init__(
        self,
        item_id: int,
        slug: str,
        name: str,
        purpose: str,
        description: str,
        discount_pct: float = 10.0,
        items: Optional[List[Dict[str, Any]]] = None,
        is_active: bool = True,
        created_at: str = "",
    ) -> None:
        self.slug: str = str(slug).strip().lower()
        self.purpose: str = str(purpose or "general_productivity").strip()
        self.discount_pct: float = max(0.0, min(90.0, float(discount_pct)))
        self.items: List[Dict[str, Any]] = list(items or [])
        self.created_at: str = str(created_at or "")

        super().__init__(
            item_id=item_id,
            name=name,
            description=description,
            price=self._compute_bundle_price(),
            is_active=is_active,
        )

    @property
    def individual_total(self) -> float:
        """Sum of component product prices multiplied by their bundle quantities."""
        total = 0.0
        for entry in self.items:
            product: Product = entry["product"]
            qty = int(entry.get("quantity", 1))
            total += product.price * qty
        return round(total, 2)

    def _compute_bundle_price(self) -> float:
        raw_total = self.individual_total
        discounted = raw_total * (1.0 - (self.discount_pct / 100.0))
        return round(discounted, 2)

    @property
    def price(self) -> float:
        """Returns the discounted bundle total in NGN."""
        return self._compute_bundle_price()

    @property
    def savings_amount(self) -> float:
        """Returns NGN saved compared to purchasing components individually."""
        return round(max(0.0, self.individual_total - self.price), 2)

    @property
    def is_available(self) -> bool:
        """True only when the bundle is active and every component has enough stock."""
        if not self.is_active or not self.items:
            return False
        for entry in self.items:
            product: Product = entry["product"]
            qty = int(entry.get("quantity", 1))
            if not product.is_active or product.stock < qty:
                return False
        return True

    @classmethod
    def from_row(
        cls,
        row: RowLike,
        items: Optional[List[Dict[str, Any]]] = None,
    ) -> "Bundle":
        data = dict(row)
        return cls(
            item_id=int(data["id"]),
            slug=str(data["slug"]),
            name=str(data["name"]),
            purpose=str(data.get("purpose") or "general_productivity"),
            description=str(data.get("description") or ""),
            discount_pct=float(data.get("discount_pct", 10.0)),
            items=items or [],
            is_active=bool(data.get("is_active", 1)),
            created_at=str(data.get("created_at") or ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        purpose_meta = Config.SETUP_PURPOSES.get(self.purpose, {})
        serialized_items = []
        for entry in self.items:
            prod: Product = entry["product"]
            qty = int(entry.get("quantity", 1))
            serialized_items.append(
                {
                    "product": prod.to_dict(),
                    "quantity": qty,
                    "line_total": round(prod.price * qty, 2),
                    "formatted_line_total": format_naira(prod.price * qty),
                }
            )

        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "purpose": self.purpose,
            "purpose_label": purpose_meta.get("label", self.purpose.replace("_", " ").title()),
            "description": self.description,
            "discount_pct": self.discount_pct,
            "individual_total": self.individual_total,
            "formatted_individual_total": format_naira(self.individual_total),
            "bundle_price": self.price,
            "formatted_bundle_price": self.formatted_price,
            "savings_amount": self.savings_amount,
            "formatted_savings": format_naira(self.savings_amount),
            "is_available": self.is_available,
            "is_active": self.is_active,
            "items": serialized_items,
            "item_count": len(serialized_items),
        }


class CartItem:
    """Represents a validated line item inside the customer's session shopping cart."""

    def __init__(self, product: Product, quantity: int) -> None:
        self.product: Product = product
        self.quantity: int = max(1, int(quantity))

    @property
    def line_total(self) -> float:
        return round(self.product.price * self.quantity, 2)

    @property
    def formatted_line_total(self) -> str:
        return format_naira(self.line_total)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product": self.product.to_dict(),
            "quantity": self.quantity,
            "unit_price": self.product.price,
            "formatted_unit_price": self.product.formatted_price,
            "line_total": self.line_total,
            "formatted_line_total": self.formatted_line_total,
            "max_available": self.product.stock,
        }


class OrderItem:
    """Represents a persisted order line item with its historical unit price snapshot."""

    def __init__(
        self,
        item_id: int,
        order_id: int,
        product_id: int,
        product_name: str,
        product_sku: str,
        quantity: int,
        unit_price: float,
        line_total: float,
    ) -> None:
        self.id: int = int(item_id)
        self.order_id: int = int(order_id)
        self.product_id: int = int(product_id)
        self.product_name: str = str(product_name)
        self.product_sku: str = str(product_sku)
        self.quantity: int = int(quantity)
        self.unit_price: float = round(float(unit_price), 2)
        self.line_total: float = round(float(line_total), 2)

    @classmethod
    def from_row(cls, row: RowLike) -> "OrderItem":
        data = dict(row)
        return cls(
            item_id=int(data["id"]),
            order_id=int(data["order_id"]),
            product_id=int(data["product_id"]),
            product_name=str(data["product_name"]),
            product_sku=str(data["product_sku"]),
            quantity=int(data["quantity"]),
            unit_price=float(data["unit_price"]),
            line_total=float(data["line_total"]),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "product_sku": self.product_sku,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "formatted_unit_price": format_naira(self.unit_price),
            "line_total": self.line_total,
            "formatted_line_total": format_naira(self.line_total),
        }


class Order:
    """Represents a persisted customer order and its fulfillment lifecycle state."""

    LIFECYCLE_STEPS: Dict[str, int] = {
        "Order placed": 1,
        "Processing": 2,
        "Shipped": 3,
        "Delivered": 4,
        "Cancelled": 0,
    }

    def __init__(
        self,
        order_id: int,
        order_number: str,
        customer_id: int,
        delivery_zone: str,
        delivery_address: str,
        subtotal: float,
        delivery_fee: float,
        total_amount: float,
        status: str = "Order placed",
        payment_method: str = "Pay on Delivery (Demo)",
        notes: str = "",
        created_at: str = "",
        updated_at: str = "",
        customer_name: str = "",
        customer_email: str = "",
        customer_phone: str = "",
        items: Optional[List[OrderItem]] = None,
    ) -> None:
        self.id: int = int(order_id)
        self.order_number: str = str(order_number).strip().upper()
        self.customer_id: int = int(customer_id)
        self.delivery_zone: str = str(delivery_zone).strip()
        self.delivery_address: str = str(delivery_address).strip()
        self.subtotal: float = round(float(subtotal), 2)
        self.delivery_fee: float = round(float(delivery_fee), 2)
        self.total_amount: float = round(float(total_amount), 2)
        self.status: str = str(status or "Order placed").strip()
        self.payment_method: str = str(payment_method or "Pay on Delivery (Demo)").strip()
        self.notes: str = str(notes or "").strip()
        self.created_at: str = str(created_at or "")
        self.updated_at: str = str(updated_at or "")
        self.customer_name: str = str(customer_name or "").strip()
        self.customer_email: str = str(customer_email or "").strip()
        self.customer_phone: str = str(customer_phone or "").strip()
        self.items: List[OrderItem] = list(items or [])

    @property
    def status_step(self) -> int:
        """Returns 1..4 for active fulfillment stages, or 0 if Cancelled."""
        return self.LIFECYCLE_STEPS.get(self.status, 1)

    @property
    def delivery_zone_label(self) -> str:
        zone = Config.DELIVERY_ZONES.get(self.delivery_zone)
        return str(zone["label"]) if zone else self.delivery_zone

    @property
    def delivery_eta(self) -> str:
        zone = Config.DELIVERY_ZONES.get(self.delivery_zone)
        return str(zone["eta"]) if zone else "2–4 business days"

    @classmethod
    def from_row(
        cls,
        row: RowLike,
        items: Optional[List[OrderItem]] = None,
    ) -> "Order":
        data = dict(row)
        return cls(
            order_id=int(data["id"]),
            order_number=str(data["order_number"]),
            customer_id=int(data["customer_id"]),
            delivery_zone=str(data["delivery_zone"]),
            delivery_address=str(data["delivery_address"]),
            subtotal=float(data["subtotal"]),
            delivery_fee=float(data["delivery_fee"]),
            total_amount=float(data["total_amount"]),
            status=str(data.get("status") or "Order placed"),
            payment_method=str(data.get("payment_method") or "Pay on Delivery (Demo)"),
            notes=str(data.get("notes") or ""),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            customer_name=str(data.get("full_name") or data.get("customer_name") or ""),
            customer_email=str(data.get("email") or data.get("customer_email") or ""),
            customer_phone=str(data.get("phone") or data.get("customer_phone") or ""),
            items=items or [],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order_number": self.order_number,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "customer_phone": self.customer_phone,
            "delivery_zone": self.delivery_zone,
            "delivery_zone_label": self.delivery_zone_label,
            "delivery_eta": self.delivery_eta,
            "delivery_address": self.delivery_address,
            "subtotal": self.subtotal,
            "formatted_subtotal": format_naira(self.subtotal),
            "delivery_fee": self.delivery_fee,
            "formatted_delivery_fee": format_naira(self.delivery_fee),
            "total_amount": self.total_amount,
            "formatted_total_amount": format_naira(self.total_amount),
            "status": self.status,
            "status_step": self.status_step,
            "payment_method": self.payment_method,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "items": [item.to_dict() for item in self.items],
        }