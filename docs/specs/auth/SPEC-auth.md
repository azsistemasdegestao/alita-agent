# SPEC-auth.md
> Feature: Agent-side authentication (dual-mode: per-request token vs. dev fallback)
> Phase: 1
> Status: Draft

## Context
- [CONTEXT-auth.md](./CONTEXT-auth.md)
- [../../../CLAUDE.md](../../../CLAUDE.md) — "Auth model" section

---

## Overview

Unlike `ecommerce-api`'s own auth feature (which issues JWTs), this feature is about how
**alita-agent consumes** JWTs already issued by the Ecommerce API. `EcommerceClient` (
`alita_agent/ecommerce_client.py`) supports two mutually exclusive paths per call:

- **Token-supplied path** (production, via `api.py`'s `/chat`): the caller's own bearer token is
  passed straight through — no login state is touched.
- **Dev-fallback path** (`adk run`/`adk web`, no HTTP request context to source a token from):
  `EcommerceClient` logs itself in with `ECOMMERCE_AGENT_EMAIL`/`ECOMMERCE_AGENT_PASSWORD`, caches
  the token, and refreshes it ~30s before expiry.

The `login` tool (`alita_agent/tools.py:login`) lets a CLI/web-UI user authenticate as a specific
account mid-conversation instead of relying on the fallback account. It is intentionally excluded
from the FastAPI `chat_agent` (see `api.py`).

---

## Tools / Methods

### `EcommerceClient.request(method, path, token=None, **kwargs)`
`alita_agent/ecommerce_client.py:73`

- If `token` is given: used directly as the bearer token for that call.
- If `token` is `None`: resolves a token via `_dev_login()` first.
- Raises `httpx.HTTPStatusError` on any non-2xx response (via `resp.raise_for_status()`).

### `EcommerceClient._dev_login()`
`alita_agent/ecommerce_client.py:31`

- Returns the cached token if still valid (`time.time() < self._expires_at`).
- Otherwise: refreshes via `POST /api/v1/auth/refresh` if a refresh token is held, else logs in
  fresh via `POST /api/v1/auth/login` with `ECOMMERCE_AGENT_EMAIL`/`PASSWORD`.
- Guarded by `asyncio.Lock` so concurrent callers don't double-login/refresh.

### `EcommerceClient.login(email, password)`
`alita_agent/ecommerce_client.py:58`

- `POST /api/v1/auth/login` with the given credentials.
- Returns the raw JSON body (`access_token`, `refresh_token`, `expires_in`, `token_type`).
- Does **not** store anything on the instance — caller decides where the token goes.

### `login(email, password, tool_context) -> dict`
`alita_agent/tools.py:25` — ADK tool, CLI/web-UI only (not on `chat_agent`).

- On success: writes `tool_context.state["access_token"]`, returns
  `{"status": "success", "message": "Login realizado com sucesso."}`.
- On `400`/`401` from the API: returns `{"status": "error", "message": "Email ou senha inválidos."}`
  instead of raising (bad credentials are an expected, recoverable conversational outcome).
- On any other HTTP error status: re-raises (unexpected failure, not something the LLM should try
  to paper over with a canned message).

---

## Business Rules

- `BR-AUTH-001` A per-call `token` argument to `request()` always wins over the dev-login fallback
  — the fallback path is only ever reached when `token is None`.
- `BR-AUTH-002` The dev-login fallback is lazy (no login happens until the first tool call with no
  token) and cached (subsequent calls within the token's lifetime reuse it, no extra HTTP call).
- `BR-AUTH-003` Token refresh happens via `/auth/refresh` (not a fresh `/auth/login`) once a refresh
  token has been obtained, until that refresh token itself is invalid.
- `BR-AUTH-004` `EcommerceClient.login()` never mutates instance state — only the caller (the
  `login` tool, writing to ADK session state) decides where the resulting token is kept.
- `BR-AUTH-005` The `login` tool converts `400`/`401` into a friendly, non-crashing error message;
  any other status code propagates as an exception.

---

## Validation Criteria

### Unit Tests

| ID | Scenario | Input | Expected |
|----|----------|-------|----------|
| AC-AUTH-U01 | `request()` with a token supplied | `token="abc"` | Request sent with `Authorization: Bearer abc`; no call to `/auth/login` |
| AC-AUTH-U02 | `request()` with no token, first call | `token=None`, no cached token | One call to `/auth/login` with `ECOMMERCE_AGENT_EMAIL`/`PASSWORD`; request sent with resulting token |
| AC-AUTH-U03 | `request()` with no token, cached token still valid | `token=None`, second call shortly after U02 | No additional call to `/auth/login`; same cached token reused |
| AC-AUTH-U04 | `request()` with no token, cached token expired | `token=None`, `_expires_at` in the past, refresh token held | Call to `/auth/refresh` (not `/auth/login`); token updated |
| AC-AUTH-U05 | `EcommerceClient.login()` | Arbitrary email/password | `POST /auth/login` with those exact credentials; raw JSON returned; instance state (`_access_token`) untouched |
| AC-AUTH-U06 | `login` tool with valid credentials | Any email/password accepted by the (mocked) API | `tool_context.state["access_token"]` set to the returned token; `{"status": "success", ...}` returned |
| AC-AUTH-U07 | `login` tool with invalid credentials | API returns `401` | `{"status": "error", "message": "Email ou senha inválidos."}`; no exception raised; state untouched |
| AC-AUTH-U08 | `login` tool with malformed request | API returns `400` | Same friendly error dict as U07 |
| AC-AUTH-U09 | `login` tool, unexpected server error | API returns `500` | Exception propagates (not swallowed) |

### Integration Tests

N/A for this feature in isolation — the token-supplied path is exercised end-to-end by the
`chat-api` feature's integration tests (`AC-CHATAPI-I*`), which is the only place a real HTTP
request carries a token through the full stack.

---

## Dependencies

| Dependency | Type | Reason |
|------------|------|--------|
| `respx` | Test | Mocks the Ecommerce API's HTTP responses at the `httpx` transport level |
| `pytest-asyncio` | Test | Runs `async def` test functions |

## Feature Dependencies
- None.

---

## Implementation Notes
- Tests live in `tests/unit/auth/`.
- Use a minimal fake `ToolContext` (an object with a plain `.state = {}` dict) rather than
  constructing a real ADK `Context` — `tools.py` only ever reads/writes `.state`.
- Don't rely on the module-level `client` singleton's real `ECOMMERCE_API_URL` (import-time,
  environment-dependent). Each test constructs its own `EcommerceClient(base_url="http://test-ecommerce-api")`
  and, for `login`-tool tests, monkeypatches `alita_agent.tools.client` to that instance —
  `respx` then mocks exactly `http://test-ecommerce-api/api/v1/auth/*`, independent of whatever
  `.env` happens to be configured.
