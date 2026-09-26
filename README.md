# CI failure triage agent

When a GitHub Actions run fails, this agent takes a **truncated** log, classifies the failure, and comments with a cited line — or returns `unknown`.

v1 is a single AWS account in `eu-west-1` (Bedrock Claude Haiku, Lambda, no VPC). Hard ceiling **$20/month**.

The agent is **not deployed yet**. Domain code so far: result contract (`schema.py`), log preprocessor (`preprocess.py`), and four **fixture-backed tools** (`tools.py`) that read `tests/fixtures/runs/<run_id>/` via `FixtureStore`. No live GitHub or Bedrock in tests. `FixtureStore` is a local adapter; a real GitHub client will replace it later.

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for the plan, cost envelope, and week-by-week checklist.

## Local setup

Python **3.12** via [uv](https://docs.astral.sh/uv/) (`.python-version`). Do not use Homebrew 3.14 for this repo.

```bash
uv sync --group dev
uv run python --version    # 3.12.x
```

## Tests

Preprocessor fixtures are plain `.log` files under `tests/fixtures/`. Fake workflow runs (what the tools read) live under `tests/fixtures/runs/<run_id>/` (`run.json`, `job.log`, optional `junit.xml`, `commit_files.json`).

```bash
uv run pytest -q
uv run pytest tests/test_preprocess.py -q
uv run pytest tests/test_preprocess.py::test_flake_log_keeps_timeout_signal -q
```

Push and pull requests to `main` run the same `uv run pytest` on GitHub Actions (`.github/workflows/ci.yml`). No AWS credentials; tests must stay offline.
