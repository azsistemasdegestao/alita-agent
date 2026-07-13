# SPEC-faq.md
> Feature: RAG-backed store FAQ/policy answers
> Phase: 1
> Status: Draft

## Context
- [CONTEXT-faq.md](./CONTEXT-faq.md)

---

## Overview

A retrieval-augmented tool that lets the LLM answer general store FAQ/policy questions
(shipping, returns, payment methods, warranty) grounded in a small static knowledge base,
instead of hallucinating store policy. Unlike every other tool in `tools.py`, this one never
calls the Ecommerce API — it's self-contained inside `alita-agent` and needs no auth token.

Two new modules:
- `alita_agent/faq_rag.py` — the retrieval engine: loads `alita_agent/data/faq.json`, embeds
  each entry once with the Gemini embeddings API, and answers queries by cosine-similarity
  ranking. No vector database — an in-memory list is enough for a FAQ-sized corpus.
- `answer_from_faq` in `alita_agent/tools.py` — the ADK tool wrapping `faq_rag.search_faq()`.

---

## Retrieval Engine

### `faq_rag.build_index(faq_path=None) -> None`
`alita_agent/faq_rag.py`

- Reads the JSON array at `faq_path` (defaults to `alita_agent/data/faq.json`), each entry
  `{"question": str, "answer": str}`.
- Computes one embedding per entry (over `f"{question} {answer}"`) via `embed_text()` and
  replaces the module-level `_index` in place.
- Called once at `api.py` startup; under `adk run`/`adk web` it's never called explicitly —
  `search_faq` builds it lazily on first use instead.

### `faq_rag.search_faq(query, top_k=3, min_similarity=0.5) -> list[dict]`
`alita_agent/faq_rag.py`

- Builds the index lazily if empty (`BR-FAQ-003`).
- Embeds `query`, scores every indexed entry by cosine similarity, and returns the `top_k`
  highest-scoring `{"question", "answer"}` dicts — but only those scoring `>= min_similarity`
  (`BR-FAQ-002`). An unrelated question can legitimately return `[]`.

### `answer_from_faq(question) -> dict`
`alita_agent/tools.py`

- Thin wrapper: `{"status": "success", "results": [...]}` when `search_faq` returns entries,
  `{"status": "empty", "results": []}` otherwise (`BR-FAQ-001`).
- Takes no `tool_context` — this tool needs no access token, unlike every other tool in the
  file.

---

## Business Rules

- `BR-FAQ-001` `answer_from_faq` never raises for "no relevant answer" — it returns
  `{"status": "empty", "results": []}` so the model can say "I don't have that information"
  instead of inventing store policy.
- `BR-FAQ-002` Entries scoring below `min_similarity` are excluded from `search_faq`'s result,
  even if the index isn't empty — prevents returning "the least irrelevant" entry as if it were
  a real answer.
- `BR-FAQ-003` `search_faq` builds the index lazily (calls `build_index()`) the first time it
  runs against an empty `_index`, so `adk run`/`adk web` work without any explicit startup step.

---

## Validation Criteria

### Unit Tests

| ID | Scenario | Input | Expected |
|----|----------|-------|----------|
| AC-FAQ-U01 | `build_index` embeds every entry | 2-entry FAQ file, fake `embed_text` | `_index` has 2 chunks, in file order, each with its fake embedding |
| AC-FAQ-U02 | `search_faq` ranks by similarity | Query vector closest to one indexed chunk | That chunk's `{question, answer}` returned first |
| AC-FAQ-U03 | `search_faq` filters low-similarity entries | Query vector orthogonal to every indexed chunk, `min_similarity=0.5` | `[]` |
| AC-FAQ-U04 | `search_faq` builds index lazily | `_index` empty, `FAQ_PATH` monkeypatched | Index gets built and the query still returns a result |
| AC-FAQ-U05 | `answer_from_faq` success | `search_faq` mocked to return entries | `{"status": "success", "results": [...]}` |
| AC-FAQ-U06 | `answer_from_faq` no match | `search_faq` mocked to return `[]` | `{"status": "empty", "results": []}` |

### Integration Tests

N/A for this feature in isolation — covered end-to-end by `chat-api`'s `AC-CHATAPI-I*` tests
once `answer_from_faq` is exercised through a real conversation.

---

## Dependencies

| Dependency | Type | Reason |
|------------|------|--------|
| `google-genai` (`google.genai.Client`) | Runtime | Already a transitive dep of `google-adk`; used directly here for `models.embed_content` — no new pinned package. |

## Feature Dependencies

None — self-contained, no Ecommerce API or auth dependency (unlike every other tool).

---

## Implementation Notes

- Tests live in `tests/unit/faq/test_faq_rag.py` (engine) and `tests/unit/faq/test_tools.py`
  (tool wrapper).
- Unit tests never hit the real embeddings API: they monkeypatch `faq_rag.embed_text` with a
  fixed `text -> vector` mapping, so similarity is fully deterministic and no `GOOGLE_API_KEY`/
  network is required — same spirit as `respx` mocking `httpx` for the Ecommerce API tools, just
  applied to the embeddings call instead since it goes through `google-genai`'s own client, not
  `httpx` directly.
- `alita_agent/data/faq.json` ships with generic placeholder content (shipping, returns, payment
  methods, warranty) — replace it with this store's actual policies before relying on it in
  production.
