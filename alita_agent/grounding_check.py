"""Post-response grounding check: catches the agent inventing facts not backed by a tool result.

Runs synchronously on every `/chat` turn (api.py), after the agent's reply is
generated and before it reaches the customer. A single cheap judge call, not
the full sentence-by-sentence pipeline used by the offline eval set
(tests/integration/eval/) — that one is thorough but too slow/costly to run
inline on every real chat message.
"""

import json
import logging

from google import genai

from .agent import INSTRUCTION, MODEL

logger = logging.getLogger(__name__)

FALLBACK_REPLY = (
    "Não tenho certeza sobre essa informação com o que consultei até agora. "
    "Pode reformular a pergunta? Vou preferir confirmar a te dar um dado errado."
)

_JUDGE_PROMPT = """
You are a strict fact-checker for a customer support chat assistant.

You will be given the assistant's system instructions, the tool calls it made
this turn along with their results (there may be none, if no tool was
needed), and the assistant's final reply to the customer.

Decide whether the final reply is fully grounded: every factual claim about a
product, order, payment, cart or store policy must be directly supported by
the tool results shown below. If no tool was called, the reply must not state
any such fact — it may greet the user, ask a clarifying question, or say it
doesn't know.

Respond with exactly one line:
GROUNDED
or
UNGROUNDED: <short reason>

**Assistant instructions:**
{instructions}

**Tool calls and results this turn:**
{tool_activity}

**Assistant's final reply:**
{reply}
""".strip()

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    # Lazy singleton, same reasoning as faq_rag._get_client: importing this
    # module never requires GOOGLE_API_KEY, only actually calling check_grounding().
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


def _format_tool_activity(tool_activity: list[dict]) -> str:
    if not tool_activity:
        return "(no tool was called this turn)"
    return json.dumps(tool_activity, indent=2, ensure_ascii=False)


async def check_grounding(tool_activity: list[dict], reply: str) -> tuple[bool, str]:
    """Returns (is_grounded, raw_judge_output). Fails open (grounded) on judge errors."""
    if not reply.strip():
        return True, "empty reply, nothing to check"

    prompt = _JUDGE_PROMPT.format(
        instructions=INSTRUCTION,
        tool_activity=_format_tool_activity(tool_activity),
        reply=reply,
    )
    try:
        response = await _get_client().aio.models.generate_content(
            model=MODEL, contents=prompt
        )
    except Exception:
        logger.exception("Grounding check judge call failed; letting the reply through")
        return True, "judge call failed"

    verdict = (response.text or "").strip()
    is_grounded = verdict.upper().startswith("GROUNDED")
    if not is_grounded:
        logger.warning("Ungrounded reply blocked: %s | reply=%r", verdict, reply)
    return is_grounded, verdict
