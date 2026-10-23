FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
EXPOSE 8000
ENTRYPOINT ["uv", "run", "--no-sync", "agent-scaffold", "serve", "--host", "0.0.0.0"]
