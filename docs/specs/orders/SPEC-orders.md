# SPEC-orders.md
> Feature: Order lookup tools
> Phase: 1
> Status: Draft

## Context
- [CONTEXT-orders.md](./CONTEXT-orders.md)
- [../auth/SPEC-auth.md](../auth/SPEC-auth.md) — shared `_request()` auth/error handling

---

## Overview

Two read-only ADK tools letting the LLM list the authenticated user's orders and check a specific
order's status. Same `_request()`-mediated auth/error handling as `catalog`.

---

## Tools

### `get_my_orders(tool_context, page_number=1, page_size=10) -> dict`
`alita_agent/tools.py:106`

- Calls `GET /api/v1/orders?page_number&page_size`.
- Success: `{"status": "success", **response_json}` (spread, like `search_products`).

### `get_order_status(order_id, tool_context) -> dict`
`alita_agent/tools.py:120`

- Calls `GET /api/v1/orders/{order_id}`.
- Success: `{"status": "success", "order": response_json}` (nested, like `get_product_details`).

---

## Business Rules

- `BR-ORDERS-001` `get_my_orders` always sends `page_number`/`page_size`, defaulting to `1`/`10`.
- `BR-ORDERS-002` `get_my_orders`'s response is spread at the top level; `get_order_status`'s is
  nested under `"order"`.
- `BR-ORDERS-003` A `401` is returned as the standard friendly error dict, never raised.

---

## Validation Criteria

### Unit Tests

| ID | Scenario | Input | Expected |
|----|----------|-------|----------|
| AC-ORDERS-U01 | `get_my_orders` default pagination | No args beyond `tool_context` | `GET /orders?page_number=1&page_size=10` |
| AC-ORDERS-U02 | `get_my_orders` custom pagination | `page_number=2, page_size=5` | `GET /orders?page_number=2&page_size=5` |
| AC-ORDERS-U03 | `get_my_orders` success | Mocked 200 with `items`/`total_count` | Result `{"status": "success", **body}` |
| AC-ORDERS-U04 | `get_my_orders` with expired token | Mocked `401` | Friendly error dict |
| AC-ORDERS-U05 | `get_order_status` success | Valid `order_id`, mocked 200 order body | `GET /orders/{order_id}`; result `{"status": "success", "order": body}` |
| AC-ORDERS-U06 | `get_order_status` with expired token | Mocked `401` | Friendly error dict |

### Integration Tests

N/A for this feature in isolation — covered end-to-end by `chat-api`'s `AC-CHATAPI-I*` tests.

---

## Dependencies

| Dependency | Type | Reason |
|------------|------|--------|
| `respx` | Test | Mocks `GET /api/v1/orders*` |

## Feature Dependencies
- `auth` — token resolution and 401 handling come from the shared `_request()` helper.

---

## Implementation Notes
- Tests live in `tests/unit/orders/test_tools.py`.
- Reuse the same `FakeToolContext` and monkeypatched `client` pattern from `auth`'s CONTEXT doc.
