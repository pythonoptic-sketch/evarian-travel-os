# Evarian Agentic Travel Agent System

This extracts the implementation requirements from the older
`agentic-travel-os.html` prototype and converts them into the active backend
contract.

## Product Goal

Evarian should not behave like an itinerary generator. It should behave like a
travel operating layer:

```txt
traveler intent -> trip intention -> traveler DNA -> scout teams -> total trip value ranking -> because recommendation -> approval-gated execution -> monitoring and recovery
```

## What Must Be Implemented

1. Intent capture
   - Accept natural-language travel requests.
   - Detect whether the traveler wants a new trip, a change, recovery, or
     general assistance.
   - Extract route, dates, priorities, budget, urgency, and missing details.

2. Traveler preference memory
   - Infer or store schedule, hotel, seat, loyalty, accessibility, and price
     preferences.
   - Keep defaults conservative until the user has explicit profile memory.

3. Search and inventory
   - Search flights, hotels, airport transfers, rail, dining, activities, and
     supplier terms.
   - Early prototype uses deterministic candidate scopes.
   - Production requires supplier APIs.

4. Total trip value ranking
   - Optimize across price, points, comfort, time, taste, location, logistics,
     status, flexibility, and recovery risk.
   - Detect trip intention before ranking.
   - Use scout teams for flight, hotel, logistics, value arbitrage, and
     recovery.

5. Policy and wallet guardrails
   - Every request must have wallet caps and approval rules.
   - No irreversible purchase, cancellation, or rebooking should execute
     without approval.

6. Recommendation and ranking
   - Rank options by traveler priority: arrival certainty, price, comfort,
     policy safety, speed, and serviceability.
   - Every recommendation must explain why it fits the traveler using
     `because`.

7. Verification
   - Check missing inputs, supplier terms, refundability, payment boundaries,
     and whether a human fallback is required.

8. Execution staging
   - Prepare holds, messages, booking payloads, cancellation requests, and
     payment actions.
   - Keep execution staged until approval.

9. Recovery
   - Monitor flight status, traffic, hotel check-in, fare waivers, weather, and
     downstream risks.
   - Prepare replacement actions when disruptions happen.

10. Human escalation
   - Package the full order context for a human operator when automation is
     unsafe, unsupported, or low-confidence.

## Agent Composition

The current backend composes these agents:

- `manager`: routes tasks and owns final trip order assembly.
- `context`: extracts intent, route, priority, and missing information.
- `profile`: applies traveler preference memory or conservative defaults.
- `policy`: attaches wallet and approval guardrails.
- `search`: prepares supplier search scope.
- `recommendation`: ranks the candidate set.
- `verification`: checks safety, missing inputs, and serviceability.
- `execution`: stages actions without spending or modifying supplier state.
- `recovery`: selected only for disruption or servicing requests.
- `human_ops`: selected for high spend, low verification confidence, or unsafe
  automation.

## Current Backend Contract

`POST /api/trip-orders` returns:

- `manager`
- `agent_network`
- `delegation_plan`
- `agent_outputs`
- `products`
- `permissions`
- `autopilot`
- `control_center`
- `audit_events`
- `monitoring`
- `allowed_actions`
- `governance`
- `source_plans`
- `action_parameters`
- `trip_intention`
- `total_trip_value_score`
- `scout_teams`
- `travel_dna`

The current frontend intentionally keeps these internals hidden. The backend
still stores and returns them for future dashboards, internal operator tools,
and product debugging.

`GET /api/suppliers/amadeus/status` returns Amadeus supplier readiness without
exposing credentials.

`POST /api/suppliers/amadeus/flight-offers` performs live Amadeus Flight Offers
Search once `AMADEUS_CLIENT_ID` and `AMADEUS_CLIENT_SECRET` are configured on
the backend. It is search-only and has no supplier side effects.

`POST /api/trip-orders/{order_id}/actions/evaluate` evaluates a proposed
supplier/payment action against the policy gate. It returns:

- `decision`
- `can_execute`
- `requires_approval`
- `gates`
- `failed_gates`
- `next_step`

This endpoint is the first concrete execution-safety primitive. Supplier and
payment tools must call it before performing side effects.

The action policy is now backed by `backend/travel_governance.py`, which embeds
the travel operating heuristics as deterministic rules:

- every recommendation needs a `because`
- flights start with overview sources and move to direct supplier verification
- long-haul, premium, and points-sensitive flights need rewards analysis
- hotels and villas need maps/location/logistics evidence
- car rentals need pickup friction and insurance evidence
- private aviation actions require human review
- every spend-bearing action needs payment, supplier terms, and audit control

## Current Limitation

The orchestration layer is deterministic and provider-neutral by default. The
server has gated OpenAI/Gemini adapters, but live model calls require active
provider keys and billing. The first live supplier rail is Amadeus Flight Offers
Search, but it remains credential-gated and search-only. That is deliberate
until:

1. Model API billing is active for the deployed backend key.
2. Supplier API credentials are configured in the server environment.
3. The execution agent has real approval, audit, and rollback controls.
4. Booking, payment, cancellation, and recovery state are fully represented in
   the Universal Trip Order.

Related policy docs:

- `docs/EVARIAN_POLICY_PACK.md`
- `docs/EVARIAN_IMPLEMENTATION_PLAN.md`
- `docs/EVARIAN_HERMES_ORCHESTRATION.md`
- `docs/AMADEUS_INTEGRATION.md`
- `docs/EVARIAN_TOTAL_TRIP_VALUE_DOCTRINE.md`
- `docs/AGENTIC_ORCHESTRATION_RUNTIME.md`

## OpenAI Agents SDK Upgrade Path

When API-key use is approved:

1. Keep the deterministic agent contracts as guardrails.
2. Add model-backed reasoning inside individual agents, not in the UI.
3. Keep `policy`, `verification`, and `execution` deterministic where possible.
4. Add evals for:
   - missing information detection
   - forbidden auto-execution
   - approval boundary compliance
   - recovery routing
   - human escalation
5. Add supplier tools one by one and require traceable outputs before execution.
