# Contributing to Steeper

Thanks for your interest in improving Steeper! This is the client library that
syncs Telegram bot traffic with a (self-hosted) Steeper backend.

## Development setup

```bash
git clone https://github.com/KarimovMurodilla/steeper.git
cd steeper
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all,dev,test]"
```

## Checks (must pass before opening a PR)

```bash
ruff check .          # lint
ruff format --check . # formatting
mypy steeper          # strict type-checking
pytest -q             # tests (offline — no backend needed)
```

CI runs all of the above on Python 3.10–3.13 plus a per-framework import smoke test.

## Conventions

- Keep backend failures **non-fatal** — the bot must keep working if Steeper is down.
- Never log the auth secret (`token_hash`) or raw bot tokens. Use the existing
  redaction helper in `SteeperClient`.
- Add or update tests for any behavioural change.
- Touching the HTTP contract (endpoint paths, payloads, headers)? Update the
  backend compatibility matrix in `README.md` and add a `CHANGELOG.md` entry.

## Releasing (maintainers)

1. Bump `__version__` in `steeper/__init__.py` (the package version is sourced from it).
2. Move the `Unreleased` section in `CHANGELOG.md` under the new version.
3. Tag and push: `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. The `publish.yml` workflow builds and publishes to PyPI via Trusted Publishing.
