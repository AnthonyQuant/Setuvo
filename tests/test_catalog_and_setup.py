"""tests/test_catalog_and_setup.py

Tests product catalogue search, multi-criteria filtering, sorting, product detail
specifications, side-by-side comparison, Setup Builder budget checks, and bundles.
"""


def test_homepage_and_seeded_catalogue_display(client):
    resp = client.get("/")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Nexstand K2" in html
    assert "Programming Starter Kit" in html
    assert "₦" in html


def test_catalogue_keyword_price_and_sort_filtering(client):
    resp = client.get(
        "/catalogue?q=keyboard&min_price=20000&max_price=90000&sort_by=price_asc"
    )
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Keychron K2" in html
    assert "Logitech MX Keys" not in html


def test_product_detail_and_three_way_spec_comparison(client):
    detail = client.get("/product/1")
    detail_html = detail.get_data(as_text=True)
    assert detail.status_code == 200
    assert "Technical Specifications" in detail_html

    compare = client.get("/compare?ids=1,2,3")
    compare_html = compare.get_data(as_text=True)
    assert compare.status_code == 200
    assert "Comparing 3 Items" in compare_html
    assert "Differs" in compare_html


def test_setup_builder_over_budget_warning_and_add_to_cart(client):
    over_resp = client.post(
        "/setup-builder",
        data={
            "purpose": "programming",
            "budget": "40000",
            "product_ids": ["1", "4"],
        },
    )
    over_html = over_resp.get_data(as_text=True)
    assert over_resp.status_code == 200
    assert "Budget Exceeded" in over_html

    add_resp = client.post(
        "/setup-builder/add-to-cart",
        data={
            "purpose": "programming",
            "budget": "150000",
            "product_ids": ["1", "4"],
        },
        follow_redirects=True,
    )
    cart_html = add_resp.get_data(as_text=True)
    assert add_resp.status_code == 200
    assert "Your Shopping Cart" in cart_html
    assert "Nexstand K2" in cart_html


def test_preconfigured_bundles_page_and_add_to_cart(client):
    page = client.get("/bundles")
    assert page.status_code == 200
    assert "Student Essentials Kit" in page.get_data(as_text=True)

    add_kit = client.post(
        "/bundles/student-essentials-kit/add-to-cart",
        follow_redirects=True,
    )
    html = add_kit.get_data(as_text=True)
    assert add_kit.status_code == 200
    assert "Student Essentials Kit" in html