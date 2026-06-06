# AGENTS.md

## Active Product Context

This repo currently serves Evarian: an agentic travel booking platform.
The current production path is a static frontend plus Python/FastAPI backend on
Hetzner/Caddy, not a Next.js app.

Legacy BTX mining files and docs still exist in this repository. Do not bring
BTX miner copy, stratum UI, wallet language, or mining flows back into the
homepage unless the user explicitly asks for BTX work.

## Product Design Standard

Evarian should feel like a premium travel operating layer, not a generic AI
chatbot or template SaaS page.

Visual direction:
- Airy, calm, precise, high-trust.
- Travel inspired, but not stock-photo tourism.
- Minimal interface with one strong action surface.
- Light fintech palette: white, soft greys, black ink, muted sky tones, rare
  warm accent.
- Subtle motion that supports the feeling of routes, monitoring, and readiness.

Avoid:
- Generic AI gradients.
- Heavy card stacks.
- Marketing fluff.
- Decorative visuals that do not explain travel, monitoring, approval, or
  execution.
- Large blocks of prewritten example prompts in the hero.

Golden thread:
1. The traveler makes one request.
2. Evarian identifies the trip intention and applies the traveler profile.
3. Scout agents compare total trip value: price, points, comfort, timing,
   taste, location, logistics, status, flexibility, and recovery risk.
4. Evarian recommends with a clear `because`.
5. The system monitors trip state and prepares actions.
6. The traveler approves before booking, payment, cancellation, or rebooking.

This golden thread must be visible in the page structure, copy, and interaction.

## Current Stack

Frontend:
- `index.html`
- `assets/styles.css`
- `assets/site.js`
- static assets in `assets/`

Backend:
- `backend/travel_app.py`
- FastAPI served by `evarian-api.service`
- SQLite data at runtime on the server

Deployment:
- Hetzner server behind Caddy
- Caddy config in `deploy/caddy/Caddyfile`
- Public site: `https://drinknile.com`
- API: `https://drinknile.com/api/*` and `https://api.drinknile.com/api/*`

Do not add a framework or major dependency unless the user explicitly asks for
a stack migration.

## Implementation Rules

- Start by clarifying the page hierarchy in the code, not by adding decoration.
- Keep the hero centered on the agentic command input.
- Keep placeholder text minimal. The default hero placeholder should remain
  concise, e.g. `Adventure awaits`.
- Make the live trip order feel like the real product output.
- Maintain visible approval and permission language.
- Mobile should be designed first-class, not compressed desktop.
- Use strong spacing, clean typography, and restrained motion.
- Prefer fewer stronger sections over more explanatory sections.
- Use existing files and patterns before adding new files.
- Keep copy concrete and product-native.

## Quality Bar

Before marking frontend work done:
- Run JavaScript syntax checks.
- Validate required HTML IDs used by `assets/site.js`.
- Verify key assets referenced by `index.html` exist.
- If backend routes changed, run the travel backend tests.
- If deploying, verify HTTPS page load, moving asset, `/api/health`, and
  `/api/trip-orders`.

Recommended local checks:

```bash
/Applications/Codex.app/Contents/Resources/node --check assets/site.js
/tmp/evarian-smoke-venv/bin/python -m unittest tests.test_travel_app
```

## Final Response Standard

Summarize:
- What changed.
- Which files changed.
- What was verified.
- Any remaining deployment, DNS, API-key, or product limitations.
