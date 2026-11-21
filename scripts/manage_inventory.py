"""scripts/manage_inventory.py

Command-line inventory inspection and stock replenishment utility for Setuvo.

Usage examples:
    python scripts/manage_inventory.py list
    python scripts/manage_inventory.py low-stock
    python scripts/manage_inventory.py restock STV-LS-001 10
    python scripts/manage_inventory.py set-stock STV-LS-001 15
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from database.db_manager import DatabaseManager
from database.seed_data import seed_database
from models.entities import format_naira
from services.exceptions import SetuvoError
from services.inventory_service import InventoryService
from services.product_service import ProductService


def _bootstrap_services(db_path: Optional[str] = None):
    target_db = db_path or str(Config.DATABASE_PATH)
    db_manager = DatabaseManager(db_path=target_db)
    db_manager.init_db()
    existing = db_manager.fetch_one("SELECT COUNT(*) AS cnt FROM categories;")
    if existing is None or int(existing["cnt"]) == 0:
        seed_database(db_manager, include_sample_orders=False)
    return (
        db_manager,
        ProductService(db_manager),
        InventoryService(db_manager),
    )


def cmd_list(product_service: ProductService, only_low: bool = False) -> int:
    products = product_service.search_and_filter_products(
        sort_by="featured", include_inactive=True
    )
    if only_low:
        products = [p for p in products if p.stock <= Config.LOW_STOCK_THRESHOLD]

    if not products:
        print("No matching products found.")
        return 0

    print(f"{'SKU':<14} {'STOCK':>5}  {'STATUS':<13} {'PRICE (NGN)':>14}  NAME")
    print("-" * 78)
    for p in products:
        print(
            f"{p.sku:<14} {p.stock:>5}  {p.stock_status:<13} "
            f"{format_naira(p.price):>14}  {p.name}"
        )
    print("-" * 78)
    print(f"Total listed SKUs: {len(products)}")
    return 0


def cmd_update_stock(
    db_manager: DatabaseManager,
    inventory_service: InventoryService,
    sku: str,
    amount: int,
    mode: str,
) -> int:
    clean_sku = str(sku or "").strip().upper()
    row = db_manager.fetch_one(
        "SELECT id, sku, name, stock FROM products WHERE UPPER(sku) = ?;",
        (clean_sku,),
    )
    if not row:
        print(f"Error: Product with SKU '{clean_sku}' was not found.", file=sys.stderr)
        return 1

    product_id = int(row["id"])
    try:
        if mode == "restock":
            if amount <= 0:
                print(
                    "Error: Restock quantity must be a positive integer.",
                    file=sys.stderr,
                )
                return 1
            result = inventory_service.adjust_stock(
                product_id=product_id,
                delta=amount,
                reason=f"CLI restock (+{amount})",
                reference_code="CLI-RESTOCK",
            )
        else:
            if amount < 0:
                print(
                    "Error: Target stock cannot be negative.",
                    file=sys.stderr,
                )
                return 1
            result = inventory_service.set_stock_level(
                product_id=product_id,
                new_stock=amount,
                reason=f"CLI stock set ({row['stock']} -> {amount})",
                reference_code="CLI-SET-STOCK",
            )
    except SetuvoError as exc:
        print(f"Error: {exc.message}", file=sys.stderr)
        return 1

    print(
        f"Updated {row['sku']} ({row['name']}): "
        f"stock changed from {result['previous_stock']} -> {result['new_stock']}."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Setuvo Inventory & Stock Management CLI"
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Optional custom SQLite database path (defaults to Config.DATABASE_PATH).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List all catalogue SKUs and stock levels.")
    subparsers.add_parser(
        "low-stock", help="List active SKUs at or below 5 units remaining."
    )

    restock_p = subparsers.add_parser(
        "restock", help="Add incoming units to an existing product SKU."
    )
    restock_p.add_argument("sku", help="Product SKU (e.g. STV-LS-001)")
    restock_p.add_argument("quantity", type=int, help="Positive number of units to add")

    set_p = subparsers.add_parser(
        "set-stock", help="Set exact stock count for a product SKU."
    )
    set_p.add_argument("sku", help="Product SKU (e.g. STV-LS-001)")
    set_p.add_argument("quantity", type=int, help="New non-negative stock quantity")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db_manager, product_service, inventory_service = _bootstrap_services(args.db_path)

    if args.command == "list":
        return cmd_list(product_service, only_low=False)
    if args.command == "low-stock":
        return cmd_list(product_service, only_low=True)
    if args.command == "restock":
        return cmd_update_stock(
            db_manager, inventory_service, args.sku, args.quantity, mode="restock"
        )
    if args.command == "set-stock":
        return cmd_update_stock(
            db_manager, inventory_service, args.sku, args.quantity, mode="set"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())