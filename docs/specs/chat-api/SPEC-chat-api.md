# SPEC-chat-api.md
> Feature: FastAPI chat endpoint (per-user auth + session continuity)
> Phase: 1
> Status: Draft

## Context
- [CONTEXT-chat-api.md](./CONTEXT-chat-api.md)
- [../auth/SPEC-auth.md](../auth/SPEC-auth.md)
- [../../../CLAUDE.md](../../../CLAUDE.md) — "Auth model" section

---

## Overview

`POST /chat` (`alita_agent/api.py`) is the HTTP surface the storefront chat widget talks to. It
takes the caller's own JWT from the `Authorization` header and threads it through ADK session
state into every tool call for that turn, using `Runner` + `InMemorySessionService` to keep
conversation history per `(user_id, session_id)`. It runs a separate `chat_agent` (not
`root_agent`) that excludes the `login` tool.

---

## Endpoints

### POST /chat

- **Auth:** Caller-supplied `Authorization: Bearer <jwt>` header, forwarded as-is (the agent never
  logs in on the caller's behalf).

**Request:**
```json
{
  "session_id": "s1",
  "user_id": "u1",
  "message": "quais são meus pedidos?"
}
```

**Response 200 OK:**
```json
{ "reply": "..." }
```

**Errors:**
| Status | Reason |
|--------|--------|
| 401 | `Authorization` header present but missing the `Bearer ` prefix |
| 422 | `Authorization` header missing entirely, or request body fails validation (FastAPI/Pydantic default) |

---

## Business Rules

- `BR-CHATAPI-001` A new ADK session is created (seeded with `state={"access_token": token}`) only
  if `(app_name, user_id, session_id)` doesn't already exist; otherwise the existing session (and
  its conversation history) is reused.
- `BR-CHATAPI-002` Every turn's `access_token` is pushed into session state via `state_delta`,
  regardless of whether the session was just created or already existed — so a token that rotates
  between messages (frontend-side refresh) is always the one tools see for that turn.
- `BR-CHATAPI-003` The reply returned to the caller is the last non-empty text part across all
  events yielded by `runner.run_async` for that turn.
- `BR-CHATAPI-004` `chat_agent` (used here) never has the `login` tool — production traffic must
  never be able to authenticate as an arbitrary account via a password typed into chat.

---

## Validation Criteria

### Unit Tests

N/A — this feature has no logic that's meaningfully unit-testable in isolation from the ADK
`Runner`/session plumbing; see Integration Tests below.

### Integration Tests

All of these require a real `GOOGLE_API_KEY` (real Gemini calls through the real ADK `Runner`).
Ecommerce API calls are faked by monkeypatching `EcommerceClient.request` directly (see
Implementation Notes) rather than mocking at the `httpx` transport level. Skipped automatically if
`GOOGLE_API_KEY` isn't set.

| ID | Scenario | Input | Expected |
|----|----------|-------|----------|
| AC-CHATAPI-I01 | Missing `Authorization` header | No header at all | `422` |
| AC-CHATAPI-I02 | `Authorization` header without `Bearer ` prefix | `Authorization: token123` | `401`, detail `"Missing bearer token"` |
| AC-CHATAPI-I03 | New session, valid token | Fresh `session_id`/`user_id`, `Bearer <token>` | `200`; ADK session created with `state["access_token"] == token`; non-empty `reply` |
| AC-CHATAPI-I04 | Second turn, same session | Same `session_id`/`user_id` as I03, new message referencing the prior turn | `200`; session reused (not recreated); ADK session history has entries from both turns |
| AC-CHATAPI-I05 | Token forwarded to a tool call | Message that reliably triggers `get_my_orders` (e.g. "quais são meus pedidos?"), faked `EcommerceClient.request` | The faked call's `token` arg equals the token from this request's header |
| AC-CHATAPI-I06 | Token rotates between turns, same session | Turn 1 with `token-a`, turn 2 (tool-triggering message) with `token-b` | Turn 2's tool call uses `token-b`, not the stale `token-a` |

---

## Dependencies

| Dependency | Type | Reason |
|------------|------|--------|
| Real `GOOGLE_API_KEY` | Test (integration only) | Runner drives a real Gemini model — no ADK-level fake-LLM harness is used here |

## Feature Dependencies
- `auth`, `catalog`, `orders`, `payments` — any of these tools may be invoked by the LLM during a
  turn depending on the user's message.

---

## Implementation Notes
- Tests live in `tests/integration/chat_api/test_chat_endpoint.py`.
- Drive `alita_agent.api.app` via `httpx.ASGITransport` (see the manual verification pattern used
  during development — this SPEC formalizes it into pytest).
- **Don't use `respx` here.** It was tried first and found to globally patch `httpx`'s transport
  dispatch for the whole process, which broke the real Gemini call these tests also make (the
  model silently returned empty candidates whenever `respx.mock` was active, even with
  `assert_all_mocked=False` for passthrough). Instead, the `fake_ecommerce_calls` fixture
  monkeypatches `EcommerceClient.request` directly — a plain attribute swap on one object, with no
  effect on Gemini's own `httpx` client.
- The LLM call itself is real (not mocked) — building a fake ADK-compatible LLM model was
  considered and rejected as disproportionate effort for this project's size; instead these tests
  are marked `@pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="requires a real Gemini key")`.
