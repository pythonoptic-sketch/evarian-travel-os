# Evarian Developer Handoff

This repository contains the current Evarian travel platform prototype:

- static frontend served from the repository root
- FastAPI backend in `backend/`
- SQLite runtime state
- Caddy reverse proxy and systemd service for Hetzner deployment
- deterministic agent orchestration, governance, permission gates, and audit events
- credential-gated Amadeus flight-offer search rail

Legacy BTX mining files are intentionally not part of this GitHub mirror. The active product is Evarian.

## Live Runtime

- Website: `https://drinknile.com`
- API health: `https://drinknile.com/api/health`
- API host alias: `https://api.drinknile.com/api/health`

## Product Contract

The current golden thread is:

```txt
traveler request
-> Universal Trip Order draft
-> specialist agents compare total trip value
-> permission and policy gates evaluate action safety
-> traveler approval is required before irreversible supplier actions
-> audit events are written
```

The backend must not book, pay, cancel, refund, rebook, or modify anything unless the policy engine allows it and the future supplier execution controller records the action.

## Repository Map

```txt
index.html                         Frontend command surface and sections
assets/styles.css                  Visual system, layout, responsive behavior
assets/site.js                     Browser API wiring and UI interaction
backend/travel_app.py              FastAPI app and API endpoints
backend/agentic_travel.py          Managing agent and specialist-agent orchestration
backend/travel_governance.py       Trip intentions, total trip value score, evidence rules
backend/travel_policy.py           Deterministic policy gates for proposed actions
backend/amadeus_client.py          Amadeus REST client for flight-offer search
backend/.env.example               Safe local env template
deploy/backend.env.example         Server env template
deploy/caddy/Caddyfile             drinknile.com and api.drinknile.com routing
deploy/systemd/evarian-api.service Backend service definition
docs/                              Product, policy, supplier, and architecture docs
tests/test_travel_app.py           API and policy smoke tests
```

## Local Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example .env.local
uvicorn backend.travel_app:app --host 127.0.0.1 --port 8010
```

Open:

```txt
http://127.0.0.1:8010/api/health
```

For the static page during local development, either open `index.html` directly or serve the repo root with a simple static server. The deployed path uses Caddy to serve the static files and reverse proxy `/api/*` to FastAPI.

## Runtime Environment

Required for persistent production state:

```bash
DATA_DIR=/var/lib/evarian
EVARIAN_DATABASE_PATH=/var/lib/evarian/evarian.sqlite3
```

Optional model-backed enrichment:

```bash
EVARIAN_MODEL_AGENTS_ENABLED=true
EVARIAN_MODEL_PROVIDER=openai
OPENAI_MODEL=gpt-5.4-mini
OPENAI_API_KEY=<server-side secret>
```

Optional Gemini fallback:

```bash
EVARIAN_MODEL_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
GEMINI_API_KEY=<server-side secret>
```

Amadeus supplier search:

```bash
AMADEUS_ENV=test
AMADEUS_CLIENT_ID=<server-side secret>
AMADEUS_CLIENT_SECRET=<server-side secret>
```

Never expose any model, Amadeus, or Stripe key in frontend JavaScript.

## Implemented API

```txt
GET  /api/health
GET  /api/demo-trip
POST /api/waitlist
GET  /api/trip-orders
POST /api/trip-orders
GET  /api/trip-orders/{order_id}
PUT  /api/trip-orders/{order_id}/permissions
GET  /api/trip-orders/{order_id}/events
POST /api/trip-orders/{order_id}/events
POST /api/trip-orders/{order_id}/actions/evaluate
GET  /api/suppliers/amadeus/status
POST /api/suppliers/amadeus/flight-offers
```

Example trip order:

```bash
curl -sS https://drinknile.com/api/trip-orders \
  -H 'Content-Type: application/json' \
  -d '{
    "intent": "Find me a long-haul business class trip to Paris using points if possible, with a quiet hotel near the center.",
    "wallet_cap": 2200,
    "risk_mode": "balanced"
  }'
```

Example action evaluation:

```bash
curl -sS https://drinknile.com/api/trip-orders/{order_id}/actions/evaluate \
  -H 'Content-Type: application/json' \
  -d '{
    "action_type": "book",
    "service_type": "airport_ride",
    "amount": 70,
    "refundable": true,
    "supplier_reliable": true,
    "within_supplier_terms": true,
    "model_confidence": 91,
    "payment_authorized": true,
    "user_approved": true,
    "because": "This protects airport timing and stays inside the approved ride cap.",
    "source_count": 3,
    "direct_supplier_verified": true,
    "maps_verified": true,
    "price_history_checked": true,
    "logistics_verified": true,
    "traveler_profile_applied": true
  }'
```

## What Is Real Now

- The frontend command surface calls the backend.
- Waitlist submissions persist in SQLite.
- Trip orders persist in SQLite.
- Agent orchestration returns structured trip state, specialist-agent outputs, permissions, products, and audit events.
- Policy evaluation blocks unsafe or unsupported actions.
- Amadeus flight-offer search is wired but disabled until credentials are installed on the server.
- Production routing through Caddy and systemd is represented in `deploy/`.

## What Still Needs Integration

- Authenticated user accounts and session management.
- Traveler profile and preference memory per user.
- Real payment authority through Stripe, Adyen, Airwallex, or virtual cards.
- Flight booking, ticketing, cancellation, rebooking, refund, and servicing rails.
- Hotel booking and cancellation rails.
- Ride booking and live pickup monitoring rails.
- Flight status, weather, traffic, and disruption monitoring.
- Human ops escalation queue and operator dashboard.
- Production-grade audit log immutability and PII handling.
- Amadeus production credential approval and supplier compliance review.

## Suggested Next Build Order

1. Add authentication and user-owned trip orders.
2. Add traveler profile memory and scoped permission settings.
3. Install server-side model key and run production evals against deterministic fixtures.
4. Install Amadeus test credentials and verify live flight-offer search.
5. Add Stripe customer/payment-method vaulting without allowing autonomous charges yet.
6. Build the execution controller as a separate module that can only run after `travel_policy.py` returns `execution_allowed`.
7. Add monitoring providers and recovery events.
8. Add a human-ops fallback queue before any irreversible supplier action goes live.

## Verification Commands

```bash
/Applications/Codex.app/Contents/Resources/node --check assets/site.js
python -m py_compile backend/travel_app.py backend/agentic_travel.py backend/travel_governance.py backend/travel_policy.py backend/amadeus_client.py
python -m unittest tests.test_travel_app
```

## Deployment Notes

The current production host is Hetzner behind Caddy. The backend service runs as:

```txt
evarian-api.service
```

The service expects private runtime variables at:

```txt
/etc/evarian/evarian-api.env
```

The public repo intentionally contains examples only.
