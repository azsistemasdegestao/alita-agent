import json
from dataclasses import dataclass
from pathlib import Path

from google import genai

EMBEDDING_MODEL = "gemini-embedding-001"
FAQ_PATH = Path(__file__).parent / "data" / "faq.json"

_client: genai.Client | None = None


@dataclass
class _Chunk:
    question: str
    answer: str
    embedding: list[float]


_index: list[_Chunk] = []


def _get_client() -> genai.Client:
    # Lazy singleton so importing this module never requires GOOGLE_API_KEY —
    # only actually calling embed_text() (real, unmocked) does.
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


def embed_text(text: str) -> list[float]:
    """Gera o vetor de embedding de um texto via Gemini API."""
    response = _get_client().models.embed_content(model=EMBEDDING_MODEL, contents=text)
    return response.embeddings[0].values


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def build_index(faq_path: Path | None = None) -> None:
    """Carrega a base de FAQ e calcula o embedding de cada entrada.

    Chamado uma vez no startup de api.py; sob adk run/web é chamado
    preguiçosamente pela primeira busca (ver search_faq).
    """
    global _index
    entries = json.loads((faq_path or FAQ_PATH).read_text(encoding="utf-8"))
    _index = [
        _Chunk(
            question=entry["question"],
            answer=entry["answer"],
            embedding=embed_text(f"{entry['question']} {entry['answer']}"),
        )
        for entry in entries
    ]


def search_faq(query: str, top_k: int = 3, min_similarity: float = 0.5) -> list[dict]:
    """Retorna as entradas de FAQ mais relevantes para a pergunta, por similaridade semântica.

    Entradas cuja similaridade com a pergunta fique abaixo de min_similarity são descartadas
    (evita devolver conteúdo sem relação nenhuma só porque era "o menos irrelevante" do índice).
    """
    if not _index:
        build_index()
    query_embedding = embed_text(query)
    scored = [(chunk, _cosine_similarity(chunk.embedding, query_embedding)) for chunk in _index]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [
        {"question": chunk.question, "answer": chunk.answer}
        for chunk, score in scored[:top_k]
        if score >= min_similarity
    ]
