"""Local test-mode ASGI entrypoint. Use the CLI to supply application settings."""

from agent_scaffold.api import create_app

app = create_app()
