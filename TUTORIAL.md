# Alita Agent - Complete Project Tutorial

> **Audience:** Senior engineers familiar with .NET/C# and Angular who want to understand this
> Python/Google ADK agent and how it fits into the broader e-commerce system.

---

## 1. The Big Picture: Where This Agent Sits

You already know the two other pieces of this system:

```
                                 +-----------------+
                                 |    Angular SSR  |
                                 |   (frontend/)   |
                                 +--------+--------+
                                          |
                                          | HTTP
                                          v
+------------------+   HTTP/JWT   +------------------+
|   alita-agent    | -----------> |  ecommerce-api   |
| (this project)   |              | (.NET 10 / CA)   |
| Google ADK +     |              | REST API + DB    |
| Gemini LLM       |              +------------------+
+------------------+
        ^
        |
   User (chat)
```

**alita-agent** is a conversational AI chatbot — a separate Python process that talks to your .NET
API over HTTP, using the same JWT auth your Angular frontend uses. It has **zero** direct access to
your database, cache, or any internal service. It's a pure API consumer.

Think of it as: **an automated customer support agent that can search products, look up orders, and
check payment status** by calling your existing REST endpoints — all driven by natural language.

---

## 2. Technology Stack (C#/.NET Mental Model)

| Concept                     | .NET Equivalent                              | Here (Python/ADK)                          |
| --------------------------- | -------------------------------------------- | ------------------------------------------ |
| Framework                   | ASP.NET Core                                 | Google ADK (Agent Development Kit)         |
| LLM orchestration           | (no built-in)                                | ADK wires Gemini model + tools + prompts   |
| HTTP client                 | `HttpClient` + `IHttpClientFactory`          | `httpx.Client` (sync, similar API)         |
| DI / singleton service      | `services.AddSingleton<T>()`                 | Module-level instance (`client = ...()`)   |
| Auth middleware / delegating handler | `DelegatingHandler` with Bearer token | `_ensure_valid_token()` in `EcommerceClient` |
| Controller actions          | `[HttpGet] Task<IActionResult> Get()`        | Plain Python functions decorated as "tools"|
| Swagger/OpenAPI docs        | XML doc comments on actions                  | **Docstrings** on tool functions (load-bearing!) |
| `appsettings.json`          | Configuration via `IOptions<T>`              | `.env` file, loaded by `adk run`           |
| Startup / `Program.cs`      | `builder.Services...` / `app.Map...`         | `agent.py` (module-level init)             |

---

## 3. Project Structure — Four Files, That's It

```
alita-agent/
  CLAUDE.md                    # AI-facing project documentation (you're reading the tutorial)
  README.md                    # Human-facing quickstart
  alita_agent/                 # The actual Python package (ADK convention: folder = agent)
    __init__.py                # Just `from . import agent` — ADK entry point
    agent.py                   # "Startup.cs" — configures the LLM agent, registers tools
    ecommerce_client.py        # "HttpClient wrapper" — JWT login, auto-refresh, Bearer header
    tools.py                   # "Controllers" — functions the LLM can invoke
    .env                       # "appsettings.Development.json" — secrets, API URL (gitignored)
```

No `requirements.txt`, no `pyproject.toml`, no test suite, no linter — this is a prototype.
Dependencies (`google-adk`, `httpx`) are pip-installed directly.

---

## 4. Deep Dive: Each File Explained

### 4.1 `__init__.py` — The Entry Point

```python
from . import agent
```

When you run `adk run alita_agent`, ADK imports the `alita_agent` package. This `__init__.py`
triggers `agent.py`, which in turn imports everything else. ADK then looks for `root_agent` in that
module.

**C# analogy:** This is your `Program.cs` that calls `CreateHostBuilder(args).Build().Run()` — it
bootstraps the application.

### 4.2 `ecommerce_client.py` — The HTTP + Auth Layer

```python
class EcommerceClient:
    def __init__(self, base_url):
        self._http = httpx.Client(base_url=base_url, timeout=10.0)
        self._access_token = None
        self._refresh_token = None
        self._expires_at = 0.0

    def login(self, email, password):       # POST /api/v1/auth/login
    def _ensure_valid_token(self):           # POST /api/v1/auth/refresh (if within 30s of expiry)
    def request(self, method, path, **kw):   # Any HTTP call with Bearer token injected

client = EcommerceClient()  # Module-level singleton
```

**In C# terms**, this is the equivalent of:

```csharp
// A DelegatingHandler that auto-refreshes the JWT
public class JwtRefreshHandler : DelegatingHandler
{
    protected override async Task<HttpResponseMessage> SendAsync(...)
    {
        if (DateTime.UtcNow >= _expiresAt)
            await RefreshTokenAsync();
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _accessToken);
        return await base.SendAsync(request, cancellationToken);
    }
}
```

**Key design decisions:**

- **Singleton pattern via module scope.** `client = EcommerceClient()` at module level means every
  tool function shares the same authenticated HTTP client. In Python, module-level code runs once
  on first import — functionally identical to `AddSingleton<EcommerceClient>()`.

- **Token refresh with 30-second margin.** The JWT has a 1-hour TTL. The client subtracts 30
  seconds from the expiry timestamp, so it proactively refreshes before the token actually expires.
  This avoids the race condition where a request is sent with a token that expires mid-flight.

- **`httpx` vs `requests`.** `httpx` is the modern Python HTTP client — think of it as Python's
  `HttpClient`. It supports sync and async, connection pooling, timeouts, and a very similar API
  to what you'd expect from `HttpClient`. The `base_url` parameter works like
  `HttpClient.BaseAddress`.

### 4.3 `tools.py` — The "Controllers"

This is where the actual API integration lives. Each function = one tool the LLM can call.

```python
def search_products(search=None, category_slug=None, min_price=None, ...) -> dict:
    """Docstring that the LLM reads to decide when/how to call this tool."""
    params = {k: v for k, v in {...}.items() if v is not None}
    resp = client.request("GET", "/api/v1/catalog/products", params=params)
    return {"status": "success", **resp.json()}
```

**Five tools currently exist, all read-only:**

| Tool Function          | HTTP Call                            | Purpose                           |
| ---------------------- | ------------------------------------ | --------------------------------- |
| `search_products()`    | `GET /api/v1/catalog/products`       | Search/filter the product catalog |
| `get_product_details()`| `GET /api/v1/catalog/products/{slug}`| Full details for one product      |
| `get_my_orders()`      | `GET /api/v1/orders`                 | List authenticated user's orders  |
| `get_order_status()`   | `GET /api/v1/orders/{id}`            | Status of a specific order        |
| `get_payment_status()` | `GET /api/v1/payments/{id}`          | Payment status for an order       |

**Critical concept: Docstrings are load-bearing.**

In .NET, you decorate controller actions with `[HttpGet]`, `[ProducesResponseType]`, and XML
comments for Swagger. In ADK, **the docstring IS the API contract with the LLM**. ADK extracts
the docstring and sends it to Gemini as part of the tool definition. The model uses it to decide:

1. *When* to call this tool (based on the user's natural language intent)
2. *What arguments* to pass (based on the `Args:` section)
3. *How to interpret the response* (based on the `Returns:` section)

If you write a vague docstring, the LLM will misuse the tool. If you write an inaccurate one,
it'll hallucinate capabilities. Treat docstrings like you'd treat your Swagger documentation.

**The `**kwargs` → query params pattern:**

```python
params = {k: v for k, v in {
    "search": search,
    "min_price": min_price,
    ...
}.items() if v is not None}
```

This is the Python idiom for "build query string, omitting null values" — equivalent to:

```csharp
var query = new Dictionary<string, string>();
if (search != null) query["search"] = search;
if (minPrice != null) query["min_price"] = minPrice.ToString();
// ...
```

### 4.4 `agent.py` — Wiring It All Together

```python
# 1. Authenticate at import time
client.login(
    email=os.environ["ECOMMERCE_AGENT_EMAIL"],
    password=os.environ["ECOMMERCE_AGENT_PASSWORD"],
)

# 2. Define the agent
root_agent = Agent(
    model="gemini-flash-lite-latest",
    name="root_agent",
    description="E-commerce shopping assistant...",
    instruction="You are a customer support assistant...",
    tools=[search_products, get_product_details, get_my_orders, ...],
)
```

**This is your `Startup.cs` + `Program.cs` in 20 lines.**

The `Agent` constructor takes:

| Parameter     | What it does                                                |
| ------------- | ----------------------------------------------------------- |
| `model`       | Which Gemini model to use (like choosing `gpt-4` vs `gpt-3.5`) |
| `name`        | Internal identifier (ADK uses this for routing in multi-agent setups) |
| `description` | Used by parent agents in multi-agent scenarios to decide delegation |
| `instruction` | **The system prompt** — defines the agent's persona and behavioral constraints |
| `tools`       | List of Python functions the LLM is allowed to call         |

**Model choice rationale:** `gemini-flash-lite-latest` is the cheapest/fastest Gemini model. It
was chosen because it has a separate free-tier quota bucket from `gemini-flash-latest`, so the
agent doesn't burn through the shared quota during development.

**The instruction (system prompt)** establishes guardrails:
- Reply in the user's language (Portuguese, English, etc.)
- Never fabricate data — always use a tool call
- Never mutate data without explicit user confirmation

---

## 5. The Runtime Flow (What Happens When a User Chats)

Here's the end-to-end flow when a user types "Do you have blue running shoes under $200?":

```
User: "Do you have blue running shoes under $200?"
  |
  v
[ADK Framework]
  |  Sends to Gemini:
  |  - System instruction (persona)
  |  - Tool definitions (docstrings + signatures)
  |  - Chat history
  |  - User message
  v
[Gemini LLM]
  |  Decides: "I should call search_products(search='blue running shoes', max_price=200)"
  |  Returns: tool_call(search_products, {search: "blue running shoes", max_price: 200.0})
  v
[ADK Framework]
  |  Executes the Python function search_products(...)
  v
[tools.py :: search_products()]
  |  client.request("GET", "/api/v1/catalog/products?search=blue+running+shoes&max_price=200")
  v
[ecommerce_client.py]
  |  1. Checks token expiry → refreshes if needed
  |  2. Adds Bearer header
  |  3. Sends HTTP request
  v
[Your .NET ecommerce-api]
  |  ProductsController.GetProducts(search, maxPrice)
  |  → Application layer → Domain → EF Core → PostgreSQL
  |  Returns JSON
  v
[tools.py]
  |  Returns {"status": "success", "items": [...], "total_count": 3, ...}
  v
[ADK Framework]
  |  Sends tool result back to Gemini
  v
[Gemini LLM]
  |  Formats a natural language response from the JSON data
  v
User: "Yes! I found 3 blue running shoes under $200: ..."
```

**C# analogy for the whole flow:**

Think of ADK as a **Mediatr-style mediator** where:
- The LLM is the "handler router" — it reads the user's intent and dispatches to the right handler
- Tool functions are the handlers
- Docstrings are the handler metadata that tells the router what each handler does
- The system instruction is the middleware pipeline's global behavior policy

---

## 6. How to Run It

### Prerequisites

1. **Python 3.12+** with `google-adk` and `httpx`:
   ```bash
   pip install google-adk httpx
   ```

2. **Your .NET ecommerce-api running** (the agent needs it for every tool call):
   ```bash
   cd ../ecommerce-api
   docker-compose up -d
   ```

3. **A registered user** in the API for the agent to log in as:
   ```bash
   curl -X POST http://localhost:8080/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "agent@test.com", "password": "Agent123!", "name": "AI Agent"}'
   ```

4. **A Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey)

### Configure

Create `alita_agent/.env`:

```env
GOOGLE_GENAI_USE_ENTERPRISE=0
GOOGLE_API_KEY=your-gemini-api-key-here
ECOMMERCE_API_URL=http://localhost:8080
ECOMMERCE_AGENT_EMAIL=agent@test.com
ECOMMERCE_AGENT_PASSWORD=Agent123!
```

### Run

```bash
# Option A: Terminal REPL — type messages, see responses
adk run alita_agent

# Option B: Web UI at http://localhost:8000 — see tool calls, args, and responses
adk web
```

The `adk web` option is especially useful during development — it shows you exactly which tools
the LLM chose, what arguments it passed, and what the API returned. Think of it as your
agent's Swagger UI + debugger combined.

---

## 7. How ADK Compares to Patterns You Know

### It's NOT like building a REST API

In .NET, you define endpoints and the client decides what to call. Here, **the LLM decides what
to call**. You define *capabilities* (tools), and the model routes user intent to them.

### It's closer to a CQRS read-side

All five tools are queries. There are no commands. The agent is a read model consumer that
presents data conversationally. The `instruction` explicitly forbids mutations — a design
constraint, not a technical limitation.

### The "dependency injection" is simpler

Python doesn't have a DI container. Instead:
- `ecommerce_client.py` creates a module-level singleton: `client = EcommerceClient()`
- `tools.py` imports it: `from .ecommerce_client import client`
- `agent.py` calls `client.login(...)` at import time

This works because Python modules are singletons — imported once, cached in `sys.modules`.
Every file that does `from .ecommerce_client import client` gets the same object instance.
It's the equivalent of `services.AddSingleton<EcommerceClient>()` without the ceremony.

### Docstrings = OpenAPI spec

In your .NET API, you write XML comments and `[ProducesResponseType]` attributes so Swagger
can generate docs. Here, the docstring serves the same purpose but for the LLM audience.
The model reads the docstring to understand:
- When to invoke the tool
- What arguments are valid
- What the return value means

Bad docstrings = bad tool usage, just like bad Swagger docs = confused API consumers.

---

## 8. Architecture Decisions Worth Understanding

### Why `gemini-flash-lite-latest` instead of a more powerful model?

Cost and quota. During development with the free tier, `flash-lite` has a separate quota bucket
that doesn't compete with `flash` or `pro`. For a read-only chatbot that mostly reformats JSON
into natural language, it's more than capable. You'd upgrade to `gemini-flash-latest` or
`gemini-pro` for complex reasoning tasks (multi-step order workflows, nuanced refund policies).

### Why a single shared login instead of per-user auth?

This is a prototype shortcut. The agent logs in once at startup with credentials from `.env`.
Every chat session sees the same user's orders/cart. The production fix is to receive the
authenticated user's JWT from the Angular frontend per-session and inject it into the agent
context, but that requires session-scoped client instances instead of the current singleton.

### Why read-only tools only?

Deliberate safety constraint. An LLM that can cancel orders or process payments based on a
misinterpreted user message is a liability. The `instruction` says "do not perform actions that
mutate data without the user's explicit confirmation," and no mutation tools exist yet to
enforce this at the code level (defense in depth).

### Why `httpx` instead of `requests`?

`httpx` is the modern choice: it supports both sync and async (useful if you later switch to
ADK's async mode), has `base_url` support (no string concatenation), and has a cleaner
timeout API. For your mental model, `httpx.Client` ≈ `HttpClient`, while `requests.Session`
≈ `WebClient` (the older, less flexible option).

---

## 9. Adding a New Tool (Step-by-Step)

Say you want to add a `get_categories` tool so the LLM can help users browse by category.

### Step 1: Add the function to `tools.py`

```python
def get_categories() -> dict:
    """Lists all product categories available in the store.

    Use this tool when the user asks about available categories, departments,
    or wants to browse the catalog by category (e.g., "what categories do you
    have?", "show me departments").

    Returns:
        dict with status and a list of categories, each having name, slug,
        and product_count.
    """
    resp = client.request("GET", "/api/v1/catalog/categories")
    return {"status": "success", "categories": resp.json()}
```

### Step 2: Register it in `agent.py`

```python
from .tools import (
    search_products,
    get_product_details,
    get_my_orders,
    get_order_status,
    get_payment_status,
    get_categories,          # <-- add import
)

root_agent = Agent(
    ...
    tools=[
        search_products,
        get_product_details,
        get_my_orders,
        get_order_status,
        get_payment_status,
        get_categories,      # <-- add to tools list
    ],
)
```

### Step 3: Test with `adk web`

```bash
adk web
# Open http://localhost:8000
# Type: "What categories do you have?"
# Verify the LLM calls get_categories() and formats the response
```

That's it. No route registration, no controller, no middleware pipeline, no Swagger annotations.
Write the function, write the docstring, register it, done.

---

## 10. Common Pitfalls

| Pitfall | Why it happens | Fix |
|---------|---------------|-----|
| Agent crashes on startup | `.env` missing or ecommerce-api not running | Check `ECOMMERCE_API_URL` is reachable and credentials are valid |
| LLM never calls your tool | Docstring doesn't match user intent well enough | Rewrite the docstring with concrete examples of when to use it |
| LLM calls the wrong tool | Docstrings overlap — two tools seem applicable | Make docstrings mutually exclusive; add "Use X, NOT this tool, when..." |
| LLM hallucinates product data | Instruction not strict enough, or tool returns partial data | Ensure instruction says "never fabricate" and tools return complete data |
| Token refresh fails | Refresh token was already rotated (used twice) | Bug in retry logic; ensure `_ensure_valid_token` is not called concurrently |
| `python agent.py` fails | Running directly doesn't load `.env` | Always use `adk run alita_agent` or `adk web`; plain Python won't load `.env` |

---

## 11. Development Workflow Cheat Sheet

```bash
# Start the backend (from sibling repo)
cd ../ecommerce-api && docker-compose up -d

# Run the agent with debugging UI
cd ../alita-agent && adk web

# Quick terminal test
adk run alita_agent

# Install dependencies (no requirements.txt yet)
pip install google-adk httpx
```

---

## 12. What's Next (Roadmap Gaps)

1. **Per-user authentication** — pass the storefront user's JWT into the agent session instead of
   a shared service account.
2. **Mutation tools** — add-to-cart, create-order, cancel-order, request-payment. Each needs
   explicit user confirmation before execution (two-step: "confirm" → "execute").
3. **Multi-agent architecture** — split into sub-agents (catalog agent, order agent, payment
   agent) with a root agent that routes. ADK supports this natively with `sub_agents`.
4. **Proper packaging** — `pyproject.toml`, `requirements.txt`, Docker image, CI/CD.
5. **Test suite** — mock the ecommerce-api responses and verify tool behavior.
6. **Async mode** — switch from `httpx.Client` to `httpx.AsyncClient` for better concurrency
   under load.
