# Simple Makefile for Commit Dude

install:
	uv sync

run:
	uv run commit-dude

build:
	uv build

publish:
	uv publish

test-local:
	uv run python -m commit_dude

clean:
	rm -rf dist/ build/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

