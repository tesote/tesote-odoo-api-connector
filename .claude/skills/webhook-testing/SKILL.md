---
description: Simulating tesote.com webhook deliveries against the local Odoo endpoint with valid HMAC signatures. Use for webhook tester, HMAC, signature, event simulation, /tesote/webhook.
applies: [python]
---

> House skill — established by dz-runner setup mode from this repo's own evidence, then owned by its maintainers. Correct it in place; setup never overwrites a skill that exists.

1. Bring up the environment: `./bin/docker-dev up` (Odoo at http://localhost:8069) — build failure → stop, see docker-dev-environment step 2.
2. Get the secret from Connectors → tesote.com → Webhook Configuration ("Show Secret") in Odoo.
3. Fire a signed event: `./bin/webhook_tester.py --url http://localhost:8069/tesote/webhook --secret <secret> --event sync.updates_available`.
4. Other events: `--event accounts.created --account-id acc_123`, `--event transactions.created`, `--event transactions.updated`; bulk with `--batch 10`.
5. Verify delivery in Odoo under tesote.webhook.event records — a rejected delivery means signature or idempotency logic changed.
6. For unit-level work with no Odoo running: `uv run pytest tests/test_webhook_processor.py -v` — failure → fix the processing logic; never bypass HMAC verification to make a test pass.
