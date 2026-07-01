# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`alita-agent` is a Google ADK (Agent Development Kit) Python agent that acts as a customer-facing
chatbot for the e-commerce project. It is a separate, independently-run project from the sibling
repos `../ecommerce-api` (Clean Architecture .NET 10 REST API) and `../frontend` (Angular SSR). It
talks to the API only over HTTP/JWT — it has no direct DB or cache access.

## Commands

```bash
# Run the agent interactively in the terminal (loads alita_agent/.env automatically)
adk run alita_agent

# Run the agent with the ADK web UI (inspect tool calls/args/responses at http://localhost:8000)
adk web

# Run the HTTP chat API used by the storefront (loads alita_agent/.env via python-dotenv)
uvicorn alita_agent.api:app --reload --port 8001
```

There is no test suite, lint config, or build step yet, and no `requirements.txt`/`pyproject.toml`
— dependencies (`google-adk`, `httpx`, `fastapi`, `uvicorn`) are currently installed directly into
the system/venv Python (`fastapi`/`uvicorn`/`python-dotenv` already come in transitively via
`google-adk`). Running any file with plain `python` (instead of `adk run`/`adk web`) does **not**
load `.env` automatically; required env vars must be exported manually or loaded with
`python-dotenv` first — `alita_agent/api.py` does this itself since `uvicorn` won't.

## Architecture

- `alita_agent/agent.py` — defines `root_agent`, a Gemini-backed `Agent`. Model is
  `gemini-flash-lite-latest` (chosen over `gemini-flash-latest`/`gemini-3.5-flash` because it has a
  separate, less easily exhausted free-tier quota bucket). Registers the tools from `tools.py`; no
  login happens here — auth is handled per-request (see Auth model below).
- `alita_agent/ecommerce_client.py` — `EcommerceClient`, an async `httpx` wrapper around the
  Ecommerce API (default `http://localhost:8080`, overridable via `ECOMMERCE_API_URL`).
  `request(method, path, token=..., **kwargs)` uses the given bearer `token` directly when one is
  supplied (the normal/production path). When called with no `token` (only happens under
  `adk run`/`adk web`, which have no per-request auth context), it falls back to logging in itself
  with `ECOMMERCE_AGENT_EMAIL`/`ECOMMERCE_AGENT_PASSWORD` and transparently refreshing
  (`POST /api/v1/auth/refresh`) ~30s before the 1h expiry — purely so the agent can still be
  exercised standalone for local testing. A single module-level `client` instance (one shared
  `httpx.AsyncClient` connection pool) is reused by every tool call; no per-user state lives on it
  when a token is supplied per-call.
- `alita_agent/tools.py` — the ADK tools (async Python functions) the LLM can call:
  `search_products`, `get_product_details`, `get_my_orders`, `get_order_status`,
  `get_payment_status`. Each takes a `tool_context: ToolContext` parameter that ADK injects
  automatically (excluded from the schema shown to the model) and reads the user's access token
  from `tool_context.state["access_token"]`. Each wraps one read-only Ecommerce API endpoint.
  **Docstrings are load-bearing** — ADK passes them to the model to decide when/how to call each
  tool, so keep them accurate and example-driven when adding new ones. All API response fields are
  `snake_case`.
- `alita_agent/api.py` — FastAPI app exposing `POST /chat` for the storefront chat widget. Expects
  an `Authorization: Bearer <jwt>` header (the caller's own token, forwarded as-is — the API never
  logs in) and a JSON body of `{session_id, user_id, message}`. Uses ADK's `Runner` +
  `InMemorySessionService` to keep conversation history per `(user_id, session_id)`, and seeds/
  refreshes `access_token` into that session's state on every turn via `state_delta` so tools can
  read it — this is what makes each chat session act as the actual calling user instead of a
  shared service account.

### Scope: read-only by design

Only query/read tools are wired up so far. Tools that would mutate state (add to cart, create
order, cancel order, request payment) are intentionally not exposed yet — `root_agent`'s
instruction explicitly forbids taking such actions without explicit user confirmation, and no tool
for them currently exists. Add mutating tools deliberately, not as a side effect of adding a new
read tool.

### Auth model

The FastAPI `/chat` endpoint (`api.py`) is per-user: it takes the caller's own JWT from the
`Authorization` header and threads it through ADK session state into every tool call for that
turn, so each chat session acts as whichever storefront user is actually calling it (no shared
account, no direct DB/token knowledge needed by the agent). Token refresh is entirely the
frontend's responsibility — the API just forwards whatever bearer token arrives with each request.

`ECOMMERCE_AGENT_EMAIL`/`ECOMMERCE_AGENT_PASSWORD` are **only** used by `ecommerce_client.py`'s
fallback login path, which activates when a tool call has no token in session state — i.e. only
when running via `adk run`/`adk web` directly (no FastAPI request context to source a token from).
That path is for local agent testing/debugging only and is never hit by real `/chat` traffic.

## Configuration

`alita_agent/.env` (gitignored) holds:
- `GOOGLE_API_KEY`, `GOOGLE_GENAI_USE_ENTERPRISE` — Gemini API credentials.
- `ECOMMERCE_API_URL` — base URL of the Ecommerce API.
- `ECOMMERCE_AGENT_EMAIL` / `ECOMMERCE_AGENT_PASSWORD` — Ecommerce API user used only by the
  `adk run`/`adk web` fallback login (see Auth model above); must already exist — register via
  `POST /api/v1/auth/register` on the target API first.
- `FRONTEND_ORIGIN` — origin allowed by `api.py`'s CORS policy for `/chat` (default
  `http://localhost:4200`).

The target Ecommerce API must be running (`docker-compose up` from `../ecommerce-api`) before the
agent can call any tool.
