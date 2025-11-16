# Commit Dude 🧠🤖

Commit Dude is a friendly command line helper that turns your staged or working tree changes into polished
[Conventional Commit](https://www.conventionalcommits.org/) messages.

## ✨ Features
- Generates Conventional Commit compliant messages from any git diff.
- Automatically includes `git status --porcelain` output for additional context.
- Copies the suggested message to your clipboard using `pyperclip`.
- Works as a standalone CLI (`commit-dude`) or through `python -m commit_dude`.
- Wraps commit subjects and bodies to a 100-character width so long lines are automatically reflowed.

## 📦 Requirements
- Python 3.10 or newer.
- [uv](https://github.com/astral-sh/uv) for dependency management and packaging.
- An OpenAI API key with access to the `gpt-4o-mini` model (set as `OPENAI_API_KEY`).

## ⚙️ Installation
```bash
uv add commit-dude
```

## 🔑 Configuration
You must have an OpenAI API key in your environment.

```bash
OPENAI_API_KEY="sk-..."
```

## 🚀 Usage

```bash
uv run commit-dude
```

```bash
git diff | uv run commit-dude
```

By default, the CLI runs in **strict** mode and blocks generation if secret patterns are detected in the
diff. Use the `--no-strict` flag to switch to redaction mode, which redacts detected secrets instead
of aborting the run:

```bash
uv run commit-dude --no-strict
```

If you need additional diagnostics (including middleware logs and detection decisions), enable debug
logging:

```bash
uv run commit-dude --debug
```

The output will be similar to:
```bash
🤖 Generating commit message...
Hey there! Here’s a chill commit message for you: 

docs: add AGENTS.md and update CONTRIBUTING.md

- Added AGENTS.md to remind contributors to read the CONTRIBUTING.md file.
- Updated various sections in CONTRIBUTING.md for clarity and accuracy.
- Modified Makefile to sync dependencies with locked versions.
- Cleaned up README.md for better readability and updated usage instructions.

✅ Suggested commit message copied to clipboard. 
```

The CLI will:
1. Capture the diff of your working tree against `HEAD`.
2. Send the diff (plus `git status --porcelain` output) to the LLM.
3. Print the conversational response and commit message.
4. Copy the final commit message to your clipboard.
5. If there are no changes, Commit Dude exits with a helpful error message.


## 🧑‍💻 Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines, commit conventions, and release steps.
