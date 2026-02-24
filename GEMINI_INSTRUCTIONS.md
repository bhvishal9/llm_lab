# Gemini CLI Instructions for llm-lab

This document outlines the conventions, tools, and workflows to be followed when working on the `llm-lab` project.

## 1. Project Overview

- **Purpose**: A FastAPI application that provides a RAG (Retrieval-Augmented Generation) service using a Google Gemini LLM.
- **Source Code**: The main application code is located in the `src/llm_lab` directory.
- **Infrastructure**: Infrastructure is managed with Terraform and located in the `infra` directory.

## 2. Setup and Dependencies

- **Python Version**: The project requires Python 3.14 or newer.
- **Package Manager**: This project uses `uv` for package and virtual environment management.
- **Installation**: To set up the development environment, run the following command from the project root. This will install all production and development dependencies.
  ```bash
  uv pip install -e ".[dev]"
  ```
- **Configuration**: The application requires a Google Gemini API key. This key must be set as an environment variable:
  ```bash
  export LLM_API_KEY="your-api-key"
  ```

## 3. Development Workflow

### Running the Application

- To run the FastAPI web server for development (with hot-reloading), use the following command:
  ```bash
  uvicorn src.llm_lab.api.main:app --reload
  ```

### Code Style and Quality

The project enforces strict code quality standards using `ruff` and `mypy`.

- **Formatting**: To format the entire codebase, run:
  ```bash
  ruff format .
  ```
- **Linting**: To check for linting errors, run:
  ```bash
  ruff check .
  ```
- **Type Checking**: To perform static type checking, run:
  ```bash
  mypy src tests
  ```

### Testing

- **Running Tests**: The project uses `pytest`. To run the full test suite, use:
  ```bash
  pytest
  ```
- **Test Coverage**: The test configuration is set up to automatically report on code coverage for the `llm_lab` package, highlighting any lines not covered by tests.

### Committing Changes

- **Pre-commit Hooks**: Before any code is committed, a series of pre-commit hooks are executed to ensure code quality. These hooks are defined in `.pre-commit-config.yaml` and include:
    1.  `ruff format`: Checks formatting.
    2.  `ruff`: Checks for linting errors.
    3.  `mypy`: Performs static type analysis.
    4.  `pytest`: Runs the entire test suite.
- **Commit Failure**: If any of these hooks fail, the commit will be aborted. You must fix the reported issues before you can successfully commit your changes.

## 4. Architectural Patterns

The application follows a modular, protocol-oriented design.

- **Protocols**: The core logic relies on protocols (interfaces) for extensibility. Key protocols are `LlmClient` (for language model interactions) and `VectorStoreClient` (for data retrieval).
- **Concrete Implementations**:
    - **LLM**: The `GeminiClient` is the concrete implementation of `LlmClient`, handling communication with the Google Gemini API.
    - **Vector Store**: The `FileStoreClient` is the concrete implementation of `VectorStoreClient`. It is not a traditional database but a file-system-based solution using an `Indexer` to pre-calculate and store embeddings and a `Retriever` to find and score relevant text chunks at query time.
- **Core Service**: The `RagService` orchestrates the RAG pipeline. It is initialized with a specific `LlmClient` and `dataset`. Its `answer_question` method queries the vector store for context and then calls the LLM to generate an answer.
- **API Layer (FastAPI)**:
    - Endpoints are defined in `src/llm_lab/api/routers/`.
    - **Dependency Injection**: FastAPI's `Depends` system is used to provide dependencies, most importantly the `LlmClient`. The `get_llm_client` function in `src/llm_lab/api/dependencies.py` is responsible for creating the `GeminiClient`.
    - **Configuration**: The `get_settings` function uses `pydantic-settings` to load configuration from environment variables. This is used in the dependency injection system to configure the `GeminiClient` with the correct API keys and model names.
- **Modularity**: Adhere to the existing modular structure. New functionality should be placed in the appropriate directory (e.g., `retrieval`, `llm`, `vector_store`) and, where appropriate, should implement the existing protocols.
