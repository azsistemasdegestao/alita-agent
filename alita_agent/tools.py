from .ecommerce_client import client


def search_products(
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
    resp = client.request("GET", "/api/v1/catalog/products", params=params)
    return {"status": "success", **resp.json()}


def get_product_details(slug: str) -> dict:
    """Busca os detalhes completos de um produto específico pelo slug.

    Use depois de search_products, quando o usuário quiser saber mais sobre
    um item específico (descrição completa, estoque exato, etc).

    Args:
        slug: identificador único do produto (ex: "tenis-corrida-azul-42").
    """
    resp = client.request("GET", f"/api/v1/catalog/products/{slug}")
    return {"status": "success", "product": resp.json()}


def get_my_orders(page_number: int = 1, page_size: int = 10) -> dict:
    """Lista os pedidos do usuário autenticado, do mais recente ao mais antigo.

    Use quando o usuário perguntar "quais são meus pedidos" ou "meu histórico de compras".
    """
    params = {"page_number": page_number, "page_size": page_size}
    resp = client.request("GET", "/api/v1/orders", params=params)
    return {"status": "success", **resp.json()}


def get_order_status(order_id: str) -> dict:
    """Consulta o status detalhado de um pedido específico do usuário autenticado.

    Use quando o usuário perguntar sobre o status/andamento de um pedido
    específico (ex: "cadê meu pedido X", "já foi confirmado?").

    Args:
        order_id: UUID do pedido.
    """
    resp = client.request("GET", f"/api/v1/orders/{order_id}")
    return {"status": "success", "order": resp.json()}


def get_payment_status(order_id: str) -> dict:
    """Consulta o status do pagamento associado a um pedido.

    Use quando o usuário perguntar se o pagamento foi aprovado, recusado
    ou está pendente.

    Args:
        order_id: UUID do pedido cujo pagamento será consultado.
    """
    resp = client.request("GET", f"/api/v1/payments/{order_id}")
    return {"status": "success", "payment": resp.json()}