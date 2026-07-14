import alita_agent.faq_rag as faq_rag
from alita_agent.tools import answer_from_faq


async def test_answer_from_faq_success_returns_results(monkeypatch):
    """AC-FAQ-U05"""
    fake_results = [{"question": "Qual a política de troca?", "answer": "30 dias."}]
    monkeypatch.setattr(faq_rag, "search_faq", lambda question: fake_results)

    result = await answer_from_faq("qual a política de troca?")

    assert result == {"status": "success", "results": fake_results}


async def test_answer_from_faq_no_relevant_entries_returns_empty(monkeypatch):
    """AC-FAQ-U06"""
    monkeypatch.setattr(faq_rag, "search_faq", lambda question: [])

    result = await answer_from_faq("qual a capital da frança?")

    assert result == {"status": "empty", "results": []}
