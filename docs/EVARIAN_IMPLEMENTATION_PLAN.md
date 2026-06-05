# Evarian Implementation Plan

This is the build sequence from the investor deck and current backend reality.

## Current State

Implemented:

- premium public frontend
- Hetzner FastAPI backend
- waitlist capture
- trip-order storage
- deterministic specialist-agent orchestration
- permission storage
- audit events
- OpenAI key installed on server
- action policy gate endpoint

Blocked:

- OpenAI project billing is not active, so model calls fall back to deterministic
  orchestration.

## Phase 0: Control Plane Foundation

Goal: make every future supplier action pass through a safe internal contract.

Status: in progress.

Build:

- Universal Trip Order schema
- action policy gate
- event/audit ledger
- permission settings
- agent handoff packet
- API health and readiness checks
- tests for forbidden auto-execution

## Phase 1: Airport Timing MVP

Product wedge:

```text
I make sure you get to your flight on time.
```

Build:

1. Flight input
   - flight number
   - departure date
   - airport
   - traveler pickup address

2. Flight status monitor
   - scheduled departure
   - terminal/gate when available
   - delay/cancellation status

3. Traffic monitor
   - route duration
   - buffer calculation
   - departure-time recommendation

4. Airport ride planner
   - estimate options
   - show recommended pickup time
   - ask before booking

5. Monitoring loop
   - recalculate when flight/traffic changes
   - notify user
   - prepare adjusted action

Success metric:

- user receives a useful airport departure recommendation without leaving the
  page.

## Phase 2: Ride Execution

Build only after Phase 1 produces useful recommendations.

Needed:

- Uber or Lyft developer access
- sandbox booking flow
- webhook verification
- cancellation/refund rules
- clear user approval flow
- payment authority

The first paid execution should be narrow:

```text
book airport ride under explicit user approval
```

## Phase 3: User Accounts And Memory

Needed for real personalization.

Build:

- login
- user profile
- preference memory
- saved home/work/airport addresses
- saved permission profile
- trip history
- deletion/export controls

Avoid storing sensitive travel documents until encryption, access control, and
privacy policies are complete.

## Phase 4: Wallet And Payment Authority

Build only after legal review.

Options:

- Stripe checkout for membership/concierge
- virtual card provider for scoped supplier payments
- stored-value wallet only if compliance supports it

Do not implement EVA token before wallet utility and legal review.

## Phase 5: Hotel And Flight APIs

Add after the airport wedge works.

Flight providers:

- Duffel
- Amadeus
- Travelport
- Sabre

Hotel providers:

- Booking.com partner APIs
- Expedia Rapid
- Duffel Stays

Each integration requires sandbox mode, typed models, audit logs, and failure
handling before live use.

## Phase 6: Recovery Agent

Goal:

```text
Your flight changed. I checked the consequences, prepared the fix, and ask only when needed.
```

Build:

- disruption detection
- alternate option search
- fare/refund rule checks
- ride retiming
- hotel late-arrival message
- human ops packet
- notification flow

## Phase 7: EVA Loyalty / Token Infrastructure

Not MVP.

Prerequisites:

- transaction volume
- wallet adoption
- legal review
- accounting policy
- partner settlement logic
- non-speculative utility framing

Start with non-transferable loyalty credits before any token.

