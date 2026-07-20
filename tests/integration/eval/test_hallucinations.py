import os
from pathlib import Path

import httpx
import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

from alita_agent.ecommerce_client import client as ecommerce_client

pytestmark = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"), reason="requires a real Gemini key (GOOGLE_API_KEY)"
)

EVAL_SET = Path(__file__).parent / "hallucination.test.json"


@pytest.fixture(autouse=True)
def fake_ecommerce_calls(monkeypatch):
    """Every Ecommerce API call comes back empty/not-found.

    The point of this eval is to check that the agent says "não encontrei"
    instead of inventing product/order data — so the fake backend never has
    anything to find. Same pattern as tests/integration/chat_api's fixture:
    patches EcommerceClient.request directly (not respx) because respx
    interferes with the real Gemini httpx call this test also makes.
    """

    async def fake_request(method: str, path: str, token: str | None = None, **kwargs):
        req = httpx.Request(method, path)
        return httpx.Response(
            200, request=req, json={"items": [], "total_count": 0, "has_next_page": False}
        )

    monkeypatch.setattr(ecommerce_client, "request", fake_request)


async def test_agent_does_not_hallucinate():
    """The agent must not invent product/order data when the API has nothing to return."""
    await AgentEvaluator.evaluate(
        agent_module="alita_agent",
        eval_dataset_file_path_or_dir=str(EVAL_SET),
    )
