# Evarian Travel OS

Evarian is an agentic travel booking control surface. The current stack is a
static frontend plus a Python/FastAPI backend deployed on Hetzner behind Caddy.

The product goal is not a generic chatbot. The core flow is:

```txt
one travel request -> live trip order -> monitored state -> prepared action -> user-approved execution
```

## Public Runtime

- Site: https://drinknile.com
- API health: https://api.drinknile.com/api/health
- API trip orders: `POST https://api.drinknile.com/api/trip-orders`

## Structure

```txt
index.html                 Static homepage and command surface
assets/styles.css          Premium Evarian visual system
assets/site.js             Frontend API wiring
backend/travel_app.py      FastAPI app
backend/agentic_travel.py  Managing agent and specialist-agent orchestration
backend/travel_policy.py   Action authorization policy gate
deploy/caddy/Caddyfile     Hetzner/Caddy routing
deploy/systemd/            API service definition
docs/                      Product, policy, and agent architecture
docs/DEVELOPER_HANDOFF.md  Integration guide for outside developers
tests/test_travel_app.py   Backend tests
```

For a complete integration brief, start with
[`docs/DEVELOPER_HANDOFF.md`](docs/DEVELOPER_HANDOFF.md).

## Local Backend

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.travel_app:app --host 127.0.0.1 --port 8010
```

Then visit:

```txt
http://127.0.0.1:8010/api/health
```

## Model Providers

The backend is provider-neutral. Deterministic agent logic always runs first;
model enrichment is optional and never bypasses permission gates.

Environment variables:

```bash
EVARIAN_MODEL_AGENTS_ENABLED=true
EVARIAN_MODEL_PROVIDER=openai
OPENAI_MODEL=gpt-5.4-mini
OPENAI_API_KEY=
```

See `backend/.env.example` and `deploy/backend.env.example` for safe templates.

The website must never receive model API keys in frontend JavaScript.

## Tests

```bash
python -m unittest tests.test_travel_app
```

## Current Limitations

- Supplier APIs for flights, hotels, rides, payments, cancellations, and
  rebooking are not connected yet.
- The backend stages and evaluates actions; it does not actually charge,
  book, cancel, refund, or rebook without future supplier integrations.
- Jules API keys are for Jules coding sessions, not Gemini model inference.
