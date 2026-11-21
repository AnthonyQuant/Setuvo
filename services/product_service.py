"""services/product_service.py

Catalogue discovery, multi-criteria search, filtering, sorting,
side-by-side specification comparison, and related-product recommendation
service for Setuvo.
"""

from typing import Any, Dict, List, Optional, Sequence

from config import Config
from database.db_manager import DatabaseManager
from models.entities import Product
from services.exceptions import ProductNotFoundError, ValidationError


def _escape_like(term: str) -> str:
    """Escapes SQL LIKE wildcard characters so user searches behave literally."""
    return (
        term.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


class ProductService:
    """Encapsulates SQLite queries and Python matching logic for Setuvo products."""

    SORT_OPTIONS: Dict[str, str] = {
        "featured": "Curated Featured",
        "price_asc": "Price: Lowest to Highest",
        "price_desc": "Price: Highest to Lowest",
        "newest": "Recently Added",
        "popular": "Most Popular",
        "bestselling": "Bestselling",
    }

    # Complementary category affinities for workstation cross-recommendations
    COMPLEMENTARY_CATEGORIES: Dict[str, List[str]] = {
        "laptop-stands-cooling": [
            "keyboards-mice",
            "storage-connectivity",
            "desk-essentials",
        ],
        "keyboards-mice": [
            "laptop-stands-cooling",
            "desk-essentials",
            "storage-connectivity",
        ],
        "headphones-audio": [
            "computer-accessories",
            "study-productivity",
            "desk-essentials",
        ],
        "storage-connectivity": [
            "laptop-stands-cooling",
            "keyboards-mice",
            "computer-accessories",
        ],
        "study-productivity": [
            "laptop-stands-cooling",
            "headphones-audio",
            "desk-essentials",
        ],
        "desk-essentials": [
            "keyboards-mice",
            "laptop-stands-cooling",
            "computer-accessories",
        ],
        "computer-accessories": [
            "storage-connectivity",
            "desk-essentials",
            "headphones-audio",
        ],
    }

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db: DatabaseManager = db_manager

    # ------------------------------------------------------------------
    # Category & Filter Metadata Queries
    # ------------------------------------------------------------------
    def get_categories(self, include_empty: bool = True) -> List[Dict[str, Any]]:
        """Returns all product categories ordered for navigation with active item counts."""
        rows = self.db.fetch_all(
            """
            SELECT
                c.id,
                c.slug,
                c.name,
                c.description,
                c.display_order,
                COUNT(p.id) AS product_count
            FROM categories c
            LEFT JOIN products p
                ON p.category_id = c.id AND p.is_active = 1
            GROUP BY c.id, c.slug, c.name, c.description, c.display_order
            ORDER BY c.display_order ASC, c.name ASC;
            """
        )
        results = [dict(row) for row in rows]
        if not include_empty:
            results = [r for r in results if int(r["product_count"]) > 0]
        return results

    def get_filter_options(self) -> Dict[str, Any]:
        """Returns distinct brands, subcategories, price bounds, and sort choices."""
        brand_rows = self.db.fetch_all(
            """
            SELECT DISTINCT brand
            FROM products
            WHERE is_active = 1 AND TRIM(brand) != ''
            ORDER BY brand ASC;
            """
        )
        type_rows = self.db.fetch_all(
            """
            SELECT DISTINCT subcategory
            FROM products
            WHERE is_active = 1 AND TRIM(subcategory) != ''
            ORDER BY subcategory ASC;
            """
        )
        bounds_row = self.db.fetch_one(
            """
            SELECT
                COALESCE(MIN(price), 0) AS min_price,
                COALESCE(MAX(price), 0) AS max_price
            FROM products
            WHERE is_active = 1;
            """
        )
        return {
            "categories": self.get_categories(include_empty=True),
            "brands": [str(r["brand"]) for r in brand_rows],
            "product_types": [str(r["subcategory"]) for r in type_rows],
            "min_price": float(bounds_row["min_price"]) if bounds_row else 0.0,
            "max_price": float(bounds_row["max_price"]) if bounds_row else 0.0,
            "sort_options": self.SORT_OPTIONS,
        }

    # ------------------------------------------------------------------
    # Single & Batch Product Lookups
    # ------------------------------------------------------------------
    def get_product_by_id(
        self, product_id: int, include_inactive: bool = False
    ) -> Product:
        """Fetches a single Product by primary key ID or raises ProductNotFoundError."""
        active_clause = "" if include_inactive else "AND p.is_active = 1"
        row = self.db.fetch_one(
            f"""
            SELECT
                p.*,
                c.name AS category_name,
                c.slug AS category_slug
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.id = ? {active_clause};
            """,
            (int(product_id),),
        )
        if row is None:
            raise ProductNotFoundError(identifier=str(product_id))
        return Product.from_row(row)

    def get_product_by_sku(
        self, sku: str, include_inactive: bool = False
    ) -> Product:
        """Fetches a single Product by SKU (case-insensitive) or raises ProductNotFoundError."""
        clean_sku = str(sku or "").strip().upper()
        if not clean_sku:
            raise ProductNotFoundError(identifier="")

        active_clause = "" if include_inactive else "AND p.is_active = 1"
        row = self.db.fetch_one(
            f"""
            SELECT
                p.*,
                c.name AS category_name,
                c.slug AS category_slug
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE UPPER(p.sku) = ? {active_clause};
            """,
            (clean_sku,),
        )
        if row is None:
            raise ProductNotFoundError(identifier=clean_sku)
        return Product.from_row(row)

    def get_products_by_ids(
        self,
        product_ids: Sequence[int],
        include_inactive: bool = False,
    ) -> List[Product]:
        """Fetches multiple products matching the provided IDs, preserving input order."""
        ordered_ids: List[int] = []
        for pid in product_ids:
            try:
                val = int(pid)
                if val not in ordered_ids:
                    ordered_ids.append(val)
            except (TypeError, ValueError):
                continue

        if not ordered_ids:
            return []

        placeholders = ", ".join("?" for _ in ordered_ids)
        active_clause = "" if include_inactive else "AND p.is_active = 1"
        rows = self.db.fetch_all(
            f"""
            SELECT
                p.*,
                c.name AS category_name,
                c.slug AS category_slug
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.id IN ({placeholders}) {active_clause};
            """,
            ordered_ids,
        )
        by_id = {int(r["id"]): Product.from_row(r) for r in rows}
        return [by_id[pid] for pid in ordered_ids if pid in by_id]

    # ------------------------------------------------------------------
    # Multi-Criteria Search, Filtering & Sorting
    # ------------------------------------------------------------------
    def search_and_filter_products(
        self,
        query: Optional[str] = None,
        category_slug: Optional[str] = None,
        brand: Optional[str] = None,
        product_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        availability: Optional[str] = None,
        sort_by: str = "featured",
        include_inactive: bool = False,
    ) -> List[Product]:
        """Queries products matching search text, filters, and sort preferences."""
        conditions: List[str] = []
        params: List[Any] = []

        if not include_inactive:
            conditions.append("p.is_active = 1")

        clean_query = (query or "").strip()
        if clean_query:
            pattern = f"%{_escape_like(clean_query.lower())}%"
            conditions.append(
                """
                (
                    LOWER(p.name) LIKE ? ESCAPE '\\'
                    OR LOWER(p.sku) LIKE ? ESCAPE '\\'
                    OR LOWER(p.brand) LIKE ? ESCAPE '\\'
                    OR LOWER(p.subcategory) LIKE ? ESCAPE '\\'
                    OR LOWER(p.description) LIKE ? ESCAPE '\\'
                    OR LOWER(c.name) LIKE ? ESCAPE '\\'
                )
                """
            )
            params.extend([pattern] * 6)

        clean_cat = (category_slug or "").strip().lower()
        if clean_cat and clean_cat != "all":
            conditions.append("LOWER(c.slug) = ?")
            params.append(clean_cat)

        clean_brand = (brand or "").strip()
        if clean_brand and clean_brand.lower() != "all":
            conditions.append("LOWER(p.brand) = ?")
            params.append(clean_brand.lower())

        clean_type = (product_type or "").strip()
        if clean_type and clean_type.lower() != "all":
            conditions.append("LOWER(p.subcategory) = ?")
            params.append(clean_type.lower())

        low_price = float(min_price) if min_price is not None else None
        high_price = float(max_price) if max_price is not None else None
        if low_price is not None and high_price is not None and low_price > high_price:
            low_price, high_price = high_price, low_price

        if low_price is not None and low_price >= 0:
            conditions.append("p.price >= ?")
            params.append(low_price)

        if high_price is not None and high_price >= 0:
            conditions.append("p.price <= ?")
            params.append(high_price)

        clean_avail = (availability or "").strip().lower()
        if clean_avail in ("in_stock", "available"):
            conditions.append("p.stock > 0")
        elif clean_avail == "low_stock":
            conditions.append("p.stock > 0 AND p.stock <= ?")
            params.append(Config.LOW_STOCK_THRESHOLD)
        elif clean_avail == "out_of_stock":
            conditions.append("p.stock = 0")

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sort_key = (sort_by or "featured").strip().lower()
        order_clauses: Dict[str, str] = {
            "featured": "p.is_featured DESC, p.is_bestseller DESC, c.display_order ASC, p.name ASC",
            "price_asc": "p.price ASC, p.name ASC",
            "price_desc": "p.price DESC, p.name ASC",
            "newest": "p.created_at DESC, p.id DESC",
            "popular": "units_sold DESC, p.is_bestseller DESC, p.is_featured DESC, p.name ASC",
            "bestselling": "p.is_bestseller DESC, units_sold DESC, p.is_featured DESC, p.name ASC",
        }
        order_sql = order_clauses.get(sort_key, order_clauses["featured"])

        rows = self.db.fetch_all(
            f"""
            SELECT
                p.*,
                c.name AS category_name,
                c.slug AS category_slug,
                COALESCE(
                    (SELECT SUM(oi.quantity) FROM order_items oi WHERE oi.product_id = p.id),
                    0
                ) AS units_sold
            FROM products p
            JOIN categories c ON p.category_id = c.id
            {where_sql}
            ORDER BY {order_sql};
            """,
            params,
        )
        return [Product.from_row(row) for row in rows]

    def get_featured_products(self, limit: int = 6) -> List[Product]:
        """Returns active featured products for storefront highlights."""
        rows = self.db.fetch_all(
            """
            SELECT
                p.*,
                c.name AS category_name,
                c.slug AS category_slug
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.is_active = 1 AND p.is_featured = 1
            ORDER BY p.is_bestseller DESC, c.display_order ASC, p.id ASC
            LIMIT ?;
            """,
            (max(1, int(limit)),),
        )
        return [Product.from_row(row) for row in rows]

    def get_bestsellers(self, limit: int = 6) -> List[Product]:
        """Returns active bestselling products."""
        rows = self.db.fetch_all(
            """
            SELECT
                p.*,
                c.name AS category_name,
                c.slug AS category_slug
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.is_active = 1 AND p.is_bestseller = 1
            ORDER BY p.is_featured DESC, p.id ASC
            LIMIT ?;
            """,
            (max(1, int(limit)),),
        )
        return [Product.from_row(row) for row in rows]

    # ------------------------------------------------------------------
    # Related-Product Recommendations
    # ------------------------------------------------------------------
    def get_related_products(
        self, product: Product, limit: int = 4
    ) -> List[Product]:
        """Recommends complementary and use-case-aligned products for a product page."""
        candidates = self.search_and_filter_products(include_inactive=False)
        target_cases = set(product.use_cases)
        complementary_slugs = set(
            self.COMPLEMENTARY_CATEGORIES.get(product.category_slug, [])
        )

        scored: List[tuple[int, Product]] = []
        for candidate in candidates:
            if candidate.id == product.id:
                continue

            score = 0
            shared_cases = len(target_cases.intersection(candidate.use_cases))
            score += shared_cases * 3

            if candidate.category_slug in complementary_slugs:
                score += 4
            elif candidate.category_slug == product.category_slug:
                score += 2

            if candidate.is_available:
                score += 2
            if candidate.is_bestseller:
                score += 1

            scored.append((score, candidate))

        scored.sort(key=lambda item: (-item[0], item[1].price, item[1].name))
        return [item[1] for item in scored[: max(1, int(limit))]]

    # ------------------------------------------------------------------
    # Side-by-Side Specification Comparison Matrix
    # ------------------------------------------------------------------
    def build_comparison_matrix(
        self, product_ids: Sequence[int]
    ) -> Dict[str, Any]:
        """Builds a side-by-side comparison payload for 2 to 3 selected products."""
        deduped_ids: List[int] = []
        for raw_id in product_ids:
            try:
                pid = int(raw_id)
                if pid not in deduped_ids:
                    deduped_ids.append(pid)
            except (TypeError, ValueError):
                continue

        deduped_ids = deduped_ids[: Config.MAX_COMPARISON_ITEMS]
        if len(deduped_ids) < 2:
            raise ValidationError(
                "Select at least 2 distinct products to compare side by side."
            )

        products: List[Product] = [
            self.get_product_by_id(pid, include_inactive=False)
            for pid in deduped_ids
        ]

        # Collect ordered union of technical specification keys across selected items
        spec_keys: List[str] = []
        for prod in products:
            for key in prod.specifications.keys():
                if key not in spec_keys:
                    spec_keys.append(key)

        spec_rows: List[Dict[str, Any]] = []
        for key in spec_keys:
            values = [
                str(prod.specifications.get(key, "—")) for prod in products
            ]
            spec_rows.append(
                {
                    "attribute": key,
                    "values": values,
                    "all_equal": len(set(values)) == 1,
                }
            )

        purpose_labels = Config.SETUP_PURPOSES
        use_case_values = [
            ", ".join(
                purpose_labels[c]["label"].split("&")[0].strip()
                if c in purpose_labels
                else c.replace("_", " ").title()
                for c in prod.use_cases
            )
            or "General Use"
            for prod in products
        ]

        return {
            "products": [prod.to_dict() for prod in products],
            "product_ids": [prod.id for prod in products],
            "core_rows": [
                {
                    "attribute": "Brand",
                    "values": [prod.brand for prod in products],
                },
                {
                    "attribute": "Category",
                    "values": [prod.category_name for prod in products],
                },
                {
                    "attribute": "SKU",
                    "values": [prod.sku for prod in products],
                },
                {
                    "attribute": "Price (NGN)",
                    "values": [prod.formatted_price for prod in products],
                },
                {
                    "attribute": "Availability",
                    "values": [
                        f"{prod.stock_status} ({prod.stock} units)"
                        for prod in products
                    ],
                },
                {
                    "attribute": "Best For",
                    "values": use_case_values,
                },
            ],
            "spec_rows": spec_rows,
        }