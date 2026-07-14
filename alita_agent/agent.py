from google.adk.agents.llm_agent import Agent
from .tools import (
    login,
    search_products,
    get_product_details,
    get_my_orders,
    get_order_status,
    get_payment_status,
    answer_from_faq,
)

MODEL = "gemini-flash-lite-latest"
NAME = "root_agent"
DESCRIPTION = (
    "E-commerce shopping assistant: searches products, looks up orders/payments, "
    "and answers store FAQ/policy questions."
)
INSTRUCTION = (
    "You are a customer support assistant for the e-commerce store. Always reply in "
    "the same language the user writes in. Use the available tools to search the "
    "product catalog, look up the user's orders/payments, and answer general store "
    "FAQ/policy questions (shipping, returns, payment methods, etc.) via "
    "answer_from_faq. Never make up order IDs, product data, or store policies — "
    "always confirm via a tool call. Do not perform actions that mutate data "
    "(purchase, cancellation) without the user's explicit confirmation."
)

# Tools shared by every entry point (CLI, web UI, and the production chat API).
CHAT_TOOLS = [
    search_products,
    get_product_details,
    get_my_orders,
    get_order_status,
    get_payment_status,
    answer_from_faq,
]

# `root_agent` is what `adk run`/`adk web` discover by convention. It adds the
# `login` tool so you can authenticate as a specific test user by email/senha
# from the terminal/web UI, without needing the FastAPI layer or a JWT already
# in hand. `login` is intentionally NOT included in api.py's agent (see there)
# — accepting a plaintext password typed into a real customer-facing chat is
# an auth anti-pattern; production traffic authenticates via the Authorization
# header instead.
root_agent = Agent(
    model=MODEL,
    name=NAME,
    description=DESCRIPTION,
    instruction=INSTRUCTION,
    tools=CHAT_TOOLS + [login],
)
