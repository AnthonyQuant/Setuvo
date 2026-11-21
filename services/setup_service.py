"""services/setup_service.py

Curated Workstation Setup Builder and Preconfigured Bundle engine for Setuvo.
Provides deterministic purpose-based product curation, running NGN budget
calculations, budget-exceeded warnings, and customizable kit pricing.
"""

from typing import Any, Dict, List, Optional, Sequence

from config import Config
from database.db_manager import DatabaseManager
from models.entities import Bundle, Product, format_naira
from services.exceptions import ProductNotFoundError, ValidationError
from services.product_service import ProductService


class SetupService:
    """Handles curated workstation setup building and preconfigured kit customization."""

    DEFAULT_PURPOSE: str = "programming"

    def __init__(
        self,
        db_manager: DatabaseManager,
        product_service: Optional[ProductService] = None,
    ) -> None:
        self.db: DatabaseManager = db_manager
        self.product_service: ProductService = product_service or ProductService(db_manager)

    # ------------------------------------------------------------------
    # Purpose Metadata & Curated Product Recommendations
    # ------------------------------------------------------------------
    def normalize_purpose(self, purpose: Optional[str]) -> str:
        """Validates and normalizes a setup purpose slug to a supported key."""
        clean = (purpose or self.DEFAULT_PURPOSE).strip().lower()
        if clean not in Config.SETUP_PURPOSES:
            return self.DEFAULT_PURPOSE
        return clean

    def get_purpose_options(self) -> List[Dict[str, Any]]:
        """Returns ordered setup purpose definitions with formatted default budgets."""
        options: List[Dict[str, Any]] = []
        for slug, meta in Config.SETUP_PURPOSES.items():
            default_budget = float(meta["default_budget"])
            options.append(
                {
                    "slug": slug,
                    "label": meta["label"],
                    "description": meta["description"],
                    "default_budget": default_budget,
                    "formatted_default_budget": format_naira(default_budget),
                    "recommended_categories": list(meta["recommended_categories"]),
                }
            )
        return options

    def get_recommended_products(self, purpose: Optional[str]) -> Dict[str, Any]:
        """Returns curated products matching a workstation purpose, grouped by category."""
        purpose_key = self.normalize_purpose(purpose)
        purpose_meta = Config.SETUP_PURPOSES[purpose_key]
        preferred_slugs: List[str] = list(purpose_meta["recommended_categories"])

        all_products = self.product_service.search_and_filter_products(
            include_inactive=False
        )

        # Rank products that explicitly list the purpose in use_cases or belong to target categories
        scored_products: List[tuple[int, Product]] = []
        for prod in all_products:
            in_use_cases = purpose_key in prod.use_cases
            in_pref_cat = prod.category_slug in preferred_slugs
            if not in_use_cases and not in_pref_cat:
                continue

            cat_rank = (
                preferred_slugs.index(prod.category_slug)
                if in_pref_cat
                else len(preferred_slugs) + 1
            )
            score = 0
            if in_use_cases:
                score += 10
            if in_pref_cat:
                score += 5
            if prod.is_available:
                score += 3
            if prod.is_bestseller:
                score += 2
            scored_products.append((cat_rank * 100 - score, prod))

        scored_products.sort(key=lambda item: (item[0], item[1].price, item[1].name))
        recommended_list = [item[1] for item in scored_products]

        # Group products by category preserving preferred category order
        grouped_map: Dict[str, Dict[str, Any]] = {}
        for prod in recommended_list:
            slug = prod.category_slug
            if slug not in grouped_map:
                grouped_map[slug] = {
                    "category_slug": slug,
                    "category_name": prod.category_name,
                    "products": [],
                }
            grouped_map[slug]["products"].append(prod.to_dict())

        ordered_groups: List[Dict[str, Any]] = []
        for slug in preferred_slugs:
            if slug in grouped_map:
                ordered_groups.append(grouped_map.pop(slug))
        ordered_groups.extend(grouped_map.values())

        return {
            "purpose": purpose_key,
            "purpose_label": purpose_meta["label"],
            "purpose_description": purpose_meta["description"],
            "default_budget": float(purpose_meta["default_budget"]),
            "products": [p.to_dict() for p in recommended_list],
            "grouped_categories": ordered_groups,
            "total_recommended": len(recommended_list),
        }

    # ------------------------------------------------------------------
    # Curated Setup Builder Budget & Selection Evaluator
    # ------------------------------------------------------------------
    def evaluate_setup(
        self,
        purpose: Optional[str],
        budget: Optional[float],
        selected_ids: Optional[Sequence[int]] = None,
    ) -> Dict[str, Any]:
        """Computes running NGN total, remaining budget, and warnings for a custom setup."""
        purpose_key = self.normalize_purpose(purpose)
        purpose_meta = Config.SETUP_PURPOSES[purpose_key]

        if budget is None:
            clean_budget = float(purpose_meta["default_budget"])
        else:
            try:
                clean_budget = round(float(budget), 2)
            except (TypeError, ValueError) as exc:
                raise ValidationError("Please enter a valid numeric budget in Naira.") from exc

        if clean_budget <= 0:
            raise ValidationError("Workstation budget must be greater than ₦0.00.")

        raw_ids = list(selected_ids or [])
        selected_products: List[Product] = self.product_service.get_products_by_ids(
            raw_ids, include_inactive=False
        )

        selected_total = round(sum(p.price for p in selected_products), 2)
        remaining_budget = round(clean_budget - selected_total, 2)
        is_over_budget = selected_total > clean_budget
        over_budget_amount = round(max(0.0, selected_total - clean_budget), 2)
        utilization_pct = (
            round((selected_total / clean_budget) * 100.0, 1)
            if clean_budget > 0
            else 0.0
        )

        unavailable_items = [p.to_dict() for p in selected_products if not p.is_available]
        purchasable_ids = [p.id for p in selected_products if p.is_available]

        warning_message: Optional[str] = None
        if is_over_budget:
            warning_message = (
                f"Budget exceeded by {format_naira(over_budget_amount)}. "
                f"Remove an item or raise your target budget above {format_naira(selected_total)}."
            )

        return {
            "purpose": purpose_key,
            "purpose_label": purpose_meta["label"],
            "purpose_description": purpose_meta["description"],
            "budget": clean_budget,
            "formatted_budget": format_naira(clean_budget),
            "selected_products": [p.to_dict() for p in selected_products],
            "selected_ids": [p.id for p in selected_products],
            "purchasable_ids": purchasable_ids,
            "selected_count": len(selected_products),
            "selected_total": selected_total,
            "formatted_selected_total": format_naira(selected_total),
            "remaining_budget": remaining_budget,
            "formatted_remaining_budget": format_naira(max(0.0, remaining_budget)),
            "is_over_budget": is_over_budget,
            "over_budget_amount": over_budget_amount,
            "formatted_over_budget": format_naira(over_budget_amount),
            "utilization_pct": utilization_pct,
            "warning_message": warning_message,
            "unavailable_items": unavailable_items,
            "all_in_stock": len(unavailable_items) == 0,
        }

    # ------------------------------------------------------------------
    # Preconfigured Workstation Bundles & Customization
    # ------------------------------------------------------------------
    def _hydrate_bundle(self, bundle_row: Any) -> Bundle:
        """Loads component products and quantities for a bundle SQLite row."""
        bundle_id = int(bundle_row["id"])
        item_rows = self.db.fetch_all(
            """
            SELECT
                bi.quantity,
                p.*,
                c.name AS category_name,
                c.slug AS category_slug
            FROM bundle_items bi
            JOIN products p ON bi.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            WHERE bi.bundle_id = ?
            ORDER BY c.display_order ASC, p.id ASC;
            """,
            (bundle_id,),
        )
        items: List[Dict[str, Any]] = []
        for row in item_rows:
            product = Product.from_row(row)
            items.append(
                {
                    "product": product,
                    "quantity": int(row["quantity"]),
                }
            )
        return Bundle.from_row(bundle_row, items=items)

    def get_all_bundles(self, include_inactive: bool = False) -> List[Bundle]:
        """Returns all preconfigured workstation bundles with savings calculations."""
        where_clause = "" if include_inactive else "WHERE is_active = 1"
        rows = self.db.fetch_all(
            f"""
            SELECT *
            FROM bundles
            {where_clause}
            ORDER BY id ASC;
            """
        )
        return [self._hydrate_bundle(row) for row in rows]

    def get_bundle_by_slug(
        self, slug: str, include_inactive: bool = False
    ) -> Bundle:
        """Fetches a single Bundle by URL slug or raises ProductNotFoundError."""
        clean_slug = (slug or "").strip().lower()
        if not clean_slug:
            raise ProductNotFoundError(identifier="")

        active_clause = "" if include_inactive else "AND is_active = 1"
        row = self.db.fetch_one(
            f"""
            SELECT *
            FROM bundles
            WHERE LOWER(slug) = ? {active_clause};
            """,
            (clean_slug,),
        )
        if row is None:
            raise ProductNotFoundError(identifier=clean_slug)
        return self._hydrate_bundle(row)

    def preview_customized_bundle(
        self,
        bundle_slug: str,
        kept_product_ids: Optional[Sequence[int]] = None,
        extra_product_ids: Optional[Sequence[int]] = None,
    ) -> Dict[str, Any]:
        """Computes customized bundle pricing and cart items when a user tweaks a kit."""
        bundle = self.get_bundle_by_slug(bundle_slug, include_inactive=False)

        default_items: List[Dict[str, Any]] = list(bundle.items)
        if kept_product_ids is None:
            chosen_entries = default_items
        else:
            allowed_ids = {int(pid) for pid in kept_product_ids}
            chosen_entries = [
                entry
                for entry in default_items
                if entry["product"].id in allowed_ids
            ]

        chosen_ids = {entry["product"].id for entry in chosen_entries}

        if extra_product_ids:
            extras = self.product_service.get_products_by_ids(
                extra_product_ids, include_inactive=False
            )
            for prod in extras:
                if prod.id not in chosen_ids:
                    chosen_entries.append({"product": prod, "quantity": 1})
                    chosen_ids.add(prod.id)

        if not chosen_entries:
            raise ValidationError(
                "Keep at least one product in the kit before adding it to your cart."
            )

        individual_total = round(
            sum(entry["product"].price * int(entry["quantity"]) for entry in chosen_entries),
            2,
        )
        # Apply full kit discount when >= 2 items remain in the bundle
        effective_discount_pct = (
            bundle.discount_pct if len(chosen_entries) >= 2 else 0.0
        )
        customized_price = round(
            individual_total * (1.0 - effective_discount_pct / 100.0), 2
        )
        savings_amount = round(max(0.0, individual_total - customized_price), 2)

        serialized_entries = []
        unavailable_names: List[str] = []
        for entry in chosen_entries:
            prod: Product = entry["product"]
            qty = int(entry["quantity"])
            if not prod.is_available or prod.stock < qty:
                unavailable_names.append(prod.name)
            serialized_entries.append(
                {
                    "product": prod.to_dict(),
                    "quantity": qty,
                    "line_total": round(prod.price * qty, 2),
                    "formatted_line_total": format_naira(prod.price * qty),
                }
            )

        return {
            "bundle": bundle.to_dict(),
            "items": serialized_entries,
            "selected_product_ids": [entry["product"].id for entry in chosen_entries],
            "discount_pct": effective_discount_pct,
            "individual_total": individual_total,
            "formatted_individual_total": format_naira(individual_total),
            "customized_price": customized_price,
            "formatted_customized_price": format_naira(customized_price),
            "savings_amount": savings_amount,
            "formatted_savings": format_naira(savings_amount),
            "is_available": len(unavailable_names) == 0,
            "unavailable_names": unavailable_names,
        }