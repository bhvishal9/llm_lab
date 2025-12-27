FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN groupadd -r llm_lab && useradd -r -g llm_lab llm_lab --home /app
USER llm_lab
WORKDIR /app
EXPOSE 8000
COPY --chown=llm_lab:llm_lab assets/indexed_chunks.json /app/assets/indexed_chunks.json
COPY --chown=llm_lab:llm_lab pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-install-project
COPY --chown=llm_lab:llm_lab src /app/src
RUN uv sync --frozen
ENTRYPOINT ["uv", "run", "uvicorn", "llm_lab.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]