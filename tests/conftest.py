import pytest

from alita_agent.ecommerce_client import EcommerceClient

TEST_BASE_URL = "http://test-ecommerce-api"


class FakeToolContext:
    """Minimal stand-in for ADK's real ToolContext.

    tools.py only ever reads/writes `.state`, so a plain dict is enough —
    no need to construct ADK's real Context/InvocationContext machinery.
    """

    def __init__(self, state: dict | None = None):
        self.state = state if state is not None else {}


@pytest.fixture
def tool_context() -> FakeToolContext:
    # Pre-seeded with a token so tests default to the token-supplied path
    # (BR-AUTH-001) instead of accidentally exercising the dev-login
    # fallback, which needs ECOMMERCE_AGENT_EMAIL/PASSWORD to be set.
    return FakeToolContext(state={"access_token": "test-access-token"})


@pytest.fixture
def test_client(monkeypatch) -> EcommerceClient:
    """A fresh EcommerceClient pointed at TEST_BASE_URL, wired into tools.py.

    Each test gets its own instance (no cross-test state leakage in the
    dev-login cache), and monkeypatching `alita_agent.tools.client` means
    tests are independent of whatever ECOMMERCE_API_URL is set in the real
    environment.
    """
    import alita_agent.tools as tools_module

    client = EcommerceClient(base_url=TEST_BASE_URL)
    monkeypatch.setattr(tools_module, "client", client)
    return client
