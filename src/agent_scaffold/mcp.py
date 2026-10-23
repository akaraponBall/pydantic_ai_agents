from pathlib import Path

from fastmcp.client.transports import StdioTransport
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.toolsets import AbstractToolset


class ServerConfig(BaseModel):
	"""Only trusted local configuration may select commands or service endpoints."""

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

	command: str | None = Field(default=None, min_length=1)
	args: list[str] = Field(default_factory=list)
	cwd: Path | None = None
	url: HttpUrl | None = None

	@model_validator(mode="after")
	def validate_transport(self) -> "ServerConfig":
		if (self.command is None) == (self.url is None):
			raise ValueError("Specify exactly one of command or url for each MCP server.")
		if self.url is not None and (self.args or self.cwd is not None):
			raise ValueError("args and cwd apply only to command-based servers.")
		return self


class MCPConfig(BaseModel):
	model_config = ConfigDict(extra="forbid")
	mcpServers: dict[str, ServerConfig]


def load_toolsets(path: Path | None) -> list[AbstractToolset]:
	"""Build namespaced MCP connections without connecting until the agent is entered."""
	if path is None:
		return []
	path = path.expanduser().resolve()
	config = MCPConfig.model_validate_json(path.read_text(encoding="utf-8"))
	toolsets = []
	for name, server in config.mcpServers.items():
		if not name.isascii() or not name.isidentifier():
			raise ValueError("MCP server names must be ASCII identifiers, such as local_tools.")
		if server.command is not None:
			cwd = server.cwd.expanduser() if server.cwd is not None else path.parent
			if not cwd.is_absolute():
				cwd = path.parent / cwd
			transport = StdioTransport(command=server.command, args=server.args, cwd=str(cwd.resolve()))
			toolset = MCPToolset(transport, id=name)
		else:
			toolset = MCPToolset(str(server.url), id=name)
		toolsets.append(toolset.prefixed(name))
	return toolsets
