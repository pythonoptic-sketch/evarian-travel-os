# Evarian Design Operating System

This document captures the practical setup from the design-system guidance and
adapts it to the current Evarian repo.

## Current Decision

Keep the current stack for now:

```txt
Static HTML
CSS
Vanilla JavaScript
FastAPI backend
Caddy on Hetzner
```

Do not migrate to Next.js, Tailwind, shadcn/ui, or Framer Motion until there is
a clear product reason. The current stack is simple, fast, and already deployed.

## Design Intent

Evarian is an agentic travel booking surface. The page must make one idea
obvious:

```txt
one request -> live trip order -> monitored state -> prepared action -> approved execution
```

This is the golden thread for the site. Preserve it in the hero, the live
output, and every supporting section.

Every visual decision should reinforce that idea.

## Visual Standard

References to keep in mind:
- premium fintech clarity
- Apple-level restraint
- calm travel intelligence
- light, airy spacing
- subtle route-like motion

Avoid:
- generic AI gradients
- heavy dashboard clutter
- tourism stock-photo language
- long prompt examples in the hero
- sections that explain features before the user understands the main action

## Working Flow

For meaningful website changes:

1. Define the target visitor.
2. Define the page goal.
3. Write the section hierarchy.
4. Implement the smallest visible improvement first.
5. Check desktop and mobile.
6. Run local syntax/tests.
7. Deploy only after verification.

## Useful Local Checks

```bash
/Applications/Codex.app/Contents/Resources/node --check assets/site.js
/tmp/evarian-smoke-venv/bin/python -m unittest tests.test_travel_app
```

For deployment, verify:

```bash
curl -fsS https://drinknile.com
curl -fsS https://api.drinknile.com/api/health
curl -fsS -X POST https://drinknile.com/api/trip-orders \
  -H 'Content-Type: application/json' \
  -d '{"intent":"Adventure awaits","wallet_cap":75,"risk_mode":"balanced"}'
```
