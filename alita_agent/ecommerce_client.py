import asyncio
import os
import time

import httpx

API_BASE_URL = os.getenv("ECOMMERCE_API_URL", "http://localhost:8080")


class EcommerceClient:
    """Wrapper httpx assíncrono para a Ecommerce API.

    Modo normal (produção/FastAPI): cada chamada recebe o token de acesso do
    usuário já autenticado no frontend, via parâmetro `token` de `request()`.
    Nenhum estado de login é guardado nessa via.

    Modo fallback (dev local via `adk run`/`adk web`, sem contexto HTTP):
    quando `token` não é informado, faz login/refresh sozinho usando
    ECOMMERCE_AGENT_EMAIL/PASSWORD, só para permitir testar o agente
    isoladamente.
    """

    def __init__(self, base_url: str = API_BASE_URL):
        self._base_url = base_url
        self._http = httpx.AsyncClient(base_url=base_url, timeout=10.0)
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = 0.0
        self._dev_login_lock = asyncio.Lock()

    async def _dev_login(self) -> str:
        """Fallback usado apenas quando nenhum token de usuário é fornecido."""
        async with self._dev_login_lock:
            if self._access_token is not None and time.time() < self._expires_at:
                return self._access_token

            if self._refresh_token is not None:
                resp = await self._http.post(
                    "/api/v1/auth/refresh",
                    json={"refresh_token": self._refresh_token},
                )
            else:
                resp = await self._http.post(
                    "/api/v1/auth/login",
                    json={
                        "email": os.environ["ECOMMERCE_AGENT_EMAIL"],
                        "password": os.environ["ECOMMERCE_AGENT_PASSWORD"],
                    },
                )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            self._refresh_token = data["refresh_token"]
            # margem de 30s antes do JWT expirar (max 1h, regra do projeto)
            self._expires_at = time.time() + data["expires_in"] - 30
            return self._access_token

    async def login(self, email: str, password: str) -> dict:
        """Loga com email/senha e devolve os tokens brutos (sem guardar estado).

        Usado pela tool `login`, que deixa o usuário autenticar como uma conta
        específica durante `adk run`/`adk web` — quem chama decide onde
        guardar o `access_token` (tipicamente no state da sessão ADK), em vez
        do fallback fixo de `ECOMMERCE_AGENT_EMAIL`/`PASSWORD`.
        """
        resp = await self._http.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        resp.raise_for_status()
        return resp.json()

    async def request(
        self, method: str, path: str, token: str | None = None, **kwargs
    ) -> httpx.Response:
        if token is None:
            token = await self._dev_login()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        resp = await self._http.request(method, path, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp

    async def aclose(self) -> None:
        await self._http.aclose()


# instância única reutilizada por todas as tools nesta sessão do agente
client = EcommerceClient()
