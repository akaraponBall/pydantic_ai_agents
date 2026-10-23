from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart


class HistoryMessage(BaseModel):
	model_config = ConfigDict(extra="forbid")
	role: Literal["user", "assistant"]
	content: str = Field(min_length=1, max_length=12_000)

	@field_validator("content")
	@classmethod
	def require_text(cls, value: str) -> str:
		if not value.strip():
			raise ValueError("Content must contain text.")
		return value


def map_history(history: list[HistoryMessage]) -> list[ModelMessage]:
	"""Map ordinary chat messages without accepting provider-specific history objects."""
	return [
		ModelRequest(parts=[UserPromptPart(message.content)])
		if message.role == "user"
		else ModelResponse(parts=[TextPart(message.content)])
		for message in history
	]
