---
description: Bringing up the local Odoo + Postgres dev environment and running module commands in Docker. Use for docker, dev environment, up, install, logs, shell, reset.
applies: [python]
---

> House skill — established by dz-runner setup mode from this repo's own evidence, then owned by its maintainers. Correct it in place; setup never overwrites a skill that exists.

1. Run `./bin/docker-dev up` — starts db (postgres:15-alpine), odoo (built from Dockerfile.dev) and pgadmin; Odoo at http://localhost:8069, admin/admin, database tesote_dev.
2. Image build fails today on `pip install` of psutil inside odoo:18.0 → stop and report the Dockerfile.dev failure; do not patch around it by editing compose or skipping services.
3. Once up, install or upgrade the module: `./bin/docker-dev install`.
4. Run Odoo-native module tests: `./bin/docker-dev test` (odoo --test-enable -i tesote_connector -d tesote_dev).
5. Other commands: `./bin/docker-dev logs odoo`, `restart`, `shell` (Odoo Python shell), `bash`, `psql`, `status`, `backup`, `restore <file>`, `down`.
6. Hot reload is on (--dev=all): Python edits apply on save; XML/manifest changes need `install`, new Python files need `restart`.
7. `./bin/docker-dev reset` deletes the database volume → confirm intent before running; it destroys all synced data.
