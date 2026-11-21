"""services/exceptions.py

Typed domain exception hierarchy for Setuvo covering product lookup,
inventory stock enforcement, checkout validation, order tracking,
SQLite persistence, and SMTP notification errors.
"""

from typing import Optional


class SetuvoError(Exception):
    """Base exception for all Setuvo domain and operational errors."""

    default_message: str = "An unexpected Setuvo application error occurred."
    status_code: int = 400

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> None:
        self.message: str = (message or self.default_message).strip()
        self.details: Optional[str] = details.strip() if details else None
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.__str__())

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} ({self.details})"
        return self.message


class ValidationError(SetuvoError):
    """Raised when form inputs, quantities, budgets, or zone codes are invalid."""

    default_message = "One or more submitted values are invalid."
    status_code = 400


class EmptyCartError(SetuvoError):
    """Raised when a customer attempts to check out with an empty cart."""

    default_message = "Your shopping cart is empty. Add at least one item before checking out."
    status_code = 400


class ProductNotFoundError(SetuvoError):
    """Raised when a requested product ID, SKU, or bundle cannot be found."""

    default_message = "The requested product or bundle could not be found."
    status_code = 404

    def __init__(
        self,
        identifier: str = "",
        message: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        self.identifier: str = str(identifier).strip()
        resolved_msg = message or (
            f"Product '{self.identifier}' was not found or is currently unavailable."
            if self.identifier
            else self.default_message
        )
        super().__init__(message=resolved_msg, details=details, status_code=404)


class OutOfStockError(SetuvoError):
    """Raised when a customer attempts to add or buy a product with zero stock."""

    default_message = "This item is currently out of stock."
    status_code = 409

    def __init__(
        self,
        product_name: str,
        sku: str = "",
        details: Optional[str] = None,
    ) -> None:
        self.product_name: str = product_name
        self.sku: str = sku
        label = f"{product_name} ({sku})" if sku else product_name
        super().__init__(
            message=f"'{label}' is currently out of stock.",
            details=details,
            status_code=409,
        )


class InsufficientStockError(SetuvoError):
    """Raised when requested quantity exceeds available inventory."""

    default_message = "Requested quantity exceeds available stock."
    status_code = 409

    def __init__(
        self,
        product_name: str,
        requested: int,
        available: int,
        sku: str = "",
    ) -> None:
        self.product_name: str = product_name
        self.sku: str = sku
        self.requested: int = int(requested)
        self.available: int = int(available)
        label = f"{product_name} ({sku})" if sku else product_name
        super().__init__(
            message=(
                f"Only {self.available} unit(s) of '{label}' available "
                f"(you requested {self.requested})."
            ),
            status_code=409,
        )


class OrderNotFoundError(SetuvoError):
    """Raised when an order tracking lookup finds no matching order number/email."""

    default_message = "No order matched that order number and email address."
    status_code = 404

    def __init__(
        self,
        order_number: str = "",
        message: Optional[str] = None,
    ) -> None:
        self.order_number: str = str(order_number).strip().upper()
        resolved_msg = message or (
            f"No order found for reference '{self.order_number}' with the provided email."
            if self.order_number
            else self.default_message
        )
        super().__init__(message=resolved_msg, status_code=404)


class EmailDeliveryError(SetuvoError):
    """Raised when SMTP order confirmation delivery fails (handled non-fatally)."""

    default_message = "Order saved, but confirmation email could not be delivered."
    status_code = 502


class DatabaseError(SetuvoError):
    """Raised when an underlying SQLite query or transaction fails."""

    default_message = "A local database error occurred while processing your request."
    status_code = 500