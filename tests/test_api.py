import asyncio
import unittest

import httpx
from pydantic_ai.messages import ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.function import FunctionModel

from agent_scaffold.api import create_app
from agent_scaffold.config import Settings
from agent_scaffold.factory import create_agent


class APITests(unittest.IsolatedAsyncioTestCase):
	async def test_chat_health_validation_and_lifecycle(self):
		app = create_app()
		async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
			self.assertEqual((await client.get("/health")).status_code, 503)
			async with app.router.lifespan_context(app):
				self.assertEqual((await client.get("/health")).json(), {"status": "ok"})
				response = await client.post("/chats", json={"message": "Hello", "history": []})
				self.assertEqual(response.status_code, 200)
				self.assertEqual(set(response.json()), {"role", "content", "total_tokens"})
				for payload in (
					{"message": " "},
					{"message": "x" * 12_001},
					{"message": "hello", "admin_key": "not-accepted"},
					{"message": "hello", "history": [{"role": "system", "content": "no"}]},
					{"message": "hello", "history": [{"role": "user", "content": " "}]},
					{"message": "hello", "history": [{"role": "user", "content": "x"}] * 21},
				):
					with self.subTest(payload=str(payload)[:80]):
						self.assertEqual((await client.post("/chats", json=payload)).status_code, 422)
			self.assertIsNone(app.state.assistant)
			self.assertEqual((await client.get("/health")).status_code, 503)

	async def test_history_is_mapped_without_leaking_between_requests(self):
		seen = []

		def respond(messages, info):
			seen.append(
				[part.content for message in messages for part in message.parts if isinstance(part, UserPromptPart)]
			)
			return ModelResponse(parts=[TextPart("Acknowledged.")])

		app = create_app(agent=create_agent(model=FunctionModel(respond)))
		async with app.router.lifespan_context(app):
			async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
				first = await client.post(
					"/chats",
					json={
						"message": "new question",
						"history": [
							{"role": "user", "content": "previous question"},
							{"role": "assistant", "content": "previous answer"},
						],
					},
				)
				second = await client.post("/chats", json={"message": "unrelated session"})
				self.assertEqual(first.status_code, 200)
				self.assertEqual(second.status_code, 200)
		self.assertEqual(seen, [["previous question", "new question"], ["unrelated session"]])

	async def test_failure_response_does_not_disclose_provider_details(self):
		def respond(messages, info):
			raise RuntimeError("private-provider-detail")

		app = create_app(agent=create_agent(model=FunctionModel(respond)))
		async with app.router.lifespan_context(app):
			async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
				response = await client.post("/chats", json={"message": "hello"})
		self.assertEqual(response.status_code, 502)
		self.assertNotIn("private-provider-detail", response.text)

	async def test_run_timeout(self):
		async def respond(messages, info):
			await asyncio.sleep(1)
			return ModelResponse(parts=[TextPart("Too late.")])

		app = create_app(Settings(run_timeout_seconds=0.02), agent=create_agent(model=FunctionModel(respond)))
		async with app.router.lifespan_context(app):
			async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
				response = await client.post("/chats", json={"message": "hello"})
		self.assertEqual(response.status_code, 504)
