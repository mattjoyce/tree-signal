# Repository Guidelines

## Project Structure & Module Organization
Use `tree_signal_spec.md` as the living product brief and update it alongside architecture changes. Place runtime code in `src/tree_signal/` with subpackages for `api` (FastAPI + WebSocket), `layout` (treemap and decay), `storage` (SQLite helpers), and `core` utilities. Mirror those domains in `tests/` via modules like `tests/layout/test_treemap.py`. Keep prototype client assets in `client/`, and store developer helpers in `scripts/`, running them through `uv run python scripts/<task>.py`.

## Build, Test, and Development Commands
Install dependencies with `uv sync` once `pyproject.toml` lands. Launch the API using `uv run uvicorn src.tree_signal.api.main:app --reload`. Run suites with `uv run pytest`, target subsets via `uv run pytest tests/layout -k treemap`, and type-check with `uv run mypy src/tree_signal`. Format before review using `uv run black src/tree_signal tests` and `uv run isort src/tree_signal tests`. Use `uvx pre-commit run --all-files` if hooks are configured.

## Coding Style & Naming Conventions
Adopt 4-space indentation and full type hints on async paths. Keep snake_case for modules, functions, and variables, and use PascalCase for Pydantic models, enums, and service classes. Prefix private helpers with `_`, let `black` drive formatting, enforce imports with `isort --profile black`, and expose supported APIs through package-level `__all__` definitions.

## Testing Guidelines
Write tests with `pytest` and async cases with `pytest-asyncio`; centralise shared fixtures in `tests/conftest.py`. Name files `test_<component>.py`, store sample payloads under `tests/data/`, and aim for ≥85% coverage on the layout engine and WebSocket broadcaster. Add regression tests for decay and scheduling semantics, and use `httpx.AsyncClient` when exercising HTTP or WebSocket contracts.

## UI Theme Guidelines
Align all frontend work with the Tokyo Night palette; document any deviations in `client/README.md`. Set Fira Code as the default monospace font in client stylesheets and ensure fallbacks match its metrics.

## Commit & Pull Request Guidelines
Adopt Conventional Commits (`feat:`, `fix:`, `chore:`) and keep subjects imperative under 72 characters. Pull requests should link tracker tickets, outline behavioural changes, call out new configuration flags, and attach screenshots or `curl` transcripts for API work. Include checkboxes confirming `uv run pytest`, `uv run mypy`, and formatters.

## Security & Configuration Tips
Store credentials like `x-api-key` values in git-ignored `.env` files and load them via FastAPI settings or `uv run python -m dotenv`. Validate and normalise channel paths before enqueueing messages, scrub payloads in logs, and publish sanitised sample configs with rotation notes in `docs/configuration.md`.
