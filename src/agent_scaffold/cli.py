import argparse
import asyncio
from pathlib import Path

import uvicorn
from pydantic_ai.usage import UsageLimits

from .api import create_app
from .config import Settings, load_settings
from .dependencies import AgentDeps
from .factory import create_agent


async def chat(settings: Settings, message: str | None = None) -> None:
	agent = create_agent(settings)
	history = []
	async with agent:
		if message is None:
			print("AI Agent — type /reset to clear history or /quit to exit.")
		while True:
			if message is None:
				try:
					prompt = await asyncio.to_thread(input, "You: ")
				except EOFError:
					break
			else:
				prompt = message
			prompt = prompt.strip()
			if message is None and prompt == "/quit":
				break
			if message is None and prompt == "/reset":
				history = []
				print("History cleared.")
				continue
			if not prompt:
				if message is not None:
					raise ValueError("Message must contain text.")
				continue
			result = await asyncio.wait_for(
				agent.run(
					prompt,
					deps=AgentDeps(),
					message_history=history,
					usage_limits=UsageLimits(request_limit=settings.request_limit),
				),
				timeout=settings.run_timeout_seconds,
			)
			print(f"Assistant: {result.output}")
			if message is not None:
				break
			history = result.all_messages()


def main() -> None:
	parser = argparse.ArgumentParser(description="Customizable AI agent with Python tools and MCP.")
	commands = parser.add_subparsers(dest="command", required=True)
	for name in ("chat", "serve"):
		command = commands.add_parser(name)
		command.add_argument("--config", type=Path, help="JSON settings file; relative paths use its directory.")
		command.add_argument("--model", help="Provider:model identifier, or test for an offline response.")
		command.add_argument("--workspace", type=Path, help="Enable file access within this directory.")
		command.add_argument("--mcp-config", type=Path, help="Trusted MCP JSON configuration file.")
		if name == "chat":
			command.add_argument("--message", help="Answer one message and exit.")
		else:
			command.add_argument("--host", default="127.0.0.1")
			command.add_argument("--port", type=int, default=8000)
	args = parser.parse_args()
	try:
		settings = load_settings(args.config)
		updates = {}
		for name in ("model", "workspace", "mcp_config"):
			value = getattr(args, name)
			if value is not None:
				updates[name] = value.expanduser().resolve() if isinstance(value, Path) else value
		settings = Settings.model_validate(settings.model_dump() | updates)
		if args.command == "serve":
			uvicorn.run(create_app(settings), host=args.host, port=args.port)
		else:
			asyncio.run(chat(settings, args.message))
	except KeyboardInterrupt:
		pass
	except Exception as exc:
		parser.exit(1, f"Unable to complete command ({type(exc).__name__}). Check configuration and provider access.\n")
