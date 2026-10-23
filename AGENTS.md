# General AI Agent Scaffold — Contributor Guide

## Purpose

This is an application-neutral Python agent starter. Keep defaults reusable and
put project-specific integrations behind tools and trusted dependencies. Do not add
organization names, customer data, credentials, or production infrastructure to the
starter configuration.

## Layout

| File | Responsibility |
| --- | --- |
| `src/agent_scaffold/factory.py` | Assemble the Pydantic AI agent, tools, capabilities, and runtime instructions |
| `src/agent_scaffold/prompts.py` | General role and tool-use guidance |
| `src/agent_scaffold/dependencies.py` | Trusted per-run context and future service interfaces |
| `src/agent_scaffold/tools.py` | Small example Python tools |
| `src/agent_scaffold/config.py` | Strict JSON settings and portable path resolution |
| `src/agent_scaffold/mcp.py` | Strict stdio/HTTP MCP settings and prefixed toolsets |
| `src/agent_scaffold/history.py` | Plain conversation DTOs and model message mapping |
| `src/agent_scaffold/api.py` | Local stateless FastAPI application and error boundaries |
| `src/agent_scaffold/cli.py` | Chat and API commands |
| `examples/mcp_server.py` | Credential-free local MCP example |
| `tests/` | Offline behavior and integration checks |

## Commands

```bash
uv sync
uv run agent-scaffold chat
uv run agent-scaffold serve
uv run python -m unittest discover -s tests -v
uv run ruff check .
uv run ruff format .
uv run ruff format --check .
```

Use Python 3.11 or newer. Pydantic AI is pinned to the 2.21 release series; Harness
is pinned to the 0.14 series. Check installed signatures and official documentation
before changing framework integrations. Keep `pyproject.toml` and `uv.lock` in sync.

## Style

- Use tabs, double quotes, a 120-character line limit, and Ruff's configured rules.
- Use descriptive names and short docstrings that explain public tool behavior.
- Use standard logging without writing prompts, credentials, or tool results to disk.
- Resolve configured paths relative to the configuration file, not a fixed checkout.
- Keep example data synthetic and application-neutral.

## Agent composition

Use `create_agent(settings, extra_tools=..., extra_toolsets=...)` for agent creation.
Keep durable role rules in `SYSTEM_PROMPT` and workflow guidance in `INSTRUCTIONS`.
`additional_instructions` is trusted application configuration, not a client request
field. Pass timestamps and application services using a fresh `AgentDeps` per run;
do not attach request-specific state to a shared agent.

For a custom tool, add a typed function with a descriptive docstring. Register it
with `Tool(..., takes_ctx=False)`, or `takes_ctx=True` when its first argument is
`RunContext[AgentDeps]`. Enforce access restrictions in the tool or service layer.
Use `ModelRetry` for recoverable bad tool inputs. Add meaningful checks for the
behavior and failure modes introduced by a new integration.

## Filesystem and MCP

Filesystem tools are enabled only when `workspace` is explicitly configured and
are scoped by Harness `FileSystem(root_dir=...)`. This grants file writes in that
directory. Preserve unrelated content and do not weaken path boundaries.

MCP is disabled unless `mcp_config` is supplied. Load only trusted JSON configuration
from disk; API callers cannot supply server commands or URLs. Each server selects
exactly one transport: `command` with optional `args`/`cwd`, or an HTTP `url`.
Configuration fields outside this format are rejected. Server names must be ASCII
identifiers and are used as tool prefixes. Keep connections inside `async with
agent` so clients and subprocesses close cleanly. MCP server permissions are
independent of the filesystem workspace.

## API contract

`POST /chats` accepts `message` and optional `history`. Each history item has a
`user` or `assistant` role and non-empty content. Requests contain at most 20 history
messages; each message is limited to 12,000 characters. The current message is sent
separately and must not be repeated in history. Unknown request fields are rejected.
Responses include only assistant text and token usage, never native model history.

The API does not persist conversations. CLI history is in memory until `/reset` or
exit. Both entrypoints enforce a run timeout and a model request limit. API errors
contain generic messages without provider details. Keep exceptions out of public
responses and keep secrets out of logs. The starter API is local and unauthenticated;
add application-specific authentication before deploying a shared service.

## Configuration and testing

Do not create checked-in secrets or `.env` files. The starter reads explicit JSON
and CLI options, with no application environment variables or telemetry setup.
Providers may require external process credentials; leave that to deployment setup.
Update example settings and README when configuration or commands change.

Use `unittest.IsolatedAsyncioTestCase` for asynchronous tests, `TestModel` or
`FunctionModel` for agent tests, and `httpx.ASGITransport` with an explicit lifespan
context for API tests. Test actual tool calls and lifecycle cleanup, not only tool
registration. Tests must remain offline and credential-free. Never call paid model
providers as part of the default suite. Run tests and Ruff checks before delivery.
