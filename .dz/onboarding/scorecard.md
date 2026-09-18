# AI-first scorecard

> Written by the developerz.ai maintainer agent — established by dz-runner setup mode. Each onboarding run rewrites this file whole; the latest run wins, and the same card is stored on the platform.

- Run: `run_bf7d966b4c8746a3aa1f531fe803dad7`
- Computed: 2026-09-18T15:20:13.698Z
- Proof: **unprovable** — `bin/check` did not run green at head on this box. Nothing in the repository’s own code was changed to force it; the excerpt below is the record.
- Score: 10 of 15 items ok

## `policy` — ok

- .dz/maintainer/maintainer.yml established
- .dz/maintainer/reviewer.md established

## `brain` — ok

- CLAUDE.md already present, left alone

## `roster` — ok

- .claude/agents/tesote-adapter.md established
- .claude/agents/webhook-events.md established
- .claude/agents/connector-models.md established
- .claude/agents/schema-migrations.md established

## `skills` — ok

- .claude/skills/verify-change/SKILL.md established
- .claude/skills/docker-environment/SKILL.md established
- .claude/skills/database-migrations/SKILL.md established
- .claude/skills/webhook-testing/SKILL.md established

## `scripts` — ok

- bin/setup established
- bin/dev established
- bin/check established
- ./bin/setup exited 0 at head (1.3s)

## `wiring` — ok

- .mcp.json established

## `commands` — gap

- nothing recorded

## `access` — gap

- landed 0 of 2 asked
- still missing: TESOTE_API_TOKEN, TESOTE_API_URL

## `layout` — gap

- migration to the house layout filed as tasks
- apps/__pycache__: 1 move(s) planned as one task

## `smoke_test` — unprovable

- tests/test_adapter_simple.py in the repository
- ./bin/check at head: not_runnable, exit 127 (0.0s)

## `env_example` — ok

- .env.example established

## `agents_md` — ok

- AGENTS.md established

## `per_workspace_brains` — ok

- single-package repository: 0 workspaces
- CLAUDE.md already present, left alone

## `docs_readme` — ok

- docs/README.md established

## `gate_proved` — unprovable

- ./bin/check at head: not_runnable, exit 127 (0.0s)
