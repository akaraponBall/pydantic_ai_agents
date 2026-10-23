import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from pydantic_ai import ModelRetry
from pydantic_ai.messages import ModelResponse, RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from agent_scaffold.config import Settings
from agent_scaffold.dependencies import AgentDeps
from agent_scaffold.factory import create_agent
from agent_scaffold.tools import calculate


class ArithmeticTests(unittest.TestCase):
	def test_operations(self):
		for operation, expected in (("add", 10), ("subtract", 6), ("multiply", 16), ("divide", 4)):
			with self.subTest(operation=operation):
				self.assertEqual(calculate(8, operation, 2), expected)

	def test_invalid_arithmetic_produces_recoverable_feedback(self):
		for left, operation, right in (
			(1, "divide", 0),
			(float("nan"), "add", 1),
			(1e308, "multiply", 1e308),
			(1, "unknown", 2),
		):
			with self.subTest(operation=operation), self.assertRaises(ModelRetry):
				calculate(left, operation, right)


class AgentTests(unittest.IsolatedAsyncioTestCase):
	async def test_default_agent_runs_offline(self):
		agent = create_agent()
		async with agent:
			result = await agent.run("Hello", deps=AgentDeps())
		self.assertIn("Local test response", result.output)

	async def test_python_tools_receive_correct_arguments_and_run_context(self):
		timestamp = datetime(2030, 1, 2, 3, 4, tzinfo=UTC)

		def respond(messages, info):
			returns = [part for message in messages for part in message.parts if isinstance(part, ToolReturnPart)]
			if not returns:
				self.assertEqual({tool.name for tool in info.function_tools}, {"calculate", "get_current_time"})
				return ModelResponse(
					parts=[
						ToolCallPart("calculate", {"left": 3, "operation": "multiply", "right": 7}, "calc"),
						ToolCallPart("get_current_time", {}, "time"),
					]
				)
			self.assertEqual(
				{part.tool_name: part.content for part in returns},
				{"calculate": 21, "get_current_time": timestamp.isoformat()},
			)
			return ModelResponse(parts=[TextPart("Tool results verified.")])

		agent = create_agent(model=FunctionModel(respond))
		async with agent:
			result = await agent.run("Calculate and check the time", deps=AgentDeps(current_time=timestamp))
		self.assertEqual(result.output, "Tool results verified.")

	async def test_stdio_mcp_tool_executes_and_connection_closes(self):
		script = Path(__file__).resolve().parents[1] / "examples" / "mcp_server.py"

		def respond(messages, info):
			returns = [part for message in messages for part in message.parts if isinstance(part, ToolReturnPart)]
			if not returns:
				self.assertIn("example_count_words", {tool.name for tool in info.function_tools})
				return ModelResponse(parts=[ToolCallPart("example_count_words", {"text": "one two three"}, "words")])
			self.assertIn("3", str(returns[-1].content))
			return ModelResponse(parts=[TextPart("Three words.")])

		with tempfile.TemporaryDirectory() as directory:
			path = Path(directory) / "mcp.json"
			path.write_text(json.dumps({"mcpServers": {"example": {"command": sys.executable, "args": [str(script)]}}}))
			agent = create_agent(Settings(mcp_config=path), model=FunctionModel(respond))
			async with agent:
				result = await agent.run("Count words", deps=AgentDeps())
			self.assertEqual(result.output, "Three words.")

	async def test_filesystem_writes_stay_in_configured_workspace(self):
		def respond(messages, info):
			returns = [part for message in messages for part in message.parts if isinstance(part, ToolReturnPart)]
			if not returns:
				return ModelResponse(parts=[ToolCallPart("write_file", {"path": "note.txt", "content": "example"})])
			return ModelResponse(parts=[TextPart("Saved.")])

		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory) / "workspace"
			agent = create_agent(Settings(workspace=root), model=FunctionModel(respond))
			async with agent:
				await agent.run("Create a note", deps=AgentDeps())
			self.assertEqual((root / "note.txt").read_text(), "example")

	async def test_filesystem_rejects_parent_traversal_and_external_symlinks(self):
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory) / "workspace"
			root.mkdir()
			outside = Path(directory) / "outside.txt"
			outside.write_text("private-example-text")
			(root / "link.txt").symlink_to(outside)
			for forbidden_path in ("../outside.txt", "link.txt"):
				with self.subTest(path=forbidden_path):

					def respond(messages, info, path=forbidden_path):
						feedback = [
							part for message in messages for part in message.parts if isinstance(part, RetryPromptPart)
						]
						if not feedback:
							return ModelResponse(parts=[ToolCallPart("read_file", {"path": path})])
						self.assertNotIn("private-example-text", str(feedback))
						return ModelResponse(parts=[TextPart("Access denied.")])

					agent = create_agent(Settings(workspace=root), model=FunctionModel(respond))
					async with agent:
						result = await agent.run("Read a file", deps=AgentDeps())
					self.assertEqual(result.output, "Access denied.")
