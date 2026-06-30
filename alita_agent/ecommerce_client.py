import os
import time
import httpx

API_BASE_URL = os.getenv("ECOMMERCE_API_URL", "http://localhost:8080")


class EcommerceClient:
    """Mantém o JWT autenticado e renova via refresh token quando expira."""

    def __init__(self, base_url: str = API_BASE_URL):
        self._base_url = base_url
        self._http = httpx.Client(base_url=base_url, timeout=10.0)
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = 0.0

    def login(self, email: str, password: str) -> None:
        resp = self._http.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]
        # margem de 30s antes do JWT expirar (max 1h, regra do projeto)
        self._expires_at = time.time() + data["expires_in"] - 30

    def _ensure_valid_token(self) -> None:
        if self._access_token is None:
            raise RuntimeError("Client not authenticated. Call login() first.")
        if time.time() >= self._expires_at:
            resp = self._http.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": self._refresh_token},
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            self._refresh_token = data["refresh_token"]  # rotacionado a cada uso
            self._expires_at = time.time() + data["expires_in"] - 30

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        self._ensure_valid_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._access_token}"
        resp = self._http.request(method, path, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp


# instância única reutilizada por todas as tools nesta sessão do agente
client = EcommerceClient()