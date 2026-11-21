"""tests/test_routes_and_analytics.py

Tests health check API, Pandas/Plotly analytics dashboard, CSV export endpoints,
and HTTP error handlers.
"""


def test_api_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["currency"] == "NGN"
    assert data["tables_ready"] is True
    assert data["active_products"] == 20


def test_analytics_dashboard_and_csv_downloads(seeded_orders_client):
    dash = seeded_orders_client.get("/analytics")
    html = dash.get_data(as_text=True)
    assert dash.status_code == 200
    assert "Sales &amp; Inventory Analytics" in html
    assert "plotly" in html.lower()

    sales_csv = seeded_orders_client.get("/analytics/export/sales")
    assert sales_csv.status_code == 200
    assert "text/csv" in sales_csv.content_type
    assert "order_number" in sales_csv.get_data(as_text=True)

    inv_csv = seeded_orders_client.get("/analytics/export/inventory")
    assert inv_csv.status_code == 200
    assert "text/csv" in inv_csv.content_type
    assert "STV-LS-001" in inv_csv.get_data(as_text=True)


def test_custom_404_error_page(client):
    resp = client.get("/this-route-does-not-exist-on-setuvo")
    assert resp.status_code == 404
    assert "Page Not Found" in resp.get_data(as_text=True)