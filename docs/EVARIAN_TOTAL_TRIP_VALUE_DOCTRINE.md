# Evarian Total Trip Value Doctrine

Evarian is not an itinerary generator. It is a permissioned travel operator.

The customer promise:

```text
Tell Evarian what you want. It finds the best way to make it happen, explains
why, prepares the action, asks before irreversible execution, and keeps
watching until the trip is complete.
```

## Golden Thread

```text
one request
-> trip intention
-> traveler DNA
-> scout teams
-> total trip value ranking
-> because recommendation
-> approval-gated execution
-> monitoring and recovery
-> preference learning
```

## Total Trip Value

Evarian does not optimize by price alone.

Total trip value means:

- cash price
- points value
- comfort
- time
- taste
- location
- logistics
- status and card benefits
- flexibility
- recovery risk

This contract is embedded in `backend/travel_governance.py` as
`TOTAL_TRIP_VALUE_SCORE` and returned on every trip order.

## Trip Intention

The first product question is not only “where are you going?” It is:

```text
What are we trying to make happen?
```

Trip intention changes the optimization strategy:

- business: schedule certainty, low friction, arrival buffer
- long-haul luxury: points, cabin comfort, sleep, transfer bonuses
- group social: luggage, drivers, villas, shared space
- couple escape: beauty, privacy, calm, views
- family: safety, space, predictable logistics
- cultural: walkability, local texture, visual character
- recovery: money preservation, arrival recovery, supplier leverage

## Scout Teams

The managing agent does not browse randomly. It routes to structured teams:

- flight optimization
- hotel optimization
- logistics
- value arbitrage
- recovery

Each scout must return evidence, not vibes. Every ranked option must include a
`because` rationale tied to traveler fit and verifiable facts.

## Authority

Evarian may prepare without approval. It must not book, pay, cancel, refund,
rebook, or modify supplier state unless the policy gate allows it.

Authority levels:

1. suggest
2. prepare checkout
3. book after approval
4. auto-book under explicit limits
5. autonomous recovery inside permission

The live implementation currently supports preparation, policy evaluation,
permission storage, audit events, Amadeus flight search readiness, and scoped
airport-ride autopilot evaluation. Actual supplier execution is still gated.
