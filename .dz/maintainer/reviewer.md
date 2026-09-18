# Reviewer instructions — tesote/tesote-odoo-api-connector

> Read by the developerz.ai reviewer at EVERY review of this repository, at the reviewed
> commit, as this repo's own layer of the reviewer's prompt — established by dz-runner setup mode.
> It refines the platform rules (a finding is cited or withheld; the bot always discloses)
> and never overrides them. Edit freely; keep it under 12,000 characters — past that it is cut.

## Stack

Odoo 18 addon + uv. The gate is `bin/check` (`uv run ruff check . && uv run ruff format --check . && uv run pytest`): a change that does not pass it is not proven, whatever its description says.

## Review conventions

- Hold every change to the singleton rule: exactly one `tesote.backend` record may exist.
- Accept only tesote.com API **v2** code — reject any v1 endpoint, client, or field mapping.
- Every sync path must persist `next_cursor` and process sync arrays in the order removed → modified → added.
- Every webhook path must verify the HMAC-SHA256 signature and stay idempotent — flag any bypass, even one added "for testing".
- Check money handling: balances come from `balance_cents`/`available_balance_cents` converted to dollars; transaction `amount` is already dollars; ISO timestamps convert to UTC.
- User-facing strings must use `_()`, with `i18n/en_US.po` and `i18n/es.po` updated.
- Files stay under 500 LOC; ask for a split when a file clearly crosses it.
- New tests must run without Odoo (mock `odoo.*` in `tests/conftest.py`, mock HTTP with `responses`) — flag any test that needs a live Odoo or network.
- New models need `security/ir.model.access.csv` lines and, if user-visible, entries in `views/` and `__manifest__.py` `data`.

## Gates that matter

- The gate is `uv run ruff check . && uv run ruff format --check . && uv run pytest` — 219 tests must pass; it matches CI (`.github/workflows/test.yml`) and the pre-commit hooks (ruff + ruff-format).
- "Proven" means that command green on the checkout; it needs no Odoo, no Docker, and no network.
- Schema-affecting model changes need a migration under `migrations/` (registered in `management_commands.py`) — an ORM field alone is not enough when data must transform.
- A Docker-verified change additionally shows `./bin/docker-dev up` + `./bin/docker-dev install` working — note the image build currently fails in `Dockerfile.dev` (psutil pip conflict), so Docker proof is not presently obtainable.

## Never flag

- The base64-obfuscated Sentry DSN in `utils/sentry_config.py` — deliberate (see `docs/SENTRY_USAGE.md`); do not demand its removal or print the decoded value.
- ruff ignores in `pyproject.toml` (E501, N802, N806, N999, UP008, F401 in `__init__.py`, etc.) — deliberate Odoo-compatibility choices, not lint debt.
- black/isort sections in `pyproject.toml` — intentionally disabled; pre-commit uses ruff-format instead (see the commented-out hooks in `.pre-commit-config.yaml`).
- `requirements.txt` holding only `requests` — it is the Odoo-deployment dependency file, not a stale dev manifest; dev deps live in `pyproject.toml`/`uv.lock`.
- Generated/vendored files: `uv.lock`, `i18n/*.pot`/`*.po`, XML data in `views/`/`data/`, SQL in `migrations/`.
- README/CLAUDE.md citing "112 tests" — the suite is now 219; the stale count is not a defect to flag.
- MixedCase method names, hyphenated module names, and explicit `super()` — Odoo conventions this repo adopted on purpose.
