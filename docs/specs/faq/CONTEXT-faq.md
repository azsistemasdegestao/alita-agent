# CONTEXT-faq.md
> Feature-specific context document for faq.
> Read alongside SPEC-faq.md when writing/regenerating tests.

---

## File Structure

```
alita_agent/faq_rag.py
  embed_text()      wraps google.genai Client().models.embed_content
  build_index()     loads data/faq.json, computes one embedding per entry
  search_faq()      cosine-similarity ranking + min_similarity cutoff

alita_agent/tools.py
  answer_from_faq()   line ~150

alita_agent/data/faq.json   the knowledge base itself (placeholder content)

tests/unit/faq/
  test_faq_rag.py   AC-FAQ-U01..U04
  test_tools.py     AC-FAQ-U05..U06
```

## Embeddings call (mocked in tests, never hits the real API)

```python
from google import genai
client = genai.Client()  # reads GOOGLE_API_KEY from env, same as the rest of the project
response = client.models.embed_content(model="text-embedding-004", contents=text)
response.embeddings[0].values  # -> list[float]
```

Tests monkeypatch `faq_rag.embed_text` directly (not the `genai.Client`) with a `dict`-backed
fake, e.g.:

```python
_VECTORS = {"pergunta trocas resposta trocas": [1.0, 0.0, 0.0], ...}

def _fake_embed(text: str) -> list[float]:
    return _VECTORS[text]

monkeypatch.setattr(faq_rag, "embed_text", _fake_embed)
```

This keeps vectors small (3-dim) and similarity scores exact/predictable, instead of dealing
with real 768-dim embeddings in assertions.

## `alita_agent/data/faq.json` shape

```jsonc
[
  { "question": "Qual é a política de troca e devolução?", "answer": "..." },
  { "question": "Quanto tempo demora para o pedido chegar?", "answer": "..." }
]
```

## Reset pattern between tests

`faq_rag._index` is module-level global state (the in-memory "vector store"). Each test file
resets it via a `setup_function()` that sets `faq_rag._index = []`, mirroring how `auth`'s
`EcommerceClient` tests get a fresh instance per test via the `test_client` fixture instead of
reusing global state.

---

## References
- [SPEC-faq.md](./SPEC-faq.md)
- [../auth/CONTEXT-auth.md](../auth/CONTEXT-auth.md) — `FakeToolContext`/monkeypatch pattern this
  feature's tests loosely follow (adapted: the mocked seam here is `embed_text`, not `httpx`).
