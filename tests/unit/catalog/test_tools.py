import httpx
import respx

from alita_agent.tools import get_product_details, search_products

TEST_BASE_URL = "http://test-ecommerce-api"


@respx.mock
async def test_search_products_with_no_filters_sends_only_pagination(test_client, tool_context):
    """AC-CATALOG-U01"""
    route = respx.get(f"{TEST_BASE_URL}/api/v1/catalog/products").mock(
        return_value=httpx.Response(
            200, json={"items": [], "total_count": 0, "has_next_page": False}
        )
    )

    await search_products(tool_context)

    sent_params = dict(route.calls.last.request.url.params)
    assert sent_params == {"page_number": "1", "page_size": "10"}


@respx.mock
async def test_search_products_with_filters_sends_only_given_ones(test_client, tool_context):
    """AC-CATALOG-U02"""
    route = respx.get(f"{TEST_BASE_URL}/api/v1/catalog/products").mock(
        return_value=httpx.Response(
            200, json={"items": [], "total_count": 0, "has_next_page": False}
        )
    )

    await search_products(
        tool_context, search="tenis", min_price=50, category_slug="calcados"
    )

    sent_params = dict(route.calls.last.request.url.params)
    assert sent_params == {
        "page_number": "1",
        "page_size": "10",
        "search": "tenis",
        "min_price": "50",
        "category_slug": "calcados",
    }


@respx.mock
async def test_search_products_success_spreads_response(test_client, tool_context):
    """AC-CATALOG-U03"""
    body = {"items": [{"id": "p1"}], "total_count": 1, "has_next_page": False}
    respx.get(f"{TEST_BASE_URL}/api/v1/catalog/products").mock(
        return_value=httpx.Response(200, json=body)
    )

    result = await search_products(tool_context)

    assert result == {"status": "success", **body}


@respx.mock
async def test_search_products_expired_token_returns_friendly_error(test_client, tool_context):
    """AC-CATALOG-U04"""
    respx.get(f"{TEST_BASE_URL}/api/v1/catalog/products").mock(
        return_value=httpx.Response(401, json={"detail": "Unauthorized"})
    )

    result = await search_products(tool_context)

    assert result == {"status": "error", "message": "Sessão expirada, faça login novamente."}


@respx.mock
async def test_get_product_details_success_nests_under_product(test_client, tool_context):
    """AC-CATALOG-U05"""
    body = {"id": "p1", "slug": "tenis-azul-42", "name": "Tênis Azul", "price": 129.9}
    respx.get(f"{TEST_BASE_URL}/api/v1/catalog/products/tenis-azul-42").mock(
        return_value=httpx.Response(200, json=body)
    )

    result = await get_product_details("tenis-azul-42", tool_context)

    assert result == {"status": "success", "product": body}


@respx.mock
async def test_get_product_details_expired_token_returns_friendly_error(
    test_client, tool_context
):
    """AC-CATALOG-U06"""
    respx.get(f"{TEST_BASE_URL}/api/v1/catalog/products/tenis-azul-42").mock(
        return_value=httpx.Response(401, json={"detail": "Unauthorized"})
    )

    result = await get_product_details("tenis-azul-42", tool_context)

    assert result == {"status": "error", "message": "Sessão expirada, faça login novamente."}
