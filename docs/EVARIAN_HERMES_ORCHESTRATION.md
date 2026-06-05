# Evarian Hermes-Style Agent Orchestration

Local repo evidence: there is no separate Hermes runtime in this workspace.
The current implementation uses a Codex-native Hermes-style router through
`backend/agentic_travel.py`.

## Orchestration Principle

Hermes is the manager/router role:

```text
request -> classify -> assign specialist agents -> verify -> stage action -> policy gate -> audit
```

## Current Specialist Agents

- `manager`: owns route and task delegation
- `context`: parses messy traveler intent
- `profile`: applies preference memory or conservative defaults
- `policy`: attaches spend and approval guardrails
- `search`: prepares supplier search scope
- `recommendation`: ranks tradeoffs
- `verification`: checks safety and serviceability
- `execution`: stages actions without side effects
- `recovery`: selected for disruption requests
- `human_ops`: selected for high-risk or low-confidence cases

## Required Future Tools

The Hermes manager should eventually own tool routing for:

- `flight_status.lookup`
- `traffic.estimate_route`
- `ride.estimate`
- `ride.book`
- `hotel.search`
- `hotel.message`
- `flight.search`
- `flight.hold`
- `payment.authorize`
- `notification.send`
- `human_ops.create_case`

## Non-Negotiable Routing Rule

No tool that creates an external side effect may run before the policy gate
returns `execution_allowed`.

External side effects include:

- charging a card
- creating a booking
- cancelling a booking
- rebooking
- changing a passenger record
- messaging a supplier
- issuing wallet or token value

## Current Backend Mapping

- Hermes manager: `run_agentic_travel_agents`
- Policy gate: `evaluate_action_policy`
- Trip order API: `POST /api/trip-orders`
- Permission API: `PUT /api/trip-orders/{order_id}/permissions`
- Action evaluation API: `POST /api/trip-orders/{order_id}/actions/evaluate`
- Audit events: `trip_events`

