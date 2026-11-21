"""tests/conftest.py

Shared pytest fixtures providing isolated SQLite-backed Setuvo Flask
applications and test clients.
"""

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    """Creates an isolated Setuvo Flask app with a fresh SQLite database."""
    db_file = tmp_path / "test_setuvo.db"
    exports_dir = tmp_path / "exports"
    return create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "DATABASE_PATH": str(db_file),
            "EXPORTS_DIR": str(exports_dir),
            "MAIL_ENABLED": False,
            "SEED_SAMPLE_ORDERS": False,
        }
    )


@pytest.fixture()
def client(app):
    """Provides a Flask test client with cookie/session support."""
    return app.test_client()


@pytest.fixture()
def seeded_orders_app(tmp_path):
    """Creates an isolated Setuvo Flask app seeded with sample historical orders."""
    db_file = tmp_path / "test_setuvo_seeded.db"
    exports_dir = tmp_path / "exports_seeded"
    return create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "DATABASE_PATH": str(db_file),
            "EXPORTS_DIR": str(exports_dir),
            "MAIL_ENABLED": False,
            "SEED_SAMPLE_ORDERS": True,
        }
    )


@pytest.fixture()
def seeded_orders_client(seeded_orders_app):
    """Provides a test client backed by sample historical orders."""
    return seeded_orders_app.test_client()