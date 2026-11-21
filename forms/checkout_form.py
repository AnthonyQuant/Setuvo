"""forms/checkout_form.py

Flask-WTF validation forms for Setuvo's guest checkout workflow
and customer order tracking lookup.
"""

import re
from typing import List, Tuple

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional as OptionalValidator, Regexp, ValidationError

from config import Config
from models.entities import format_naira

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\+?[0-9\s\-()]{7,20}$")
ORDER_NUMBER_PATTERN = re.compile(r"^STV-\d{8}-\d{4}$", re.IGNORECASE)


def build_delivery_zone_choices() -> List[Tuple[str, str]]:
    """Builds formatted (slug, label + Naira fee) tuples from Config.DELIVERY_ZONES."""
    choices: List[Tuple[str, str]] = []
    for slug, meta in Config.DELIVERY_ZONES.items():
        fee = float(meta["fee"])
        fee_label = "Free" if fee == 0 else format_naira(fee)
        choices.append((slug, f"{meta['label']} — {fee_label} ({meta['eta']})"))
    return choices


class GuestCheckoutForm(FlaskForm):
    """Validates guest customer contact, Nigerian delivery zone, and address details."""

    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Please enter your full name."),
            Length(
                min=2,
                max=120,
                message="Full name must be between 2 and 120 characters.",
            ),
        ],
    )
    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Please enter your email address for order updates."),
            Length(max=150, message="Email address must be 150 characters or fewer."),
            Regexp(
                EMAIL_PATTERN,
                message="Please enter a valid email address (e.g., name@example.ng).",
            ),
        ],
    )
    phone = StringField(
        "Phone Number",
        validators=[
            DataRequired(message="Please enter a reachable phone number for dispatch."),
            Regexp(
                PHONE_PATTERN,
                message="Enter a valid phone number (e.g., 08031234567 or +2348031234567).",
            ),
        ],
    )
    delivery_zone = SelectField(
        "Delivery Zone (Nigeria)",
        choices=build_delivery_zone_choices(),
        default="edo_local",
        validators=[DataRequired(message="Please choose a delivery zone.")],
    )
    address = TextAreaField(
        "Delivery Address",
        validators=[
            DataRequired(message="Please enter your street, hostel, or office address."),
            Length(
                min=5,
                max=300,
                message="Delivery address must be between 5 and 300 characters.",
            ),
        ],
    )
    payment_method = SelectField(
        "Payment Method",
        choices=[
            ("Pay on Delivery (Demo)", "Pay on Delivery (Demo)"),
            ("Bank Transfer on Dispatch (Demo)", "Bank Transfer on Dispatch (Demo)"),
        ],
        default="Pay on Delivery (Demo)",
        validators=[DataRequired(message="Please select a payment method.")],
    )
    notes = TextAreaField(
        "Order Notes (Optional)",
        validators=[
            OptionalValidator(),
            Length(max=250, message="Order notes must be 250 characters or fewer."),
        ],
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.delivery_zone.choices = build_delivery_zone_choices()

    def validate_phone(self, field: StringField) -> None:
        """Ensures the phone number contains at least 10 digits after stripping formatting."""
        digits = re.sub(r"\D", "", str(field.data or ""))
        if len(digits) < 10 or len(digits) > 15:
            raise ValidationError(
                "Phone number must contain between 10 and 15 digits."
            )

    def validate_delivery_zone(self, field: SelectField) -> None:
        """Ensures the submitted delivery zone exists in Config.DELIVERY_ZONES."""
        zone_key = str(field.data or "").strip().lower()
        if zone_key not in Config.DELIVERY_ZONES:
            raise ValidationError("Selected Nigerian delivery zone is not supported.")


class OrderTrackingForm(FlaskForm):
    """Validates order reference and customer email for self-service order tracking."""

    order_number = StringField(
        "Order Number",
        validators=[
            DataRequired(message="Please enter your Setuvo order number."),
            Length(max=30, message="Order number is too long."),
            Regexp(
                ORDER_NUMBER_PATTERN,
                message="Order number must follow the format STV-YYYYMMDD-XXXX (e.g., STV-20261121-1001).",
            ),
        ],
    )
    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Please enter the email address used during checkout."),
            Length(max=150, message="Email address must be 150 characters or fewer."),
            Regexp(
                EMAIL_PATTERN,
                message="Please enter a valid email address.",
            ),
        ],
    )

    @property
    def normalized_order_number(self) -> str:
        return str(self.order_number.data or "").strip().upper()

    @property
    def normalized_email(self) -> str:
        return str(self.email.data or "").strip().lower()