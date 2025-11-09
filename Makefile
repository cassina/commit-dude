# Simple Makefile for Commit Dude

install:
	uv sync --locked

run:
        uv run commit-dude

test:
        uv run pytest -s --log-cli-level=DEBUG tests/

build:
        uv build

publish:
	uv publish

test-local:
	uv run python -m commit_dude

clean:
	rm -rf dist/ build/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

