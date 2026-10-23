from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Settings(BaseModel):
	"""Explicit settings; no environment-file loading or application environment variables."""

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

	model: str = Field(default="test", min_length=1)
	additional_instructions: str = ""
	workspace: Path | None = None
	mcp_config: Path | None = None
	request_limit: int = Field(default=12, gt=0)
	run_timeout_seconds: float = Field(default=60, gt=0, allow_inf_nan=False)

	@field_validator("workspace", "mcp_config", mode="before")
	@classmethod
	def reject_empty_path(cls, value: object) -> object:
		if isinstance(value, str) and not value.strip():
			raise ValueError("Use null to disable an optional path.")
		return value


def load_settings(path: str | Path | None = None) -> Settings:
	"""Resolve paths against the config file so the project can be moved freely."""
	if path is None:
		return Settings()
	config_path = Path(path).expanduser().resolve()
	settings = Settings.model_validate_json(config_path.read_text(encoding="utf-8"))
	resolved = {}
	for name in ("workspace", "mcp_config"):
		value = getattr(settings, name)
		if value is not None:
			value = value.expanduser()
			resolved[name] = (config_path.parent / value).resolve() if not value.is_absolute() else value.resolve()
	return settings.model_copy(update=resolved)
