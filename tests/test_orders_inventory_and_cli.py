"""tests/test_orders_inventory_and_cli.py

Tests session cart stock enforcement & reconciliation, Nigerian delivery zone fees,
wishlist actions, atomic guest checkout, stock deduction & cancellation restocking,
order tracking, and the CLI scripts in scripts/manage_inventory.py and scripts/sales_report.py.
"""

from scripts.manage_inventory import main as manage_inventory_main
from scripts.sales_report import main as sales_report_main


def test_cart_stock_clamping_and_nigerian_delivery_zones(app, client):
    services = app.extensions["services"]
    product_service = services["product_service"]
    inventory_service = services["inventory_service"]
    product = product_service.get_product_by_id(1)

    # 1. Direct add above live stock must be rejected without corrupting cart
    over_resp = client.post(
        "/cart/add",
        data={"product_id": "1", "quantity": str(product.stock + 20)},
        follow_redirects=True,
    )
    assert over_resp.status_code == 200
    assert "Your Setuvo shopping cart is empty" in client.get("/cart").get_data(
        as_text=True
    )

    # 2. Add 3 units legitimately, then drop live SQLite stock to 1 unit;
    #    CartService.get_cart_summary() must auto-clamp the cart quantity to 1.
    client.post("/cart/add", data={"product_id": "1", "quantity": "3"})
    inventory_service.set_stock_level(1, 1, reason="Test stock drop")
    client.post("/cart/zone", data={"delivery_zone": "lagos_metro"})

    cart_resp = client.get("/cart")
    html = cart_resp.get_data(as_text=True)
    normalized_html = " ".join(html.split())
    assert cart_resp.status_code == 200
    assert "Selected Items (1 unit across 1 product)" in normalized_html
    assert "Lagos State" in normalized_html
    assert "₦3,500.00" in normalized_html


def test_wishlist_toggle_and_move_to_cart(client):
    toggle = client.post("/wishlist/toggle/1", follow_redirects=True)
    assert toggle.status_code == 200
    assert "Nexstand K2" in toggle.get_data(as_text=True)

    move = client.post("/wishlist/move-to-cart/1", follow_redirects=True)
    assert move.status_code == 200
    assert "Nexstand K2" in client.get("/cart").get_data(as_text=True)


def test_atomic_checkout_tracking_and_cancellation_restock(app, client):
    services = app.extensions["services"]
    product_service = services["product_service"]
    order_service = services["order_service"]

    initial_stock = product_service.get_product_by_id(1).stock
    assert initial_stock >= 3

    client.post("/cart/add", data={"product_id": "1", "quantity": "2"})
    checkout_resp = client.post(
        "/checkout",
        data={
            "full_name": "Anthony Omokpo",
            "email": "anthony@example.ng",
            "phone": "08064890981",
            "delivery_zone": "pickup_benin",
            "address": "UNIBEN Ugbowo Campus, Benin City, Edo State",
            "payment_method": "Pay on Delivery (Demo)",
            "notes": "Call on arrival",
        },
        follow_redirects=True,
    )
    assert checkout_resp.status_code == 200
    assert "Thank You, Anthony Omokpo!" in checkout_resp.get_data(as_text=True)

    # Stock must decrease by 2 immediately upon checkout
    assert product_service.get_product_by_id(1).stock == initial_stock - 2

    # Cart must be cleared
    assert "Your Setuvo shopping cart is empty" in client.get("/cart").get_data(
        as_text=True
    )

    orders = order_service.get_all_orders()
    assert len(orders) == 1
    order = orders[0]

    # Self-service order tracking lookup
    track_resp = client.post(
        "/track-order",
        data={"order_number": order.order_number, "email": "anthony@example.ng"},
    )
    track_html = track_resp.get_data(as_text=True)
    assert track_resp.status_code == 200
    assert order.order_number in track_html
    assert "Fulfillment Progress" in track_html

    # Cancelling the order must restore the 2 deducted units
    order_service.update_order_status(order.order_number, "Cancelled")
    assert product_service.get_product_by_id(1).stock == initial_stock


def test_cli_inventory_and_sales_report_scripts(tmp_path, capsys):
    cli_db = str(tmp_path / "cli_test.db")
    cli_exports = str(tmp_path / "cli_exports")

    assert manage_inventory_main(["--db-path", cli_db, "list"]) == 0
    out_list = capsys.readouterr().out
    assert "STV-LS-001" in out_list

    assert manage_inventory_main(["--db-path", cli_db, "restock", "STV-LS-001", "5"]) == 0
    out_restock = capsys.readouterr().out
    assert "Updated STV-LS-001" in out_restock

    assert (
        manage_inventory_main(["--db-path", cli_db, "set-stock", "STV-LS-001", "12"])
        == 0
    )
    out_set = capsys.readouterr().out
    assert "-> 12." in out_set

    assert (
        sales_report_main(
            ["--db-path", cli_db, "--exports-dir", cli_exports, "--export-csv", "all"]
        )
        == 0
    )
    out_report = capsys.readouterr().out
    assert "SETUVO — SALES & INVENTORY ANALYTICS REPORT" in out_report
    assert "Exported Sales CSV" in out_report
    assert "Exported Inventory CSV" in out_report