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

# Run the HTTP chat API in Docker, joining the shared ecommerce-network so it
# can reach ecommerce-api by its service name. ecommerce-api (and, if you
# want CORS to work end-to-end, frontend) must already be up first — same
# convention frontend's own docker-compose.yml follows.
docker-compose up --build

# Install dev deps (pytest, pytest-asyncio, respx) and run the test suite
pip install -r requirements-dev.txt
pytest                    # runs both unit and integration
pytest tests/unit         # no external dependencies (no network, no API key)
pytest tests/integration  # requires a real GOOGLE_API_KEY in alita_agent/.env
                          # (skipped automatically otherwise)
```

There is no lint config yet. Dependencies are pinned in `requirements.txt`
(`google-adk`, `httpx`, `fastapi`, `uvicorn`, `python-dotenv`) for the Docker build; outside Docker
they're still installed directly into the system/venv Python (`pip install -r requirements.txt`
works there too). Running any file with plain `python` (instead of `adk run`/`adk web`) does **not**
load `.env` automatically; required env vars must be exported manually or loaded with
`python-dotenv` first — `alita_agent/api.py` does this itself since `uvicorn` won't.

## Architecture

- `alita_agent/agent.py` — defines `root_agent`, a Gemini-backed `Agent` discovered by convention
  by `adk run`/`adk web`. Model is `gemini-flash-lite-latest` (chosen over
  `gemini-flash-latest`/`gemini-3.5-flash` because it has a separate, less easily exhausted
  free-tier quota bucket). Exports `MODEL`/`NAME`/`DESCRIPTION`/`INSTRUCTION`/`CHAT_TOOLS` as shared
  building blocks so `api.py` can build its own agent instance from the same config. `root_agent`
  additionally includes the `login` tool (email/senha) for CLI/web testing — see Auth model below
  for why that tool is excluded from the FastAPI agent.
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
  `get_payment_status`, and `login`. Each of the first five takes a `tool_context: ToolContext`
  parameter that ADK injects automatically (excluded from the schema shown to the model) and reads
  the user's access token from `tool_context.state["access_token"]`; each wraps one read-only
  Ecommerce API endpoint. `login(email, password, tool_context)` calls
  `EcommerceClient.login()` and writes the resulting token into `tool_context.state["access_token"]`
  — CLI/web-only (see Auth model below), never exposed to the FastAPI chat agent. **Docstrings are
  load-bearing** — ADK passes them to the model to decide when/how to call each tool, so keep them
  accurate and example-driven when adding new ones. All API response fields are `snake_case`.
- `alita_agent/observability.py` — bootstrap module (Python equivalent of `frontend/src/instrument.mts`),
  called from `api.py` right after the `FastAPI()` instance is created. Registers a global
  `TracerProvider` exporting spans via OTLP/gRPC to Jaeger (`JAEGER_ENDPOINT`), instruments FastAPI
  and `httpx` (so `ecommerce_client.py`'s client and google-adk's own Gemini HTTP calls get traced
  automatically, no code changes needed there), adds a `GET /metrics` route backed by a real OTel
  `PrometheusMetricReader`, and attaches a `LokiLoggerHandler` (label `app=alita-agent`) to the root
  logger so log lines are pushed to Loki alongside traces/metrics. Only covers the FastAPI (`api.py`)
  path — `adk run`/`adk web` remain uninstrumented by design, since they're local dev/debug entry
  points, not the production traffic path. All new `opentelemetry-*` packages are pinned to versions
  compatible with `google-adk`'s own `opentelemetry-api`/`-sdk` ceiling (`<=1.42.1`); bumping past
  that requires checking google-adk's dependency constraints first.
- `alita_agent/api.py` — FastAPI app exposing `POST /chat` for the storefront chat widget. Builds
  its own `chat_agent` from `agent.py`'s shared config (same model/instruction/tools, minus
  `login`). Expects an `Authorization: Bearer <jwt>` header (the caller's own token, forwarded
  as-is — the API never logs in) and a JSON body of `{session_id, user_id, message}`. Uses ADK's
  `Runner` + `InMemorySessionService` to keep conversation history per `(user_id, session_id)`, and
  seeds/refreshes `access_token` into that session's state on every turn via `state_delta` so tools
  can read it — this is what makes each chat session act as the actual calling user instead of a
  shared service account.

### Scope: read-only by design

Only query/read tools are wired up so far. Tools that would mutate state (add to cart, create
order, cancel order, request payment) are intentionally not exposed yet — `root_agent`'s
instruction explicitly forbids taking such actions without explicit user confirmation, and no tool
for them currently exists. Add mutating tools deliberately, not as a side effect of adding a new
read tool.

### Specs and tests

`docs/specs/<feature>/SPEC-<feature>.md` + `CONTEXT-<feature>.md` mirror the spec-driven convention
used in `../ecommerce-api/docs/specs/`: the SPEC's **Validation Criteria** table (IDs
`AC-[FEATURE]-U/I-NN`) is the single source of truth tests are generated from — don't add a test
without a corresponding row, and don't add a row without a test. Features: `auth` (dual-mode
client auth + `login` tool), `catalog`, `orders`, `payments` (the read tools), `chat-api`
(the FastAPI endpoint). Tests live under `tests/unit/<feature>/` (no network, `respx`-mocked
Ecommerce API calls, a `FakeToolContext` stub instead of ADK's real `Context`) and
`tests/integration/chat_api/` (real ADK `Runner` + real Gemini call, Ecommerce API calls faked via
monkeypatching `EcommerceClient.request` directly — **not** `respx`, which was found to interfere
with the real Gemini `httpx` call when both were active in the same process; see
`docs/specs/chat-api/SPEC-chat-api.md`'s Implementation Notes).

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
Alternatively, under `adk run`/`adk web` you can call the `login` tool mid-conversation with any
email/senha to act as that specific user instead of the fallback account — that token also lands in
session state and is used by every subsequent tool call in the conversation.

## Configuration

`alita_agent/.env` (gitignored) holds:
- `GOOGLE_API_KEY`, `GOOGLE_GENAI_USE_ENTERPRISE` — Gemini API credentials.
- `ECOMMERCE_API_URL` — base URL of the Ecommerce API. Defaults to `http://localhost:8080` for
  host-based runs; `docker-compose.yml` overrides this to `http://ecommerce-api:8080` (the Docker
  DNS service name on `ecommerce-network`) when running containerized.
- `ECOMMERCE_AGENT_EMAIL` / `ECOMMERCE_AGENT_PASSWORD` — Ecommerce API user used only by the
  `adk run`/`adk web` fallback login (see Auth model above); must already exist — register via
  `POST /api/v1/auth/register` on the target API first.
- `FRONTEND_ORIGIN` — origin allowed by `api.py`'s CORS policy for `/chat` (default
  `http://localhost:4200`).
- `OTEL_SERVICE_NAME` — `service.name` resource attribute reported to Jaeger. Defaults to
  `alita-agent`.
- `JAEGER_ENDPOINT` — OTLP/gRPC endpoint for trace export. Defaults to `http://localhost:4317` for
  host-based runs; `docker-compose.yml` overrides to `http://jaeger:4317`.
- `LOKI_URL` — Loki push endpoint for logs. Defaults to `http://localhost:3100`; `docker-compose.yml`
  overrides to `http://loki:3100`.

The target Ecommerce API must be running (`docker-compose up` from `../ecommerce-api`) before the
agent can call any tool. When running alita-agent itself via `docker-compose up` (this repo's own
`docker-compose.yml`), it joins the same external `ecommerce-network` bridge that `ecommerce-api`
and `frontend` use, so it can reach `ecommerce-api` by service name — see Commands above. Secrets
(`GOOGLE_API_KEY`, `ECOMMERCE_AGENT_EMAIL`/`PASSWORD`) are supplied via `env_file:
alita_agent/.env` at container runtime, never baked into the image (`.dockerignore` excludes it
from the build context).
