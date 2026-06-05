# AGENTS.md

## Active Product Context

This repository serves Evarian: an agentic travel booking platform.

The production path is a static frontend plus Python/FastAPI backend on
Hetzner/Caddy. Do not introduce crypto-mining language, mining-wallet flows,
or legacy crypto onboarding into this project.

## Product Design Standard

Evarian should feel like a premium travel operating layer, not a generic AI
chatbot or template SaaS page.

Visual direction:

- Airy, calm, precise, high-trust.
- Travel inspired, but not stock-photo tourism.
- Minimal interface with one strong action surface.
- Light fintech palette with white, soft greys, black ink, muted sky tones,
  rare warm accents, and an editorial dark hero when useful.
- Subtle motion that supports routes, monitoring, and readiness.

Avoid:

- Generic AI gradients.
- Heavy card stacks.
- Marketing fluff.
- Large blocks of prewritten example prompts in the hero.

Golden thread:

1. The traveler makes one request.
2. Evarian turns it into a live trip order.
3. The system monitors trip state.
4. Evarian prepares actions.
5. The traveler approves before booking, payment, cancellation, or rebooking.

## Current Stack

Frontend:

- `index.html`
- `assets/styles.css`
- `assets/site.js`
- static assets in `assets/`

Backend:

- `backend/travel_app.py`
- `backend/agentic_travel.py`
- `backend/travel_policy.py`

Deployment:

- Hetzner server behind Caddy
- Caddy config in `deploy/caddy/Caddyfile`
- Public site: `https://drinknile.com`
- API: `https://drinknile.com/api/*` and `https://api.drinknile.com/api/*`

## Implementation Rules

- Keep the hero centered on the agentic command input.
- Keep placeholder text minimal. The default hero placeholder should stay
  concise, for example `Adventure awaits`.
- Maintain visible approval and permission language.
- Mobile should be first-class.
- Prefer fewer stronger sections over explanatory sprawl.
- Do not expose API keys in frontend JavaScript.
- Model enrichment must never bypass deterministic policy gates.

## Verification

```bash
/Applications/Codex.app/Contents/Resources/node --check assets/site.js
python -m unittest tests.test_travel_app
```
