# SPEC-payments.md
> Feature: Payment status lookup tool
> Phase: 1
> Status: Draft

## Context
- [CONTEXT-payments.md](./CONTEXT-payments.md)
- [../auth/SPEC-auth.md](../auth/SPEC-auth.md) — shared `_request()` auth/error handling

---

## Overview

Single read-only ADK tool letting the LLM check the payment status of a specific order.

---

## Tools

### `get_payment_status(order_id, tool_context) -> dict`
`alita_agent/tools.py:135`

- Calls `GET /api/v1/payments/{order_id}`.
- Success: `{"status": "success", "payment": response_json}`.

---

## Business Rules

- `BR-PAYMENTS-001` Response is nested under `"payment"`, matching the `get_order_status`/
  `get_product_details` pattern (single-resource lookups nest; list/search endpoints spread).
- `BR-PAYMENTS-002` A `401` is returned as the standard friendly error dict, never raised.

---

## Validation Criteria

### Unit Tests

| ID | Scenario | Input | Expected |
|----|----------|-------|----------|
| AC-PAYMENTS-U01 | `get_payment_status` success | Valid `order_id`, mocked 200 payment body | `GET /payments/{order_id}`; result `{"status": "success", "payment": body}` |
| AC-PAYMENTS-U02 | `get_payment_status` with expired token | Mocked `401` | Friendly error dict |

### Integration Tests

N/A for this feature in isolation — covered end-to-end by `chat-api`'s `AC-CHATAPI-I*` tests.

---

## Dependencies

| Dependency | Type | Reason |
|------------|------|--------|
| `respx` | Test | Mocks `GET /api/v1/payments/{order_id}` |

## Feature Dependencies
- `auth` — token resolution and 401 handling come from the shared `_request()` helper.

---

## Implementation Notes
- Tests live in `tests/unit/payments/test_tools.py`.
- Reuse the same `FakeToolContext` and monkeypatched `client` pattern from `auth`'s CONTEXT doc.
