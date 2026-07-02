# CONTEXT-payments.md
> Feature-specific context document for payments.
> Read alongside SPEC-payments.md when writing/regenerating tests.

---

## File Structure

```
alita_agent/tools.py
  get_payment_status()  line 135

tests/unit/payments/
  test_tools.py   AC-PAYMENTS-U01..U02
```

## Real API endpoint touched (mocked with respx in tests)

```
GET {base_url}/api/v1/payments/{order_id}
```

## Response shape (as seen by the tool, snake_case per project convention)

```jsonc
{ "order_id": "...", "status": "APPROVED", "amount": 199.9, ... }
```

---

## References
- [SPEC-payments.md](./SPEC-payments.md)
- [../auth/CONTEXT-auth.md](../auth/CONTEXT-auth.md) — `FakeToolContext` / monkeypatch pattern
