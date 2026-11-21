"""forms/search_form.py

Flask-WTF validation forms for Setuvo's product catalogue search/filtering,
Curated Workstation Setup Builder, and side-by-side product comparison.
"""

from typing import Any, Dict, List, Optional, Sequence

from flask_wtf import FlaskForm
from wtforms import (
    DecimalField,
    SelectField,
    SelectMultipleField,
    StringField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional as OptionalValidator, ValidationError

from config import Config
from models.entities import Product
from services.product_service import ProductService


class ProductSearchForm(FlaskForm):
    """GET-friendly catalogue search, multi-filter, and sorting form."""

    class Meta:
        csrf = False

    q = StringField(
        "Search Products",
        validators=[
            OptionalValidator(),
            Length(max=100, message="Search query must be 100 characters or fewer."),
        ],
    )
    category = SelectField(
        "Category",
        choices=[("all", "All Categories")],
        default="all",
        validators=[OptionalValidator()],
    )
    brand = SelectField(
        "Brand",
        choices=[("all", "All Brands")],
        default="all",
        validators=[OptionalValidator()],
    )
    product_type = SelectField(
        "Product Type",
        choices=[("all", "All Product Types")],
        default="all",
        validators=[OptionalValidator()],
    )
    min_price = DecimalField(
        "Min Price (₦)",
        places=2,
        validators=[
            OptionalValidator(),
            NumberRange(min=0, message="Minimum price cannot be negative."),
        ],
    )
    max_price = DecimalField(
        "Max Price (₦)",
        places=2,
        validators=[
            OptionalValidator(),
            NumberRange(min=0, message="Maximum price cannot be negative."),
        ],
    )
    availability = SelectField(
        "Availability",
        choices=[
            ("all", "All Stock Statuses"),
            ("in_stock", "In Stock Only"),
            ("low_stock", f"Low Stock (≤ {Config.LOW_STOCK_THRESHOLD} left)"),
            ("out_of_stock", "Out of Stock"),
        ],
        default="all",
        validators=[OptionalValidator()],
    )
    sort_by = SelectField(
        "Sort By",
        choices=list(ProductService.SORT_OPTIONS.items()),
        default="featured",
        validators=[OptionalValidator()],
    )

    def populate_filter_choices(self, filter_options: Dict[str, Any]) -> None:
        """Dynamically populates category, brand, and product-type dropdown choices."""
        cat_choices = [("all", "All Categories")]
        for cat in filter_options.get("categories", []):
            cat_choices.append(
                (str(cat["slug"]), f"{cat['name']} ({cat['product_count']})")
            )
        self.category.choices = cat_choices

        brand_choices = [("all", "All Brands")]
        for brand_name in filter_options.get("brands", []):
            brand_choices.append((str(brand_name), str(brand_name)))
        self.brand.choices = brand_choices

        type_choices = [("all", "All Product Types")]
        for ptype in filter_options.get("product_types", []):
            type_choices.append((str(ptype), str(ptype)))
        self.product_type.choices = type_choices

        sort_map = filter_options.get("sort_options") or ProductService.SORT_OPTIONS
        self.sort_by.choices = list(sort_map.items())

    def validate_max_price(self, field: DecimalField) -> None:
        """Ensures maximum price is not lower than minimum price when both are supplied."""
        if (
            self.min_price.data is not None
            and field.data is not None
            and field.data < self.min_price.data
        ):
            raise ValidationError(
                "Maximum price cannot be lower than minimum price."
            )


class SetupBuilderForm(FlaskForm):
    """Validates purpose, NGN target budget, and product picks in the Setup Builder."""

    purpose = SelectField(
        "Workstation Purpose",
        choices=[
            (slug, str(meta["label"]))
            for slug, meta in Config.SETUP_PURPOSES.items()
        ],
        default="programming",
        validators=[DataRequired(message="Please choose a workstation purpose.")],
    )
    budget = DecimalField(
        "Target Budget (₦)",
        places=2,
        default=250000.00,
        validators=[
            DataRequired(message="Please enter your workstation budget in Naira."),
            NumberRange(
                min=1000,
                max=50000000,
                message="Budget must be between ₦1,000 and ₦50,000,000.",
            ),
        ],
    )
    product_ids = SelectMultipleField(
        "Selected Setup Products",
        coerce=int,
        choices=[],
        validators=[OptionalValidator()],
    )

    def populate_product_choices(self, products: Sequence[Product]) -> None:
        """Populates selectable product IDs from the active catalogue."""
        self.product_ids.choices = [
            (int(p.id), f"{p.name} ({p.formatted_price})") for p in products
        ]


class ProductComparisonForm(FlaskForm):
    """Validates 2 to 3 distinct products for side-by-side specification comparison."""

    class Meta:
        csrf = False

    product_1 = SelectField(
        "First Product",
        coerce=int,
        choices=[],
        validators=[DataRequired(message="Select the first product to compare.")],
    )
    product_2 = SelectField(
        "Second Product",
        coerce=int,
        choices=[],
        validators=[DataRequired(message="Select the second product to compare.")],
    )
    product_3 = SelectField(
        "Third Product (Optional)",
        coerce=int,
        default=0,
        choices=[(0, "— Optional 3rd Product —")],
        validators=[OptionalValidator()],
    )

    def populate_product_choices(self, products: Sequence[Product]) -> None:
        """Populates dropdown options with active products."""
        base_choices = [
            (int(p.id), f"{p.name} — {p.brand} ({p.formatted_price})")
            for p in products
        ]
        self.product_1.choices = base_choices
        self.product_2.choices = base_choices
        self.product_3.choices = [(0, "— Optional 3rd Product —")] + base_choices

    def validate(self, extra_validators: Optional[Dict[str, Any]] = None) -> bool:
        """Ensures at least 2 distinct products are selected."""
        is_valid = super().validate(extra_validators=extra_validators)
        if not is_valid:
            return False

        p1 = int(self.product_1.data or 0)
        p2 = int(self.product_2.data or 0)
        p3 = int(self.product_3.data or 0)

        if p1 <= 0 or p2 <= 0:
            self.product_2.errors.append("Please select two valid products to compare.")
            return False

        if p1 == p2:
            self.product_2.errors.append("Select a different second product to compare.")
            return False

        if p3 > 0 and p3 in (p1, p2):
            self.product_3.errors.append(
                "The third product must be different from the first two."
            )
            return False

        return True

    def get_selected_ids(self) -> List[int]:
        """Returns the deduplicated ordered list of chosen product IDs."""
        ids = [int(self.product_1.data), int(self.product_2.data)]
        p3 = int(self.product_3.data or 0)
        if p3 > 0 and p3 not in ids:
            ids.append(p3)
        return ids