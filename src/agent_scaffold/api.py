import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_ai import Agent
from pydantic_ai.usage import UsageLimits

from .config import Settings
from .dependencies import AgentDeps
from .factory import create_agent
from .history import HistoryMessage, map_history

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
	model_config = ConfigDict(extra="forbid")
	message: str = Field(min_length=1, max_length=12_000)
	history: list[HistoryMessage] = Field(default_factory=list, max_length=20)

	@field_validator("message")
	@classmethod
	def require_text(cls, value: str) -> str:
		if not value.strip():
			raise ValueError("Message must contain text.")
		return value


class ChatResponse(BaseModel):
	role: Literal["assistant"] = "assistant"
	content: str
	total_tokens: int


def create_app(settings: Settings | None = None, *, agent: Agent[AgentDeps, str] | None = None) -> FastAPI:
	"""Create a stateless local API; inject an agent for tests or application integration."""
	settings = settings or Settings()

	@asynccontextmanager
	async def lifespan(app: FastAPI):
		assistant = agent if agent is not None else create_agent(settings)
		async with assistant:
			app.state.assistant = assistant
			try:
				yield
			finally:
				app.state.assistant = None

	app = FastAPI(title="General AI Agent API", version="0.1.0", lifespan=lifespan)
	app.state.assistant = None

	@app.get("/")
	async def root() -> dict:
		return {"name": app.title, "mode": settings.model, "routes": ["GET /health", "POST /chats"]}

	@app.get("/health")
	async def health() -> dict:
		if app.state.assistant is None:
			raise HTTPException(503, "Agent is not ready.")
		return {"status": "ok"}

	@app.post("/chats", response_model=ChatResponse)
	async def chat(payload: ChatRequest) -> ChatResponse:
		assistant = app.state.assistant
		if assistant is None:
			raise HTTPException(503, "Agent is not ready.")
		try:
			result = await asyncio.wait_for(
				assistant.run(
					payload.message,
					deps=AgentDeps(),
					message_history=map_history(payload.history),
					usage_limits=UsageLimits(request_limit=settings.request_limit),
				),
				timeout=settings.run_timeout_seconds,
			)
		except TimeoutError as exc:
			raise HTTPException(504, "Agent response timed out.") from exc
		except Exception as exc:
			logger.warning("Agent run failed (%s).", type(exc).__name__)
			raise HTTPException(502, "Agent could not complete the request.") from exc
		return ChatResponse(content=result.output, total_tokens=result.usage.total_tokens)

	return app
