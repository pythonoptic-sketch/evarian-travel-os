# Agentic Orchestration Runtime

This repo uses a deterministic shell with an agentic core.

## Runtime Principle

```text
code owns phase order, approvals, persistence, audit, and deployment
models reason inside bounded phases
tools execute only after policy gates
```

This keeps Evarian reliable while still allowing model-backed planning,
recommendation, verification, and recovery.

## Where Things Belong

| Layer | Purpose |
| --- | --- |
| `AGENTS.md` | repo-wide operating contract |
| `docs/` | durable product truth and architecture |
| `.agents/skills/` | narrow reusable procedures |
| `backend/agentic_travel.py` | manager and specialist agent composition |
| `backend/travel_governance.py` | action parameters, evidence rules, trip value doctrine |
| `backend/travel_policy.py` | deterministic permission and execution gates |
| `backend/travel_app.py` | API surface, persistence, audit events |

Skills are procedures. Agents are judgment and routing. Docs are truth.

## Current Agent Flow

```text
intake
-> context
-> profile / trip intention
-> policy
-> scout swarm
-> pricing / points / maps / supplier verification
-> recommendation with because
-> verification
-> execution staging
-> audit
```

## Side-Effect Rule

No external mutation may happen before policy clearance.

External mutations include:

- booking
- payment
- cancellation
- refund
- rebooking
- supplier messaging
- passenger record modification
- points transfer

Search and comparison can run as preparation. Execution requires the exact
action to pass `POST /api/trip-orders/{order_id}/actions/evaluate`.

## Provider Routing

Use the built-in OpenAI/Gemini adapters first. Keep Hermes-style routing thin:
it may choose roles or provider adapters, but it must not own memory,
approvals, source-of-truth docs, or audit records.

The trust boundary stays in code and policy.
