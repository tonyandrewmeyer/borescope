.DEFAULT_GOAL := help

.PHONY: help lint fmt test integration docs

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

lint:  ## Lint with ruff and type-check with ty
	uv run --group dev ruff check src tests
	uv run --group dev ruff format --check src tests
	uv run --group dev ty check src tests

fmt:  ## Format code with ruff
	uv run --group dev ruff format src tests
	uv run --group dev ruff check --fix src tests

test:  ## Run unit tests (no pebble binary or juju required)
	uv run --group dev pytest tests/ -m "not integration and not requires_juju" --cov=borescope --cov-report=term-missing

integration:  ## Run integration tests (requires a local pebble binary)
	uv run --group dev pytest tests/ -m integration -v

docs:  ## Build documentation site (docs/src/*.md -> docs/docs/*.html)
	uv run --group docs python docs/src/_build.py
