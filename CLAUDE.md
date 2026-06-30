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
```

There is no test suite, lint config, or build step yet, and no `requirements.txt`/`pyproject.toml`
— dependencies (`google-adk`, `httpx`) are currently installed directly into the system/venv Python.
Running any file with plain `python` (instead of `adk run`/`adk web`) does **not** load `.env`
automatically; required env vars must be exported manually or loaded with `python-dotenv` first.

## Architecture

- `alita_agent/agent.py` — defines `root_agent`, a Gemini-backed `Agent`. Model is
  `gemini-flash-lite-latest` (chosen over `gemini-flash-latest`/`gemini-3.5-flash` because it has a
  separate, less easily exhausted free-tier quota bucket). At import time it logs into the
  Ecommerce API once via `ECOMMERCE_AGENT_EMAIL`/`ECOMMERCE_AGENT_PASSWORD`, then registers the
  tools from `tools.py`.
- `alita_agent/ecommerce_client.py` — `EcommerceClient`, a thin `httpx` wrapper around the
  Ecommerce API (default `http://localhost:8080`, overridable via `ECOMMERCE_API_URL`). Handles
  JWT login (`POST /api/v1/auth/login`) and transparently refreshes the access token
  (`POST /api/v1/auth/refresh`) ~30s before the 1h expiry. A single module-level `client` instance
  is shared by every tool call.
- `alita_agent/tools.py` — the ADK tools (plain Python functions) the LLM can call:
  `search_products`, `get_product_details`, `get_my_orders`, `get_order_status`,
  `get_payment_status`. Each wraps one read-only Ecommerce API endpoint. **Docstrings are
  load-bearing** — ADK passes them to the model to decide when/how to call each tool, so keep them
  accurate and example-driven when adding new ones. All API response fields are `snake_case`.

### Scope: read-only by design

Only query/read tools are wired up so far. Tools that would mutate state (add to cart, create
order, cancel order, request payment) are intentionally not exposed yet — `root_agent`'s
instruction explicitly forbids taking such actions without explicit user confirmation, and no tool
for them currently exists. Add mutating tools deliberately, not as a side effect of adding a new
read tool.

### Auth model — known prototype limitation

`agent.py` currently logs in once with a single fixed account (from `.env`), shared by every
conversation. Every chatbot session therefore sees the *same* user's cart/orders. Before this goes
beyond local testing, the JWT needs to come from the actual logged-in storefront user (passed into
the agent per-session) instead of from `.env` credentials.

## Configuration

`alita_agent/.env` (gitignored) holds:
- `GOOGLE_API_KEY`, `GOOGLE_GENAI_USE_ENTERPRISE` — Gemini API credentials.
- `ECOMMERCE_API_URL` — base URL of the Ecommerce API.
- `ECOMMERCE_AGENT_EMAIL` / `ECOMMERCE_AGENT_PASSWORD` — Ecommerce API user the agent logs in as
  (must already exist — register via `POST /api/v1/auth/register` on the target API first).

The target Ecommerce API must be running (`docker-compose up` from `../ecommerce-api`) before the
agent can log in or call any tool.
