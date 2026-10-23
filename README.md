# General AI Agent Scaffold

A small Python starter for building an assistant for any application. It provides a
Pydantic AI agent, two example Python tools, optional scoped filesystem access,
optional MCP connections, an interactive CLI, and a stateless FastAPI endpoint.

The default `test` mode returns a fixed local response. It does not generate answers,
contact a model provider, or call tools. Choose a provider model when you are ready
to use generated responses.

## Quick start

Requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run agent-scaffold chat --message "Hello"
uv run agent-scaffold chat
uv run agent-scaffold serve
```

The API defaults to `http://127.0.0.1:8000`. Its interactive documentation is at
`http://127.0.0.1:8000/docs`. Stop the server with Ctrl+C. In interactive chat,
`/quit` exits and `/reset` clears the in-memory conversation.

```bash
curl http://127.0.0.1:8000/chats \
  -H 'Content-Type: application/json' \
  -d '{"message":"Hello","history":[]}'
```

The response contains `role`, `content`, and `total_tokens`. `GET /health` reports
whether the agent has started. History is supplied by the caller as ordinary
`user`/`assistant` messages; omit the current message from that history. No chats
are stored on disk or kept between API requests.

## Configuration

Copy `settings.example.json` to `settings.local.json` and edit it, or pass options
directly:

```bash
uv run agent-scaffold chat --config settings.local.json
uv run agent-scaffold chat --model provider:model-name
uv run agent-scaffold serve --config settings.local.json
uv run agent-scaffold chat --workspace ./workspace
```

`provider:model-name` is a placeholder for a supported Pydantic AI model identifier.
Configure provider authentication outside this project using that provider's
supported mechanism. This starter does not read `.env` files, define application
environment variables, bundle credentials, or enable telemetry exports. Provider
SDKs may use credentials from the process environment or an external credential
store. See [Pydantic AI providers](https://ai.pydantic.dev/models/overview/).

Settings:

| Field | Default | Purpose |
| --- | --- | --- |
| `model` | `"test"` | Offline test mode or a provider model identifier |
| `additional_instructions` | `""` | Extra application-level guidance |
| `workspace` | `null` | Enable read/write file tools within the selected directory |
| `mcp_config` | `null` | Load an explicitly selected MCP configuration |
| `request_limit` | `12` | Maximum model requests within one agent run |
| `run_timeout_seconds` | `60` | Time limit for an answer, including its tool calls |

Paths in a settings file resolve relative to that file. Paths passed on the command
line resolve relative to the current directory. No paths reference the original
checkout location, so the folder can be moved. Workspace access and MCP connections
are disabled by default. Enabling a workspace permits the agent to edit files there.

## Custom Python tools and prompts

`src/agent_scaffold/tools.py` contains `calculate` and `get_current_time`. The time
tool receives trusted per-run data through `AgentDeps`; the model supplies only
the tool arguments it needs. Add your own tools through `create_agent(extra_tools=...)`:

```python
from pydantic_ai import Tool
from agent_scaffold.factory import create_agent


def count_characters(text: str) -> int:
	"""Return the length of the supplied text."""
	return len(text)


agent = create_agent(extra_tools=[Tool(count_characters, takes_ctx=False)])
```

Use `takes_ctx=True` for tools that receive `RunContext[AgentDeps]`. Put service
interfaces, access checks, and request context in dependencies rather than
model-visible tool arguments. Edit `prompts.py` for the role and default workflow;
use `additional_instructions` for deployment-specific guidance. Extend
`dependencies.py` when the application needs additional trusted per-run context.

The default prompt is general guidance. Applications must implement their own
authorization, confirmation flows, and domain-specific validation in code where
needed; prompt instructions alone do not enforce those controls.

## MCP tools

MCP toolsets use Pydantic AI's client and are opened and closed with the agent's
async context. Each server's tools receive the server name as a prefix to avoid
collisions. Both command-based stdio servers and HTTP servers are supported.
See the [Pydantic AI MCP client documentation](https://ai.pydantic.dev/mcp/client/).

To try the bundled local example, create `mcp.local.json` in the project root:

```json
{
  "mcpServers": {
    "example": {
      "command": "uv",
      "args": ["run", "--no-sync", "python", "examples/mcp_server.py"]
    }
  }
}
```

```bash
uv run agent-scaffold chat --mcp-config mcp.local.json --model provider:model-name
```

The example exposes `example_count_words`. Test mode can check startup and MCP
connection setup, but it does not invoke these tools. The automated tests exercise
an actual local MCP tool call without a model provider.

For an already-running HTTP server, use an entry such as
`{"url":"http://127.0.0.1:9000/mcp"}` instead of `command` and `args`. Optional
`cwd` applies only to stdio servers and resolves relative to the MCP file. Without
`cwd`, the MCP file's directory is used. Only load MCP configurations you trust:
stdio entries run programs with your local permissions, and external servers have
their own access policies. MCP access is separate from the filesystem workspace.
The strict starter format accepts `command`, `args`, `cwd`, or `url`; it does not
provide credential fields, headers, environment mappings, or variable expansion.

## API integration and packaging

Use `create_app(settings, agent=...)` to embed the API or inject a test agent.
`api_server.py` is a convenience ASGI entrypoint in local test mode. The CLI's
`serve` command accepts the same settings as chat, plus `--host` and `--port`.
The starter API has no authentication and binds to loopback by default. Add
authentication and authorization before exposing it to other users.

```bash
uv run uvicorn api_server:app --host 127.0.0.1 --port 8000
uv build
docker build -t agent-scaffold .
docker run --rm -p 127.0.0.1:8000:8000 agent-scaffold
```

The container also starts in offline test mode. To use a settings file, mount it
and pass `--config /path/to/settings.json` after the image name. Supply any provider
credentials through your own external runtime setup.

## Verification

```bash
make test
make check
```

Tests cover arithmetic edge cases, configuration and path resolution, Python tool
execution, local MCP execution, API validation, conversation isolation, failures,
timeouts, and connection lifecycle. They do not require provider credentials or
make paid model requests. `uv.lock` records dependency versions. Runtime
environments and generated caches are disposable and are recreated when installing
or running the project.
