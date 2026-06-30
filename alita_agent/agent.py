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

# TODO: em produção, troque por login real do usuário (ex: token recebido
# do front-end), não credenciais fixas de uma conta de serviço.
client.login(
    email=os.environ["ECOMMERCE_AGENT_EMAIL"],
    password=os.environ["ECOMMERCE_AGENT_PASSWORD"],
)

root_agent = Agent(
    model="gemini-flash-lite-latest",
    name="root_agent",
    description="Assistente de compras do e-commerce: busca produtos e consulta pedidos/pagamentos.",
    instruction=(
        "Você é um assistente de atendimento do e-commerce. Use as tools disponíveis "
        "para buscar produtos no catálogo e consultar pedidos/pagamentos do usuário. "
        "Nunca invente IDs de pedido ou dados de produto — sempre confirme via tool. "
        "Não execute ações que alterem dados (compra, cancelamento) sem confirmação "
        "explícita do usuário."
    ),
    tools=[
        search_products,
        get_product_details,
        get_my_orders,
        get_order_status,
        get_payment_status,
    ],
)