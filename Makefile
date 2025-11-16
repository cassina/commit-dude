# Simple Makefile for Commit Dude

install:
	uv sync --locked

run:
	uv run commit-dude

run-no-strict:
	uv run commit-dude --no-strict

run-no-strict-debug:
	uv run commit-dude --no-strict --debug

test:
	uv run pytest -s --log-cli-level=DEBUG tests/unit/

lint:
	uv run ruff check .

format:
	uv run ruff format .

build:
	uv build

publish:
	uv publish

test-local:
	uv run python -m commit_dude --debug

clean:
	rm -rf dist/ build/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

