import math
from typing import Literal

from pydantic_ai import ModelRetry, RunContext

from .dependencies import AgentDeps


def get_current_time(ctx: RunContext[AgentDeps]) -> str:
	"""Return the trusted timestamp for the current run in ISO 8601 format."""
	return ctx.deps.current_time.isoformat()


def calculate(left: float, operation: Literal["add", "subtract", "multiply", "divide"], right: float) -> float:
	"""Calculate a basic arithmetic operation on two finite numbers."""
	if not math.isfinite(left) or not math.isfinite(right):
		raise ModelRetry("Supply finite numbers.")
	if operation == "add":
		result = left + right
	elif operation == "subtract":
		result = left - right
	elif operation == "multiply":
		result = left * right
	elif operation == "divide":
		if right == 0:
			raise ModelRetry("Division by zero is undefined. Choose a nonzero divisor.")
		result = left / right
	else:
		raise ModelRetry("Choose add, subtract, multiply, or divide.")
	if not math.isfinite(result):
		raise ModelRetry("The result is outside the supported numeric range.")
	return result
