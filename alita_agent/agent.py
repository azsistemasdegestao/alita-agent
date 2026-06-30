import os

from google.adk.agents.llm_agent import Agent
from .ecommerce_client import client
from .tools import (
    search_products,
    get_product_details,
    get_my_orders,
    get_order_status,
    get_payment_status,
)

# TODO: in production, replace this with the real logged-in user's login
# (e.g. a token forwarded from the storefront), not a fixed service account.
client.login(
    email=os.environ["ECOMMERCE_AGENT_EMAIL"],
    password=os.environ["ECOMMERCE_AGENT_PASSWORD"],
)

root_agent = Agent(
    model="gemini-flash-lite-latest",
    name="root_agent",
    description="E-commerce shopping assistant: searches products and looks up orders/payments.",
    instruction=(
        "You are a customer support assistant for the e-commerce store. Always reply in "
        "the same language the user writes in. Use the available tools to search the "
        "product catalog and look up the user's orders/payments. Never make up order IDs "
        "or product data — always confirm via a tool call. Do not perform actions that "
        "mutate data (purchase, cancellation) without the user's explicit confirmation."
    ),
    tools=[
        search_products,
        get_product_details,
        get_my_orders,
        get_order_status,
        get_payment_status,
    ],
)