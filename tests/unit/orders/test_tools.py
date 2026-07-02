import httpx
import respx

from alita_agent.tools import get_my_orders, get_order_status

TEST_BASE_URL = "http://test-ecommerce-api"


@respx.mock
async def test_get_my_orders_default_pagination(test_client, tool_context):
    """AC-ORDERS-U01"""
    route = respx.get(f"{TEST_BASE_URL}/api/v1/orders").mock(
        return_value=httpx.Response(
            200, json={"items": [], "total_count": 0, "has_next_page": False}
        )
    )

    await get_my_orders(tool_context)

    sent_params = dict(route.calls.last.request.url.params)
    assert sent_params == {"page_number": "1", "page_size": "10"}


@respx.mock
async def test_get_my_orders_custom_pagination(test_client, tool_context):
    """AC-ORDERS-U02"""
    route = respx.get(f"{TEST_BASE_URL}/api/v1/orders").mock(
        return_value=httpx.Response(
            200, json={"items": [], "total_count": 0, "has_next_page": False}
        )
    )

    await get_my_orders(tool_context, page_number=2, page_size=5)

    sent_params = dict(route.calls.last.request.url.params)
    assert sent_params == {"page_number": "2", "page_size": "5"}


@respx.mock
async def test_get_my_orders_success_spreads_response(test_client, tool_context):
    """AC-ORDERS-U03"""
    body = {"items": [{"id": "o1", "status": "PAID"}], "total_count": 1, "has_next_page": False}
    respx.get(f"{TEST_BASE_URL}/api/v1/orders").mock(return_value=httpx.Response(200, json=body))

    result = await get_my_orders(tool_context)

    assert result == {"status": "success", **body}


@respx.mock
async def test_get_my_orders_expired_token_returns_friendly_error(test_client, tool_context):
    """AC-ORDERS-U04"""
    respx.get(f"{TEST_BASE_URL}/api/v1/orders").mock(
        return_value=httpx.Response(401, json={"detail": "Unauthorized"})
    )

    result = await get_my_orders(tool_context)

    assert result == {"status": "error", "message": "Sessão expirada, faça login novamente."}


@respx.mock
async def test_get_order_status_success_nests_under_order(test_client, tool_context):
    """AC-ORDERS-U05"""
    body = {"id": "o1", "status": "SHIPPED", "total": 199.9}
    respx.get(f"{TEST_BASE_URL}/api/v1/orders/o1").mock(
        return_value=httpx.Response(200, json=body)
    )

    result = await get_order_status("o1", tool_context)

    assert result == {"status": "success", "order": body}


@respx.mock
async def test_get_order_status_expired_token_returns_friendly_error(test_client, tool_context):
    """AC-ORDERS-U06"""
    respx.get(f"{TEST_BASE_URL}/api/v1/orders/o1").mock(
        return_value=httpx.Response(401, json={"detail": "Unauthorized"})
    )

    result = await get_order_status("o1", tool_context)

    assert result == {"status": "error", "message": "Sessão expirada, faça login novamente."}
