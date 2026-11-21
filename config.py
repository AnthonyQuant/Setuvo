"""config.py

Centralized configuration for Setuvo — a curated student, developer,
and creator workstation store priced in Nigerian Naira (NGN).
"""

import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

BASE_DIR: Path = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Application settings, currency rules, delivery zones, and SMTP defaults."""

    APP_NAME: str = "Setuvo"
    APP_TAGLINE: str = "Curated Study, Developer & Creator Workstation Essentials"

    # Security & Flask Core
    SECRET_KEY: str = (
        os.getenv("FLASK_SECRET_KEY")
        or os.getenv("SECRET_KEY")
        or "dev-setuvo-secret-key-change-in-production"
    )
    DEBUG: bool = _as_bool(os.getenv("FLASK_DEBUG"), default=True)
    WTF_CSRF_ENABLED: bool = True

    # Local Storage & File Paths
    DATABASE_DIR: Path = BASE_DIR / "database"
    DATABASE_PATH: Path = Path(
        os.getenv("SETUVO_DATABASE_PATH")
        or os.getenv("DATABASE_PATH")
        or str(DATABASE_DIR / "shop.db")
    )
    SCHEMA_PATH: Path = DATABASE_DIR / "schema.sql"
    EXPORTS_DIR: Path = Path(
        os.getenv("SETUVO_EXPORTS_DIR")
        or os.getenv("EXPORTS_DIR")
        or str(BASE_DIR / "exports")
    )

    # Currency & Inventory Rules
    CURRENCY_CODE: str = "NGN"
    CURRENCY_SYMBOL: str = "₦"
    LOW_STOCK_THRESHOLD: int = 5
    MAX_COMPARISON_ITEMS: int = 3

    # Nigerian Delivery Zones & Shipping Fees (in NGN)
    DELIVERY_ZONES: Dict[str, Dict[str, Any]] = {
        "pickup_benin": {
            "label": "Store Pickup — Benin City (UNIBEN / Ugbowo Hub)",
            "fee": 0.0,
            "eta": "Same day (2–4 hours)",
        },
        "edo_local": {
            "label": "Edo State (Benin City & Environs)",
            "fee": 2500.0,
            "eta": "1–2 business days",
        },
        "lagos_metro": {
            "label": "Lagos State (Mainland & Island)",
            "fee": 3500.0,
            "eta": "2–3 business days",
        },
        "abuja_fct": {
            "label": "Abuja (FCT)",
            "fee": 4000.0,
            "eta": "2–4 business days",
        },
        "south_south_east": {
            "label": "South-South & South-East (Port Harcourt, Asaba, Enugu, Owerri)",
            "fee": 3500.0,
            "eta": "2–4 business days",
        },
        "south_west": {
            "label": "South-West (Ibadan, Abeokuta, Akure, Osogbo)",
            "fee": 3800.0,
            "eta": "2–4 business days",
        },
        "northern_zones": {
            "label": "North-Central, North-West & North-East",
            "fee": 5000.0,
            "eta": "3–5 business days",
        },
    }

    # Curated Workstation Setup Builder Purposes
    SETUP_PURPOSES: Dict[str, Dict[str, Any]] = {
        "studying": {
            "label": "Studying & Academic Research",
            "description": "Ergonomic posture, distraction-free audio, and portable study essentials.",
            "default_budget": 150000.0,
            "recommended_categories": [
                "laptop-stands-cooling",
                "headphones-audio",
                "study-productivity",
                "storage-connectivity",
            ],
        },
        "programming": {
            "label": "Software Engineering & Quantitative Coding",
            "description": "Tactile mechanical input, precision mice, elevated screens, and USB-C docks.",
            "default_budget": 250000.0,
            "recommended_categories": [
                "keyboards-mice",
                "laptop-stands-cooling",
                "storage-connectivity",
                "desk-essentials",
            ],
        },
        "content_creation": {
            "label": "Content Creation, Design & Video Editing",
            "description": "Studio monitoring audio, high-speed external SSDs, and desk lighting.",
            "default_budget": 320000.0,
            "recommended_categories": [
                "headphones-audio",
                "storage-connectivity",
                "desk-essentials",
                "computer-accessories",
            ],
        },
        "general_productivity": {
            "label": "General Home Office & Productivity",
            "description": "Balanced everyday workstation upgrades for remote work and comfort.",
            "default_budget": 200000.0,
            "recommended_categories": [
                "keyboards-mice",
                "laptop-stands-cooling",
                "desk-essentials",
                "computer-accessories",
            ],
        },
    }

    # Order Fulfillment Lifecycle
    ORDER_STATUSES: List[str] = [
        "Order placed",
        "Processing",
        "Shipped",
        "Delivered",
        "Cancelled",
    ]

    # Fault-Tolerant SMTP Email Notification Settings (Port 465 SSL)
    MAIL_ENABLED: bool = _as_bool(os.getenv("MAIL_ENABLED"), default=False)
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "465"))
    MAIL_USE_TLS: bool = _as_bool(os.getenv("MAIL_USE_TLS"), default=False)
    MAIL_USE_SSL: bool = _as_bool(os.getenv("MAIL_USE_SSL"), default=True)
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER: str = os.getenv(
        "MAIL_DEFAULT_SENDER", "orders@setuvo.ng"
    )
    ADMIN_NOTIFICATION_EMAIL: str = os.getenv(
        "ADMIN_NOTIFICATION_EMAIL", "admin@setuvo.ng"
    )

    @classmethod
    def ensure_directories(cls) -> None:
        """Creates runtime database and CSV export folders if missing."""
        cls.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        cls.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)