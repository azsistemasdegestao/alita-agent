# CONTEXT-cart.md
> Feature-specific context document for cart.
> Read alongside SPEC-cart.md when writing/regenerating tests.

---

## File Structure

```
alita_agent/tools.py
  get_my_cart()   line ~136

tests/unit/cart/
  test_tools.py   AC-CART-U01..U03
```

## Real API endpoint touched (mocked with respx in tests)

```
GET {base_url}/api/v1/cart
```

## Response shape (as seen by the tool, snake_case per project convention)

Derived from the Ecommerce API's `CartQueryService.GetByUserIdAsync` (Dapper query joining
`carts`/`cart_items`/`products`) and its `CartDto`/`CartItemDto` records:

```jsonc
// GET /api/v1/cart
{
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
      "subtotal": 259.8
    }
  ],
  "total": 259.8,
  "item_count": 1,
  "updated_at": "2026-07-14T00:00:00Z"
}
```

`items` is `[]` (and `total`/`item_count` are `0`) when the user has no cart yet — the endpoint's
own summary is explicit about this ("Returns the active Cart of the authenticated Customer, or
an empty Cart if none exists"), so the tool never needs to special-case a missing cart.

---

## References
- [SPEC-cart.md](./SPEC-cart.md)
- [../auth/CONTEXT-auth.md](../auth/CONTEXT-auth.md) — `FakeToolContext`/monkeypatch pattern
- [../payments/CONTEXT-payments.md](../payments/CONTEXT-payments.md) — same single-resource
  nested-response pattern this feature follows
