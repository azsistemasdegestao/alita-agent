# CONTEXT-orders.md
> Feature-specific context document for orders.
> Read alongside SPEC-orders.md when writing/regenerating tests.

---

## File Structure

```
alita_agent/tools.py
  get_my_orders()     line 106
  get_order_status()  line 120

tests/unit/orders/
  test_tools.py   AC-ORDERS-U01..U06
```

## Real API endpoints touched (mocked with respx in tests)

```
GET {base_url}/api/v1/orders             ?page_number&page_size
GET {base_url}/api/v1/orders/{order_id}
```

## Response shapes (as seen by the tool, snake_case per project convention)

```jsonc
// GET /api/v1/orders
{ "items": [{"id": "...", "status": "PAID", ...}], "total_count": 1, "has_next_page": false }

// GET /api/v1/orders/{order_id}
{ "id": "...", "status": "SHIPPED", "total": 199.9, ... }
```

---

## References
- [SPEC-orders.md](./SPEC-orders.md)
- [../auth/CONTEXT-auth.md](../auth/CONTEXT-auth.md) — `FakeToolContext` / monkeypatch pattern
