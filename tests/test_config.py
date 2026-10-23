import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from agent_scaffold.config import Settings, load_settings
from agent_scaffold.mcp import load_toolsets


class ConfigurationTests(unittest.TestCase):
	def test_defaults_disable_external_integrations(self):
		settings = load_settings()
		self.assertEqual(settings.model, "test")
		self.assertIsNone(settings.workspace)
		self.assertEqual(load_toolsets(settings.mcp_config), [])

	def test_paths_resolve_relative_to_settings_file(self):
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			config = root / "settings.json"
			config.write_text(json.dumps({"workspace": "data", "mcp_config": "tools.json"}))
			settings = load_settings(config)
			self.assertEqual(settings.workspace, root / "data")
			self.assertEqual(settings.mcp_config, root / "tools.json")

	def test_settings_reject_invalid_limits_unknown_fields_and_empty_paths(self):
		for values in (
			{"model": " "},
			{"request_limit": 0},
			{"run_timeout_seconds": -1},
			{"run_timeout_seconds": float("inf")},
			{"workspace": ""},
			{"unexpected": True},
		):
			with self.subTest(values=values), self.assertRaises(ValidationError):
				Settings.model_validate(values)

	def test_mcp_rejects_ambiguous_and_malformed_transports(self):
		for server in (
			{},
			{"command": " "},
			{"command": "python", "url": "http://localhost:9000/mcp"},
			{"url": "file:///tmp/server"},
			{"url": "http://localhost:9000/mcp", "args": ["bad"]},
			{"command": "python", "args": "wrong-type"},
			{"command": "python", "env": {"SECRET": "not-supported"}},
		):
			with self.subTest(server=server), tempfile.TemporaryDirectory() as directory:
				path = Path(directory) / "mcp.json"
				path.write_text(json.dumps({"mcpServers": {"example": server}}))
				with self.assertRaises(ValidationError):
					load_toolsets(path)

	def test_mcp_rejects_invalid_prefix(self):
		with tempfile.TemporaryDirectory() as directory:
			path = Path(directory) / "mcp.json"
			path.write_text(json.dumps({"mcpServers": {"bad name": {"command": "python"}}}))
			with self.assertRaises(ValueError):
				load_toolsets(path)
