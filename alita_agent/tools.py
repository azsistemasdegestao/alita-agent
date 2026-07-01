import httpx
from google.adk.tools.tool_context import ToolContext

from .ecommerce_client import client


async def _request(
    method: str, path: str, tool_context: ToolContext, **kwargs
) -> httpx.Response | dict:
    """Chama a Ecommerce API usando o token do usuário guardado na sessão.

    Retorna a Response em caso de sucesso, ou um dict de erro pronto para ser
    devolvido pela tool quando o token expirou/é inválido (401), já que
    tentar de novo com o mesmo token nunca vai funcionar.
    """
    token = tool_context.state.get("access_token")
    try:
        return await client.request(method, path, token=token, **kwargs)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return {"status": "error", "message": "Sessão expirada, faça login novamente."}
        raise


async def login(email: str, password: str, tool_context: ToolContext) -> dict:
    """Autentica um usuário específico na Ecommerce API usando email e senha.

    Use apenas quando o usuário pedir explicitamente para logar/entrar com uma
    conta (ex: "loga como fulano@exemplo.com, senha 123"). Depois do login, as
    próximas tools desta mesma conversa passam a usar automaticamente esse
    usuário em vez da conta padrão de testes.

    Args:
        email: email de login do usuário.
        password: senha do usuário.
    """
    try:
        data = await client.login(email, password)
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (400, 401):
            return {"status": "error", "message": "Email ou senha inválidos."}
        raise
    tool_context.state["access_token"] = data["access_token"]
    return {"status": "success", "message": "Login realizado com sucesso."}


async def search_products(
    tool_context: ToolContext,
    search: str | None = None,
    category_slug: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    in_stock: bool | None = None,
    page_number: int = 1,
    page_size: int = 10,
) -> dict:
    """Busca produtos no catálogo do e-commerce com filtros opcionais.

    Use esta tool quando o usuário pedir para encontrar, listar ou comparar
    produtos (ex: "tem tênis de corrida?", "produtos até R$200 da categoria eletrônicos").

    Args:
        search: termo de busca livre no nome/descrição do produto.
        category_slug: slug exato da categoria (use get_categories para descobrir).
        min_price: preço mínimo em reais.
        max_price: preço máximo em reais.
        in_stock: se True, retorna apenas produtos com estoque disponível.
        page_number: página de resultados (começa em 1).
        page_size: itens por página (padrão 10, máx 20 recomendado para não estourar contexto).

    Returns:
        dict com status, lista de produtos (items) e metadados de paginação
        (total_count, has_next_page).
    """
    params = {
        "page_number": page_number,
        "page_size": page_size,
        "category_slug": category_slug,
        "search": search,
        "min_price": min_price,
        "max_price": max_price,
        "in_stock": in_stock,
    }
    params = {k: v for k, v in params.items() if v is not None}
    resp = await _request("GET", "/api/v1/catalog/products", tool_context, params=params)
    if isinstance(resp, dict):
        return resp
    return {"status": "success", **resp.json()}


async def get_product_details(slug: str, tool_context: ToolContext) -> dict:
    """Busca os detalhes completos de um produto específico pelo slug.

    Use depois de search_products, quando o usuário quiser saber mais sobre
    um item específico (descrição completa, estoque exato, etc).

    Args:
        slug: identificador único do produto (ex: "tenis-corrida-azul-42").
    """
    resp = await _request("GET", f"/api/v1/catalog/products/{slug}", tool_context)
    if isinstance(resp, dict):
        return resp
    return {"status": "success", "product": resp.json()}


async def get_my_orders(
    tool_context: ToolContext, page_number: int = 1, page_size: int = 10
) -> dict:
    """Lista os pedidos do usuário autenticado, do mais recente ao mais antigo.

    Use quando o usuário perguntar "quais são meus pedidos" ou "meu histórico de compras".
    """
    params = {"page_number": page_number, "page_size": page_size}
    resp = await _request("GET", "/api/v1/orders", tool_context, params=params)
    if isinstance(resp, dict):
        return resp
    return {"status": "success", **resp.json()}


async def get_order_status(order_id: str, tool_context: ToolContext) -> dict:
    """Consulta o status detalhado de um pedido específico do usuário autenticado.

    Use quando o usuário perguntar sobre o status/andamento de um pedido
    específico (ex: "cadê meu pedido X", "já foi confirmado?").

    Args:
        order_id: UUID do pedido.
    """
    resp = await _request("GET", f"/api/v1/orders/{order_id}", tool_context)
    if isinstance(resp, dict):
        return resp
    return {"status": "success", "order": resp.json()}


async def get_payment_status(order_id: str, tool_context: ToolContext) -> dict:
    """Consulta o status do pagamento associado a um pedido.

    Use quando o usuário perguntar se o pagamento foi aprovado, recusado
    ou está pendente.

    Args:
        order_id: UUID do pedido cujo pagamento será consultado.
    """
    resp = await _request("GET", f"/api/v1/payments/{order_id}", tool_context)
    if isinstance(resp, dict):
        return resp
    return {"status": "success", "payment": resp.json()}
