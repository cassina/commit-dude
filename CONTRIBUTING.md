# Contributing to Commit Dude

Thanks for your interest in contributing! This document describes how to set up your environment, make changes,
and publish releases for Commit Dude.

## 📋 Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- An OpenAI API key with access to the `gpt-4o-mini` model

Install uv by following the instructions in the official documentation. Once uv is available, the rest of the
commands below will work out of the box.

## 🛠️ Project Setup
Clone the repository and install dependencies:

```bash
make install  # or `uv sync`
```

This creates (or reuses) uv's isolated virtual environment and installs both runtime and development
requirements.

### Environment variables
The CLI requires an OpenAI API key. Create a `.env` file at the project root or export environment variables in
your shell:

```bash
OPENAI_API_KEY="sk-..."
```

We use `python-dotenv` to load the `.env` file automatically.

## 🚧 Development Workflow
1. Create a feature branch based on `main`.
2. Make your changes.
3. Run the relevant checks:
   ```bash
   make test-local  # uv run python -m commit_dude
   make run         # optional, try the CLI interactively
   ```
4. Ensure your commit message follows the [Conventional Commits](https://www.conventionalcommits.org/) format.
5. Submit a pull request.

## 🧪 Testing
Currently the project exposes a CLI integration check through `make test-local`. It exercises the command line
entrypoint via `python -m commit_dude`. Because the tool makes live requests to OpenAI, tests require valid API
credentials. Please stub network calls when adding automated tests.

## 📝 Coding Guidelines
- Maintain readability and follow existing style in the codebase.
- Keep imports at the top of files; do not wrap them in `try`/`except` blocks.
- Use type hints where practical and leverage Pydantic models for structured responses.
- Document new configuration options in the README.

## 🚀 Releasing
1. Update the version in `pyproject.toml` (the project tracks semantic versions; first release is `1.0.0`).
2. Regenerate the changelog (if present) and ensure documentation reflects the release.
3. Build artifacts:
   ```bash
   make build
   ```
4. Publish to the Python Package Index (requires configured credentials):
   ```bash
   make publish
   ```
5. Create a Git tag matching the version and push it to the repository.

Thanks again for helping improve Commit Dude!
