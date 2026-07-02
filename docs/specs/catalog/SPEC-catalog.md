# SPEC-catalog.md
> Feature: Product catalog tools
> Phase: 1
> Status: Draft

## Context
- [CONTEXT-catalog.md](./CONTEXT-catalog.md)
- [../auth/SPEC-auth.md](../auth/SPEC-auth.md) — shared `_request()` auth/error handling

---

## Overview

Two read-only ADK tools that let the LLM search the product catalog and inspect a single product.
Both go through the shared `_request()` helper (`alita_agent/tools.py:7`), which resolves the
token from `tool_context.state["access_token"]` and maps `401` responses to a friendly error dict
instead of raising.

---

## Tools

### `search_products(tool_context, search=None, category_slug=None, min_price=None, max_price=None, in_stock=None, page_number=1, page_size=10) -> dict`
`alita_agent/tools.py:47`

- Calls `GET /api/v1/catalog/products`.
- Every filter param is omitted from the query string when `None` — only `page_number`/`page_size`
  are always sent.
- Success: `{"status": "success", **response_json}` (spreads `items`, `total_count`,
  `has_next_page`, etc. from the API response directly into the result).

### `get_product_details(slug, tool_context) -> dict`
`alita_agent/tools.py:91`

- Calls `GET /api/v1/catalog/products/{slug}`.
- Success: `{"status": "success", "product": response_json}` (nested, unlike `search_products`).

---

## Business Rules

- `BR-CATALOG-001` Filter parameters that are `None` must not appear in the outgoing query string
  at all (not sent as empty string).
- `BR-CATALOG-002` `search_products`'s successful response spreads the API's pagination envelope
  directly at the top level; `get_product_details`'s nests the product under a `"product"` key.
- `BR-CATALOG-003` A `401` from the Ecommerce API is returned as
  `{"status": "error", "message": "Sessão expirada, faça login novamente."}`, never raised.

---

## Validation Criteria

### Unit Tests

| ID | Scenario | Input | Expected |
|----|----------|-------|----------|
| AC-CATALOG-U01 | `search_products` with no filters | All filter args `None`, defaults for pagination | `GET /catalog/products?page_number=1&page_size=10` only — no filter params sent |
| AC-CATALOG-U02 | `search_products` with filters | `search="tenis"`, `min_price=50`, `category_slug="calcados"` | Query string includes exactly those three plus pagination; other filters absent |
| AC-CATALOG-U03 | `search_products` success | Mocked 200 with `items`/`total_count`/`has_next_page` | Result is `{"status": "success", **body}` |
| AC-CATALOG-U04 | `search_products` with expired token | Mocked `401` | `{"status": "error", "message": "Sessão expirada, faça login novamente."}` |
| AC-CATALOG-U05 | `get_product_details` success | Valid `slug`, mocked 200 product body | `GET /catalog/products/{slug}`; result `{"status": "success", "product": body}` |
| AC-CATALOG-U06 | `get_product_details` with expired token | Mocked `401` | Same friendly error dict as U04 |

### Integration Tests

N/A for this feature in isolation — covered end-to-end by `chat-api`'s `AC-CHATAPI-I*` tests.

---

## Dependencies

| Dependency | Type | Reason |
|------------|------|--------|
| `respx` | Test | Mocks `GET /api/v1/catalog/products*` |

## Feature Dependencies
- `auth` — token resolution and 401 handling come from the shared `_request()` helper.

---

## Implementation Notes
- Tests live in `tests/unit/catalog/test_tools.py`.
- Reuse the same `FakeToolContext` and monkeypatched `client` pattern from `auth`'s CONTEXT doc.
