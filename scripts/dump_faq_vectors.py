"""Dev utility: builds the real FAQ RAG index and dumps it to faq_vectors.json for inspection.

Requires a real GOOGLE_API_KEY in alita_agent/.env — it calls the actual Gemini embeddings
API, unlike the test suite (which mocks embed_text and never hits the network).

Usage (from the repo root):
    python scripts/dump_faq_vectors.py
"""
import json
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / "alita_agent" / ".env")

from alita_agent import faq_rag  # noqa: E402 (must import after load_dotenv)

faq_rag.build_index()

output = [
    {
        "question": chunk.question,
        "answer": chunk.answer,
        "embedding_dims": len(chunk.embedding),
        "embedding_preview": chunk.embedding[:5],
        "embedding_full": chunk.embedding,
    }
    for chunk in faq_rag._index
]

out_path = REPO_ROOT / "faq_vectors.json"
out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"{len(output)} entradas salvas em {out_path}")
