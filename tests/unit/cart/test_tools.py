import httpx
import respx

from alita_agent.tools import get_my_cart

TEST_BASE_URL = "http://test-ecommerce-api"


@respx.mock
async def test_get_my_cart_success_nests_under_cart(test_client, tool_context):
    """AC-CART-U01"""
    body = {
        "cart_id": "c1111111-1111-1111-1111-111111111111",
        "items": [
            {
                "id": "i1111111-1111-1111-1111-111111111111",
                "product_id": "p1111111-1111-1111-1111-111111111111",
                "product_name": "Tênis Azul",
                "product_slug": "tenis-azul-42",
                "image_url": "https://example.com/tenis.jpg",
                "unit_price": 129.9,
                "quantity": 2,
                "subtotal": 259.8,
            }
        ],
        "total": 259.8,
        "item_count": 1,
        "updated_at": "2026-07-14T00:00:00Z",
    }
    respx.get(f"{TEST_BASE_URL}/api/v1/cart").mock(return_value=httpx.Response(200, json=body))

    result = await get_my_cart(tool_context)

    assert result == {"status": "success", "cart": body}


@respx.mock
async def test_get_my_cart_empty_cart_is_still_success(test_client, tool_context):
    """AC-CART-U02"""
    body = {
        "cart_id": "c1111111-1111-1111-1111-111111111111",
        "items": [],
        "total": 0,
        "item_count": 0,
        "updated_at": "2026-07-14T00:00:00Z",
    }
    respx.get(f"{TEST_BASE_URL}/api/v1/cart").mock(return_value=httpx.Response(200, json=body))

    result = await get_my_cart(tool_context)

    assert result == {"status": "success", "cart": body}


@respx.mock
async def test_get_my_cart_expired_token_returns_friendly_error(test_client, tool_context):
    """AC-CART-U03"""
    respx.get(f"{TEST_BASE_URL}/api/v1/cart").mock(
        return_value=httpx.Response(401, json={"detail": "Unauthorized"})
    )

    result = await get_my_cart(tool_context)

    assert result == {"status": "error", "message": "Sessão expirada, faça login novamente."}
