.PHONY: test check format

test:
	uv run python -m unittest discover -s tests -v

check:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
