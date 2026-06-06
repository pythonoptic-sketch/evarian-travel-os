---
name: verification-bundle
description: Run after code changes when the task needs validation. Use for test, syntax, endpoint, deployment, and diff-summary checks. Do not use for planning-only or research-only tasks.
---

# Goal

Produce a compact verification report for an Evarian code change.

# Steps

1. Identify the affected layer:
   - frontend: `index.html`, `assets/styles.css`, `assets/site.js`, static assets
   - backend: `backend/travel_app.py`, `backend/agentic_travel.py`, policy, governance, supplier clients
   - docs/instructions: `AGENTS.md`, `docs/`, `.agents/skills/`
2. Run the smallest relevant checks first:
   - frontend JavaScript: `/Applications/Codex.app/Contents/Resources/node --check assets/site.js`
   - backend tests: `/tmp/evarian-smoke-venv/bin/python -m unittest tests.test_travel_app`
   - backend compile: `/tmp/evarian-smoke-venv/bin/python -m py_compile ...`
3. If deploying, verify:
   - `https://drinknile.com`
   - `https://drinknile.com/api/health`
   - `https://drinknile.com/api/trip-orders`
4. Classify failures as:
   - caused by change
   - existing unrelated state
   - missing environment or credential
   - flaky or transient
5. Report:
   - commands run
   - pass/fail
   - deployed or not deployed
   - remaining limitations
