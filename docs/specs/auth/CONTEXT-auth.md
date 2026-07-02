# CONTEXT-auth.md
> Feature-specific context document for auth.
> Read alongside SPEC-auth.md when writing/regenerating tests.

---

## File Structure

```
alita_agent/
  ecommerce_client.py   EcommerceClient: request(), _dev_login(), login(), aclose()
  tools.py              login() tool (line 25), _request() helper (line 7)

tests/
  unit/auth/
    test_ecommerce_client.py   AC-AUTH-U01..U05
    test_login_tool.py         AC-AUTH-U06..U09
```

---

## `EcommerceClient` state

```python
self._access_token: str | None   # cached dev-fallback token
self._refresh_token: str | None  # cached dev-fallback refresh token
self._expires_at: float          # unix time, 30s before real expiry
self._dev_login_lock: asyncio.Lock
```

These three fields are **only** touched by `_dev_login()`. The token-supplied path
(`request(..., token=<real token>)`) never reads or writes them — that's what makes it safe to
share one `EcommerceClient` instance across concurrent requests for different users in production.

## Real API endpoints touched (mocked with respx in tests)

```
POST {base_url}/api/v1/auth/login    {"email", "password"} -> {"access_token","refresh_token","expires_in","token_type"}
POST {base_url}/api/v1/auth/refresh  {"refresh_token"}      -> same shape
```

## `login` tool contract

```python
async def login(email: str, password: str, tool_context: ToolContext) -> dict
```
- Success: `{"status": "success", "message": "Login realizado com sucesso."}`, and
  `tool_context.state["access_token"]` set.
- `400`/`401`: `{"status": "error", "message": "Email ou senha inválidos."}`.
- Anything else: exception propagates from `client.login()` (an `httpx.HTTPStatusError`).

## Fake `ToolContext` for unit tests

```python
class FakeToolContext:
    def __init__(self):
        self.state = {}
```
`tools.py` never touches any other attribute of `tool_context`, so this is sufficient — no need to
construct ADK's real `Context`/`InvocationContext` machinery for these tests.

---

## References
- [SPEC-auth.md](./SPEC-auth.md)
- [../../../CLAUDE.md](../../../CLAUDE.md)
