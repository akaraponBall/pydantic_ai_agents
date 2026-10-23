from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class AgentDeps:
	"""Trusted per-run context; extend with application service interfaces as needed."""

	current_time: datetime = field(default_factory=lambda: datetime.now(UTC))
	task_context: str = ""
