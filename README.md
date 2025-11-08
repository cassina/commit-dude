# Commit Dude 🧠🤖

Commit Dude is a friendly command line helper that turns your staged or working tree changes into polished
[Conventional Commit](https://www.conventionalcommits.org/) messages. It shells out to Git to collect a diff,
asks OpenAI's GPT models (via LangChain) to summarise the changes, and copies the result to your clipboard so
you can paste it straight into `git commit`.

## ✨ Features
- Generates Conventional Commit compliant messages from any git diff.
- Automatically includes `git status --porcelain` output for additional context.
- Copies the suggested message to your clipboard using `pyperclip`.
- Works as a standalone CLI (`commit-dude`) or through `python -m commit_dude`.
- Configurable via environment variables or a `.env` file loaded with `python-dotenv`.

## 📦 Requirements
- Python 3.10 or newer.
- [uv](https://github.com/astral-sh/uv) for dependency management and packaging.
- An OpenAI API key with access to the `gpt-4o-mini` model (set as `OPENAI_API_KEY`).
- macOS, Linux, or Windows with clipboard support for `pyperclip`.

## ⚙️ Installation
```bash
make install  # syncs dependencies using uv
```

This command installs all runtime and development dependencies into uv's virtual environment. If you prefer to
use uv directly, run `uv sync`.

## 🔑 Configuration
Create a `.env` file (or export environment variables) containing your OpenAI credentials:

```bash
OPENAI_API_KEY="sk-..."
```

`commit-dude` uses `python-dotenv` to auto-load `.env` files located at the project root.

## 🚀 Usage
From a Git repository, run the CLI to have Commit Dude generate a suggestion:

```bash
uv run commit-dude
```

The CLI will:
1. Capture the diff of your working tree against `HEAD`.
2. Send the diff (plus `git status --porcelain` output) to the LLM.
3. Print the conversational response and commit message.
4. Copy the final commit message to your clipboard.

You can also pipe a custom diff through standard input:

```bash
git diff main..feature | uv run commit-dude
```

To execute the module explicitly:

```bash
uv run python -m commit_dude
```

If there are no changes, Commit Dude exits with a helpful error message.

## 🧪 Testing & Development
```bash
make test-local  # runs python -m commit_dude through uv
make run         # launches the CLI via uv
```

These commands ensure the CLI starts correctly against your environment. Because the project invokes live LLMs,
integration tests require valid API credentials.

## 📦 Building & Publishing
```bash
make build    # builds an sdist and wheel using uv build
make publish  # publishes artifacts with uv publish (requires credentials)
```

All packaging metadata is defined in `pyproject.toml`. Ensure the `version` field is updated before tagging a
release.

## 🧑‍💻 Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines, commit conventions, and release steps.

## 📄 License
The project currently does not include a license file. Add one if you plan to distribute the package publicly.

