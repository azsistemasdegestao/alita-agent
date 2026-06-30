# alita-agent

Agente conversacional (Google ADK) que atua como chatbot de atendimento para o e-commerce,
consultando produtos, pedidos e pagamentos através da API REST do projeto (`../ecommerce-api`).

## Pré-requisitos

- Python 3.x com `google-adk` e `httpx` instalados (`pip install google-adk httpx`)
- A API do e-commerce rodando (`docker-compose up` em `../ecommerce-api`)
- Um usuário já registrado na API (`POST /api/v1/auth/register`) para o agente usar no login
- Uma `GOOGLE_API_KEY` válida (Gemini API)

## Configuração

Crie/edite `alita_agent/.env`:

```
GOOGLE_GENAI_USE_ENTERPRISE=0
GOOGLE_API_KEY=<sua chave>
ECOMMERCE_API_URL=http://localhost:8080
ECOMMERCE_AGENT_EMAIL=demo@example.com
ECOMMERCE_AGENT_PASSWORD=Demo123!
```

## Rodando

```bash
# Modo terminal (REPL)
adk run alita_agent

# Modo web (UI para inspecionar chamadas de tool)
adk web
```

## Estrutura

```
alita_agent/
  agent.py              # root_agent (modelo Gemini + instruction + tools)
  ecommerce_client.py    # client HTTP autenticado (login/refresh de JWT)
  tools.py                # tools expostas ao LLM (busca de produtos, pedidos, pagamentos)
  .env                     # credenciais e config local (não versionado)
```

## Limitações atuais

- Apenas tools de leitura (sem carrinho/checkout/cancelamento) — ações que alteram dados não estão
  implementadas ainda.
- O agente loga uma única vez com uma conta fixa definida no `.env`, compartilhada por todas as
  conversas — ainda não autentica como o usuário real logado na loja.

Mais detalhes de arquitetura em [CLAUDE.md](./CLAUDE.md).
