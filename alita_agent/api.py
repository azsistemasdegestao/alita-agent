import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel

from . import faq_rag, grounding_check, observability
from .agent import CHAT_TOOLS, DESCRIPTION, INSTRUCTION, MODEL, NAME
from .ecommerce_client import client

APP_NAME = "alita_agent"

# Separate Agent instance from `root_agent` (used by adk run/web): it omits
# the `login` tool, since production chat traffic authenticates via the
# request's Authorization header, not a password typed into the chat.
# Low temperature keeps both tool-call decisions and the final narration of
# tool results close to the most-supported wording, reducing (not
# eliminating) the chance of inventing details when describing what a tool
# returned — complements grounding_check.py, which catches what gets through.
chat_agent = Agent(
    model=MODEL,
    name=NAME,
    description=DESCRIPTION,
    instruction=INSTRUCTION,
    tools=CHAT_TOOLS,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)

session_service = InMemorySessionService()
runner = Runner(agent=chat_agent, app_name=APP_NAME, session_service=session_service)

app = FastAPI(title="Alita Agent Chat API")
# Registers tracer/meter providers and instruments FastAPI + httpx globally
# (covering ecommerce_client.py's client and google-adk's own HTTP calls to
# Gemini) before any request is served.
observability.setup(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:4200")],
    allow_methods=["POST"],
    allow_headers=["Authorization", "Content-Type"],
)


class ChatRequest(BaseModel):
    session_id: str
    user_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, authorization: str = Header(...)) -> ChatResponse:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ")

    session = await session_service.get_session(
        app_name=APP_NAME, user_id=req.user_id, session_id=req.session_id
    )
    if session is None:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=req.user_id,
            session_id=req.session_id,
            state={"access_token": token},
        )

    content = types.Content(role="user", parts=[types.Part(text=req.message)])

    reply_text = ""
    tool_activity: list[dict] = []
    async for event in runner.run_async(
        user_id=req.user_id,
        session_id=req.session_id,
        new_message=content,
        state_delta={"access_token": token},
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    reply_text = part.text
                if part.function_call:
                    tool_activity.append(
                        {"tool_call": part.function_call.model_dump(exclude_none=True)}
                    )
                if part.function_response:
                    tool_activity.append(
                        {"tool_result": part.function_response.model_dump(exclude_none=True)}
                    )

    is_grounded, _ = await grounding_check.check_grounding(tool_activity, reply_text)
    if not is_grounded:
        reply_text = grounding_check.FALLBACK_REPLY

    return ChatResponse(reply=reply_text)


@app.on_event("startup")
async def _startup() -> None:
    # Computes the FAQ embeddings once before serving any request, instead of
    # paying that latency on the first /chat call that needs answer_from_faq.
    faq_rag.build_index()


@app.on_event("shutdown")
async def _shutdown() -> None:
    await client.aclose()
    observability.shutdown()
