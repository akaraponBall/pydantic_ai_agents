from collections.abc import Sequence

from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel
from pydantic_ai.toolsets import AbstractToolset
from pydantic_ai_harness import FileSystem

from .config import Settings
from .dependencies import AgentDeps
from .mcp import load_toolsets
from .prompts import INSTRUCTIONS, SYSTEM_PROMPT
from .tools import calculate, get_current_time


def create_agent(
	settings: Settings | None = None,
	*,
	model: Model | None = None,
	extra_tools: Sequence[Tool] = (),
	extra_toolsets: Sequence[AbstractToolset] = (),
) -> Agent[AgentDeps, str]:
	"""Compose prompts, Python tools, optional scoped files, and optional MCP servers."""
	settings = settings or Settings()
	selected_model = model
	if selected_model is None:
		selected_model = (
			TestModel(
				call_tools=[],
				custom_output_text="Local test response. Configure a model provider for generated answers.",
			)
			if settings.model == "test"
			else settings.model
		)
	capabilities = []
	if settings.workspace is not None:
		workspace = settings.workspace.expanduser().resolve()
		workspace.mkdir(parents=True, exist_ok=True)
		capabilities.append(FileSystem(root_dir=workspace))
	agent = Agent(
		selected_model,
		deps_type=AgentDeps,
		system_prompt=SYSTEM_PROMPT,
		instructions=[INSTRUCTIONS, settings.additional_instructions],
		tools=[Tool(get_current_time, takes_ctx=True), Tool(calculate, takes_ctx=False), *extra_tools],
		toolsets=[*load_toolsets(settings.mcp_config), *extra_toolsets],
		capabilities=capabilities,
	)

	@agent.instructions
	def runtime_context(ctx: RunContext[AgentDeps]) -> str:
		return f"Run timestamp: {ctx.deps.current_time.isoformat()}\nApplication task context: {ctx.deps.task_context}"

	return agent
