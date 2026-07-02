# CONTEXT-catalog.md
> Feature-specific context document for catalog.
> Read alongside SPEC-catalog.md when writing/regenerating tests.

---

## File Structure

```
alita_agent/tools.py
  search_products()       line 47
  get_product_details()   line 91

tests/unit/catalog/
  test_tools.py   AC-CATALOG-U01..U06
```

## Real API endpoints touched (mocked with respx in tests)

```
GET {base_url}/api/v1/catalog/products          ?page_number&page_size&search&category_slug&min_price&max_price&in_stock
GET {base_url}/api/v1/catalog/products/{slug}
```

## Response shapes (as seen by the tool, snake_case per project convention)

```jsonc
// GET /api/v1/catalog/products
{ "items": [...], "total_count": 1, "has_next_page": false }

// GET /api/v1/catalog/products/{slug}
{ "id": "...", "slug": "...", "name": "...", "price": 129.9, "stock": 5, ... }
```

---

## References
- [SPEC-catalog.md](./SPEC-catalog.md)
- [../auth/CONTEXT-auth.md](../auth/CONTEXT-auth.md) — `FakeToolContext` / monkeypatch pattern
