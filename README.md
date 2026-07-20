# alita-agent

A conversational agent (Google ADK) that acts as a customer support chatbot for the e-commerce
store, looking up products, orders, payments, and the shopping cart through the project's REST API
(`../ecommerce-api`), plus answering store FAQ/policy questions via a small RAG-backed knowledge
base of its own.

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
  tools.py                # tools exposed to the LLM (product search, orders, payments, cart, FAQ)
  faq_rag.py               # RAG engine backing the FAQ tool (in-memory embeddings index)
  grounding_check.py        # post-response hallucination guardrail (see below), used by api.py
  data/faq.json             # FAQ/policy knowledge base indexed by faq_rag.py
  .env                     # local credentials and config (not committed)
```

## Hallucination safeguards

The agent is prompted to never invent order/product/policy data, runs at a low sampling
temperature, and every `/chat` reply passes through a runtime grounding check
(`grounding_check.py`) that blocks and replaces replies not backed by that turn's tool results.
There's also an offline eval set (`tests/integration/eval/`) built on ADK's `hallucinations_v1`
metric for deeper, sentence-level checks. Details in [CLAUDE.md](./CLAUDE.md)'s "Hallucination
safeguards" section.

## Current limitations

- Only read-only tools (no adding/removing cart items, checkout, cancellation) — actions that
  mutate data are not implemented yet.
- Under `adk run`/`adk web` only, the agent falls back to logging in once with a single fixed
  account defined in `.env`, shared across the whole conversation (or you can call the `login`
  tool mid-conversation to act as a specific user instead). The production chat API (`api.py`) is
  per-user: it forwards the caller's own JWT into every tool call, no shared account involved —
  see [CLAUDE.md](./CLAUDE.md)'s Auth model section.

More architecture details in [CLAUDE.md](./CLAUDE.md).
