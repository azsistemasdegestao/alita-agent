import json
from pathlib import Path

import alita_agent.faq_rag as faq_rag

_VECTORS = {
    "pergunta trocas resposta trocas": [1.0, 0.0, 0.0],
    "pergunta entrega resposta entrega": [0.0, 1.0, 0.0],
    "quero trocar um produto": [0.9, 0.1, 0.0],
    "isso não tem nada a ver com a loja": [0.0, 0.0, 1.0],
}


def _fake_embed(text: str) -> list[float]:
    return _VECTORS[text]


def _write_faq(tmp_path: Path) -> Path:
    path = tmp_path / "faq.json"
    path.write_text(
        json.dumps(
            [
                {"question": "pergunta trocas", "answer": "resposta trocas"},
                {"question": "pergunta entrega", "answer": "resposta entrega"},
            ]
        ),
        encoding="utf-8",
    )
    return path


def setup_function():
    faq_rag._index = []


def test_build_index_computes_embedding_per_entry(tmp_path, monkeypatch):
    """AC-FAQ-U01"""
    monkeypatch.setattr(faq_rag, "embed_text", _fake_embed)

    faq_rag.build_index(_write_faq(tmp_path))

    assert [c.question for c in faq_rag._index] == ["pergunta trocas", "pergunta entrega"]
    assert faq_rag._index[0].embedding == [1.0, 0.0, 0.0]


def test_search_faq_returns_most_similar_entry_first(tmp_path, monkeypatch):
    """AC-FAQ-U02"""
    monkeypatch.setattr(faq_rag, "embed_text", _fake_embed)
    faq_rag.build_index(_write_faq(tmp_path))

    results = faq_rag.search_faq("quero trocar um produto", top_k=1)

    assert results == [{"question": "pergunta trocas", "answer": "resposta trocas"}]


def test_search_faq_filters_out_entries_below_min_similarity(tmp_path, monkeypatch):
    """AC-FAQ-U03"""
    monkeypatch.setattr(faq_rag, "embed_text", _fake_embed)
    faq_rag.build_index(_write_faq(tmp_path))

    results = faq_rag.search_faq(
        "isso não tem nada a ver com a loja", top_k=2, min_similarity=0.5
    )

    assert results == []


def test_search_faq_builds_index_lazily_when_empty(tmp_path, monkeypatch):
    """AC-FAQ-U04"""
    monkeypatch.setattr(faq_rag, "FAQ_PATH", _write_faq(tmp_path))
    monkeypatch.setattr(faq_rag, "embed_text", _fake_embed)

    results = faq_rag.search_faq("pergunta trocas resposta trocas", top_k=1)

    assert results == [{"question": "pergunta trocas", "answer": "resposta trocas"}]
