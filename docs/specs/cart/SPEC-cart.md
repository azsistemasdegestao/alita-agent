# SPEC-cart.md
> Feature: Shopping cart lookup tool
> Phase: 1
> Status: Draft

## Context
- [CONTEXT-cart.md](./CONTEXT-cart.md)
- [../auth/SPEC-auth.md](../auth/SPEC-auth.md) — shared `_request()` auth/error handling

---

## Overview

Single read-only ADK tool letting the LLM check the authenticated user's current shopping cart
(items, quantities, unit prices, subtotal, total). Still read-only per the project's scope —
this only *looks at* the cart, it does not add/remove/change items in it.

---

## Tools

### `get_my_cart(tool_context) -> dict`
`alita_agent/tools.py`

- Calls `GET /api/v1/cart`.
- The Ecommerce API guarantees a `200` with a `CartDto` body even when the user has no cart yet
  (`items: []`, `total: 0`, `item_count: 0`) — never a `404`/`null` for "no cart".
- Success: `{"status": "success", "cart": response_json}` (nested, same pattern as
  `get_order_status`/`get_payment_status`/`get_product_details` — single-resource lookups nest).

---

## Business Rules

- `BR-CART-001` Response is nested under `"cart"`, matching the single-resource lookup pattern
  (`get_order_status`, `get_payment_status`, `get_product_details`).
- `BR-CART-002` An empty cart (`items: []`) is a normal success response, not an error or an
  "empty" status — unlike `answer_from_faq`, which has an explicit `"empty"` status for
  no-match. The Ecommerce API itself is responsible for materializing an empty `CartDto` when no
  cart row exists for the user.
- `BR-CART-003` A `401` from the Ecommerce API is returned as the standard friendly error dict,
  never raised.

---

## Validation Criteria

### Unit Tests

| ID | Scenario | Input | Expected |
|----|----------|-------|----------|
| AC-CART-U01 | `get_my_cart` success with items | Mocked 200 `CartDto` with one item | `GET /api/v1/cart`; result `{"status": "success", "cart": body}` |
| AC-CART-U02 | `get_my_cart` success, empty cart | Mocked 200 `CartDto` with `items: []` | Still `{"status": "success", "cart": body}`, not an error |
| AC-CART-U03 | `get_my_cart` with expired token | Mocked `401` | `{"status": "error", "message": "Sessão expirada, faça login novamente."}` |

### Integration Tests

N/A for this feature in isolation — covered end-to-end by `chat-api`'s `AC-CHATAPI-I*` tests.

---

## Dependencies

| Dependency | Type | Reason |
|------------|------|--------|
| `respx` | Test | Mocks `GET /api/v1/cart` |

## Feature Dependencies
- `auth` — token resolution and 401 handling come from the shared `_request()` helper.

---

## Implementation Notes
- Tests live in `tests/unit/cart/test_tools.py`.
- Reuse the same `FakeToolContext` and monkeypatched `client` pattern from `auth`'s CONTEXT doc.
- Response field names (snake_case, confirmed against the Ecommerce API's `CartDto`/`CartItemDto`
  records): `cart_id`, `items` (`id`, `product_id`, `product_name`, `product_slug`, `image_url`,
  `unit_price`, `quantity`, `subtotal`), `total`, `item_count`, `updated_at`.
