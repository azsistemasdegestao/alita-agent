import alita_agent.grounding_check as grounding_check


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text


class _FakeModels:
    def __init__(self, text: str):
        self._text = text

    async def generate_content(self, model, contents):
        return _FakeResponse(self._text)


class _FakeAio:
    def __init__(self, text: str):
        self.models = _FakeModels(text)


class _FakeClient:
    def __init__(self, text: str):
        self.aio = _FakeAio(text)


def _stub_judge(monkeypatch, text: str):
    monkeypatch.setattr(grounding_check, "_get_client", lambda: _FakeClient(text))


async def test_grounded_reply_passes(monkeypatch):
    _stub_judge(monkeypatch, "GROUNDED")

    is_grounded, verdict = await grounding_check.check_grounding(
        tool_activity=[
            {"tool_result": {"name": "search_products", "response": {"items": []}}}
        ],
        reply="Não encontrei esse produto no catálogo.",
    )

    assert is_grounded is True
    assert verdict == "GROUNDED"


async def test_ungrounded_reply_is_flagged(monkeypatch):
    _stub_judge(monkeypatch, "UNGROUNDED: invented an order id not present in tool results")

    is_grounded, verdict = await grounding_check.check_grounding(
        tool_activity=[],
        reply="Seu pedido #12345 foi entregue ontem.",
    )

    assert is_grounded is False
    assert "invented" in verdict


async def test_empty_reply_short_circuits_without_calling_judge(monkeypatch):
    def _boom():
        raise AssertionError("should not call the judge for an empty reply")

    monkeypatch.setattr(grounding_check, "_get_client", _boom)

    is_grounded, verdict = await grounding_check.check_grounding(tool_activity=[], reply="   ")

    assert is_grounded is True


async def test_judge_call_failure_fails_open(monkeypatch):
    class _BrokenModels:
        async def generate_content(self, model, contents):
            raise RuntimeError("boom")

    class _BrokenAio:
        models = _BrokenModels()

    class _BrokenClient:
        aio = _BrokenAio()

    monkeypatch.setattr(grounding_check, "_get_client", lambda: _BrokenClient())

    is_grounded, verdict = await grounding_check.check_grounding(
        tool_activity=[], reply="oi, tudo bem?"
    )

    assert is_grounded is True
