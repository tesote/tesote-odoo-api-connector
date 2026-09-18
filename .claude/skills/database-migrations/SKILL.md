---
description: Writing and running schema or data migrations for the tesote_connector module. Use for migration, schema change, management commands, module upgrade, uninstall.
applies: [python]
---

> House skill — established by dz-runner setup mode from this repo's own evidence, then owned by its maintainers. Correct it in place; setup never overwrites a skill that exists.

1. Create migrations/YYYYMMDD_NNN_description.py modeled on migrations/20250130_004_add_missing_transaction_fields.py.
2. Register the step in migrations/management_commands.py — unregistered files never execute.
3. Migrations run via migrations/migrate.py::migrate(cr, version), called by Odoo on module upgrade; trigger it with `./bin/docker-dev install` once the Docker env is up (see docker-dev-environment).
4. Verify in the Odoo logs for `Starting tesote_connector migrations` and `Completed tesote_connector migrations` — missing → the step was not registered; go back to step 2.
5. Guard fresh installs: `version` is None on first install, so steps assuming prior schema must skip.
6. Prefer the ORM auto-schema for new model fields; write a migration only for data transforms or custom SQL — fail -> stop, never hand-edit tables.
7. Before any uninstall or destructive change, run `./bin/docker-dev backup` — uninstall drops every tesote_* table (MIGRATIONS.md).
