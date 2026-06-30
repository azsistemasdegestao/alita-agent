# alita-agent

A conversational agent (Google ADK) that acts as a customer support chatbot for the e-commerce
store, looking up products, orders, and payments through the project's REST API
(`../ecommerce-api`).

## Prerequisites

- Python 3.x with `google-adk` and `httpx` installed (`pip install google-adk httpx`)
- The e-commerce API running (`docker-compose up` in `../ecommerce-api`)
- A user already registered in the API (`POST /api/v1/auth/register`) for the agent to log in as
- A valid `GOOGLE_API_KEY` (Gemini API)

## Configuration

Create/edit `alita_agent/.env`:

```
GOOGLE_GENAI_USE_ENTERPRISE=0
GOOGLE_API_KEY=<your key>
ECOMMERCE_API_URL=http://localhost:8080
ECOMMERCE_AGENT_EMAIL=demo@example.com
ECOMMERCE_AGENT_PASSWORD=Demo123!
```

## Running

```bash
# Terminal mode (REPL)
adk run alita_agent

# Web mode (UI for inspecting tool calls)
adk web
```

## Structure

```
alita_agent/
  agent.py              # root_agent (Gemini model + instruction + tools)
  ecommerce_client.py    # authenticated HTTP client (JWT login/refresh)
  tools.py                # tools exposed to the LLM (product search, orders, payments)
  .env                     # local credentials and config (not committed)
```

## Current limitations

- Only read-only tools (no cart/checkout/cancellation) — actions that mutate data are not
  implemented yet.
- The agent logs in once with a single fixed account defined in `.env`, shared across every
  conversation — it does not yet authenticate as the actual logged-in storefront user.

More architecture details in [CLAUDE.md](./CLAUDE.md).
