# CONTEXT-chat-api.md
> Feature-specific context document for chat-api.
> Read alongside SPEC-chat-api.md when writing/regenerating tests.

---

## File Structure

```
alita_agent/api.py
  chat_agent          line 24 — Agent built from agent.py's shared config, minus `login`
  session_service     line 26 — InMemorySessionService()
  runner              line 27 — Runner(agent=chat_agent, ...)
  chat()              line 48 — POST /chat handler

tests/integration/chat_api/
  test_chat_endpoint.py   AC-CHATAPI-I01..I06
```

## Request/response models

```python
class ChatRequest(BaseModel):
    session_id: str
    user_id: str
    message: str

class ChatResponse(BaseModel):
    reply: str
```

## Handler flow (`chat()`, api.py:48-79)

```
1. Validate Authorization header starts with "Bearer " -> 401 if not.
2. session_service.get_session(app_name, user_id, session_id) -> None if new.
3. If new: session_service.create_session(..., state={"access_token": token}).
4. Build types.Content(role="user", parts=[types.Part(text=message)]).
5. runner.run_async(user_id, session_id, new_message=content,
                     state_delta={"access_token": token})
   -> async generator of Event; last non-empty text part across all events = reply.
6. Return ChatResponse(reply=...).
```

## Test harness pattern (already exercised manually during development)

```python
import httpx
transport = httpx.ASGITransport(app=api.app)
async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
    resp = await ac.post("/chat", headers={"Authorization": f"Bearer {token}"},
                          json={"session_id": "s1", "user_id": "u1", "message": "..."})
```

The `fake_ecommerce_calls` fixture monkeypatches `EcommerceClient.request` (imported as
`ecommerce_client` in the test module) with a recording async stub, so tool calls never hit the
network — only the Gemini call goes out for real, hence the `GOOGLE_API_KEY` requirement noted in
the SPEC:

```python
async def fake_request(method, path, token=None, **kwargs):
    calls.append((method, path, token))
    return httpx.Response(200, request=httpx.Request(method, path), json={...})

monkeypatch.setattr(ecommerce_client, "request", fake_request)
```

To inspect session state after a call (for I03/I06):
```python
session = await api.session_service.get_session(
    app_name=api.APP_NAME, user_id="u1", session_id="s1")
session.state["access_token"]  # what the *next* tool call would use
```

---

## References
- [SPEC-chat-api.md](./SPEC-chat-api.md)
- [../auth/CONTEXT-auth.md](../auth/CONTEXT-auth.md)
