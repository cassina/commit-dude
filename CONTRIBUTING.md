# Contributing to Commit Dude

## Important for Agents and LLM's
- You must use the `Makefile` commands instead of directly using `uv` commands. If the command you need is not available, please create it in the `Makefile`.
- You must run `make install` and make sure all tests pass before submitting a PR.
- You must run `make build` and make sure all tests pass before submitting a PR.
- You must run `make test` and make sure all tests pass before submitting a PR.
- You should never skip tests but fix them following the best practices unless explicitly stated by the user.
- You must run `make format` and make sure all tests pass before submitting a PR (this command refactors files automatically).
- You must use `make run` to get your commit message, this will actually run the Commit Dude CLI so it is a way to also test it out.

## 📋 Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- An OpenAI API key with access to the `gpt-4o-mini` model

## 🛠️ Project Setup
Clone the repository and install dependencies:

```bash
make install
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
1. Create a feature branch based on `development`.
2. Make your changes.
3. Run the relevant checks:
   ```bash
   make test-local  # uv run python -m commit_dude
   make run         # optional, try the CLI interactively
   ```
4. Ensure your commit message follows the [Conventional Commits](https://www.conventionalcommits.org/) format.
5. Submit a pull request.

## 🧪 Testing

### Unit tests
Unit tests are located in the `tests/` directory. Run them with:
```bash
uv run pytest
```

#### Unit Test Guidelines

- Framework: Use pytest for all tests.
- Style: Follow the AAA pattern: Arrange, Act, Assert.

##### Isolation:
- Mock all network, file, and API calls (e.g. ChatOpenAI, .invoke(), os.getenv). 
- Never depend on real .env or external APIs. 
- Coverage: Aim for ≥90% line coverage; all public methods must be tested.

##### Naming:
- Use `test_<method>_<expected_behavior>()` format.
- One logical assertion per test when possible.

##### Assertions:
- Verify return types, side effects, and exceptions (pytest.raises). 
- Use `caplog` for log validation if relevant.

##### Fixtures:
- Define reusable mocks and dummy data in conftest.py. 
- Keep test files self-contained and deterministic.

##### Scope:
- Focus on behavior, not implementation details. 
- Private methods may be tested when they contain logic (e.g. _validate_num_tokens). 
- Currently, the project exposes a CLI integration check through `make test-local`. 
- It exercises the command line entrypoint via `python -m commit_dude`. 
- Because the tool makes live requests to OpenAI, tests require valid API credentials. Please stub network calls when adding automated tests.

## 📝 Coding Guidelines
- Maintain readability and follow existing style in the codebase.
- Keep imports at the top of files; do not wrap them in `try`/`except` blocks.
- Use type hints where practical and leverage Pydantic models for structured responses.
- Document new configuration options in the README.

## 🚀 Releasing
1. Update the version in `pyproject.toml` (the project tracks semantic versions; first release is `0.1.0`).
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


## Recommended Release Verification Flow

### 1. Refresh dependencies in your development environment
Run:
```bash
make install
````

This syncs the **uv** virtual environment with the locked dependencies before building any artifacts.

---

### 2. Run the project’s built-in smoke test

Execute:

```bash
make test-local
```

This launches:

```bash
python -m commit_dude
```

through **uv** to confirm the CLI entry point still starts successfully with your local sources.

This mirrors how the package exposes a module entry point via:

* `commit_dude/__main__.py`
* The `commit_dude.cli:main` callable that backs the console script.

---

### 3. Produce the publishable artifacts

Clean previous builds and generate new ones:

```bash
make clean
make build
```

This produces both the **wheel** and **sdist** under `dist/` using **uv build** and **Hatchling**.

---

### 4. Install the wheel in a fresh environment

Create a clean virtual environment:

```bash
uv run python -m venv .venv-release-test
source .venv-release-test/bin/activate
pip install dist/commit_dude-0.1.2-py3-none-any.whl
```

This verifies that the packaged metadata (dependencies, entry points, and included modules) is **self-contained** and doesn’t rely on your editable checkout.

---

### 5. Exercise the installed CLI exactly as users will

Export your API key:

```bash
export OPENAI_API_KEY=your-key
```

Then run the following to confirm the console script was generated.:

```bash
commit-dude --help
```

Perform a lightweight sanity check by:

* Piping in a fake diff:

  ```bash
  printf 'diff --git ...' | commit-dude
  ```

These confirm that the **Click command**, **OpenAI integration**, and **clipboard copy** pathways all work end-to-end.

---

### 6. Optionally validate the source distribution

Repeat the installation test using the sdist:

```bash
pip install dist/commit_dude-0.1.2.tar.gz
```

This helps catch missing package data that might not appear when testing only the wheel.

---


