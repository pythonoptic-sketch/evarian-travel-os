# Evarian Policy Pack

This policy pack converts the business plan into operating rules for the product,
backend, agents, wallet, and future supplier execution layer.

Source context: `docs/EVARIAN_INVESTOR_DECK_EXTRACT.txt`.

## 1. Product Boundary

Evarian is an agentic travel and real-world commerce operating layer.

It is not:

- a generic chatbot
- a search-only itinerary generator
- a crypto-token product first
- a travel agency that owns inventory
- a payment processor

The core product promise is:

```text
one request -> total trip value ranking -> because recommendation -> permissioned execution -> live monitoring -> recovery
```

Total trip value means price, points, comfort, time, taste, location,
logistics, status, flexibility, and recovery risk. The system must optimize the
whole trip, not only the cheapest itinerary.

## 2. Execution Policy

The agent may always prepare:

- parse traveler intent
- infer missing information
- search candidate supply
- rank options
- prepare supplier payloads
- draft messages
- calculate timing
- monitor public status signals
- create audit events

The agent must not execute without policy clearance:

- book
- pay
- cancel
- refund
- rebook
- modify a live supplier order
- move a ride pickup with a spend or cancellation consequence
- store sensitive traveler identity data
- issue, transfer, or redeem EVA token value

Every irreversible action must pass:

1. supported action
2. user permission
3. budget cap
4. refund/cancellation risk
5. model confidence
6. supplier API reliability
7. verified supplier terms
8. payment authority
9. traveler approval unless pre-approved by scope

### 2.1 Action Evidence Parameters

Implemented in `backend/travel_governance.py` and enforced by
`backend/travel_policy.py`.

Recommendations, holds, and side-effect actions must carry operational
evidence, not just model confidence:

- `because_rationale`: every ranked, held, or executable action must explain
  why it fits the traveler.
- `traveler_profile`: recommendations and actions must apply the traveler's
  evolving preference profile.
- `source_comparison`: flights, hotels, villas, cars, and private aviation need
  multiple comparison sources before ranking or execution.
- `direct_supplier_verification`: holds and supplier side effects require direct
  airline, hotel, rental, villa, or provider price and terms verification.
- `maps_location`: hotels, villas, rides, ground transport, and cars require
  location, distance, traffic, access, and logistics checks when relevant.
- `points_rewards`: long-haul, premium, or points-sensitive flights require
  cash-versus-points and card-fit analysis.
- `price_history`: spend-bearing flight, hotel, car, and private aviation
  actions require current price and outlier review.
- `credit_card_fit`: flight, hotel, and car spend must consider points, portal,
  insurance, and card fit.
- `insurance`: car rentals require card and supplier insurance checks.
- `logistics`: ground, villa, and car decisions require arrival, baggage, group,
  and pickup logistics verification.

If these evidence gates are missing, the policy endpoint returns
`research_required` instead of allowing execution.

## 3. Autonomy Levels

### Level 1: Notify

The agent can observe and notify only.

Allowed:

- parse requests
- monitor flight status
- monitor traffic
- send reminders
- suggest next actions

Blocked:

- booking
- payment
- cancellation
- rebooking
- supplier modification

### Level 2: Prepare

The current default.

Allowed:

- search
- rank
- stage booking payloads
- draft supplier messages
- prepare recovery plans
- create reversible no-cost holds when supplier terms are verified

Blocked without user approval:

- spend
- cancellation
- refund
- non-refundable booking
- rebooking

### Level 3: Approve And Execute

The agent can execute after explicit action-level approval.

Required:

- clear amount
- supplier name
- cancellation/refund terms
- payment method
- audit event
- traveler approval

### Level 4: Scoped Autopilot

Configuration is now implemented. Live supplier execution is not yet
implemented.

The agent may execute narrow, low-risk actions inside a pre-approved scope.

Examples:

- auto-book airport ride under a configured cap
- auto-adjust pickup time when a flight delay shifts arrival
- auto-cancel refundable hotel before deadline
- auto-hold replacement flight without payment

Required before enabling:

- reliable supplier APIs
- payment authorization controls
- notification system
- rollback path
- human ops fallback
- production monitoring
- legal review

Current implementation:

- the frontend lets the traveler choose `Ask before charges` or
  `Autobook under cap`
- the backend stores the permission profile
- the policy gate allows scoped airport-ride booking only when all gates pass
- no external booking or payment side effect is connected yet

## 4. Wallet And Payment Policy

MVP payment posture:

- no stored card data in Evarian backend
- no money transmission
- no wallet balances
- no EVA token issuance
- no automatic payments

Allowed MVP payment architecture:

- Stripe checkout for subscriptions or concierge fees
- supplier payment links or user-approved redirects
- future virtual card issuance through a regulated provider

Before wallet launch:

- fintech counsel review
- money transmission analysis
- KYC/AML scope review
- card data handling review
- stored-value and gift-card law review
- chargeback and dispute process
- refund ledger
- settlement ledger

## 5. EVA Token Policy

The deck frames EVA as operational utility, not speculation.

Implementation rule:

```text
No token launch before real platform utility, legal review, and wallet compliance.
```

Allowed now:

- document future loyalty mechanics
- model reward accounting
- track non-transferable loyalty credits in a sandbox

Blocked now:

- public token sale
- speculative claims
- price appreciation claims
- transferable token issuance
- wallet balance claims
- token settlement

## 6. Traveler Data Policy

MVP may store:

- email
- natural-language travel request
- inferred non-sensitive preferences
- trip-order events
- permission settings

MVP must not store yet:

- passport
- date of birth
- government ID
- payment card numbers
- full legal identity documents
- loyalty credentials
- private email/calendar content

Before sensitive data storage:

- user account system
- encryption at rest
- access controls
- deletion/export flow
- privacy policy
- data retention schedule
- incident response process

## 7. Supplier API Policy

Each supplier integration must have:

- sandbox credentials
- typed request/response models
- retry and timeout rules
- circuit breaker
- webhook verification
- failure messaging
- audit logging
- no side effect in tests unless explicitly marked live

Initial supplier order:

1. flight status API
2. maps/traffic API
3. ride estimate API
4. ride booking API
5. hotel search API
6. flight offer API
7. payment/virtual card API

## 8. Human Ops Policy

Escalate when:

- model confidence is below threshold
- supplier API is unreliable
- supplier terms are unavailable
- spend exceeds cap
- request has legal/safety ambiguity
- traveler approval is unclear
- cancellation/rebooking creates irreversible loss

The handoff packet must include:

- traveler request
- trip order
- proposed action
- policy result
- failed gates
- supplier evidence
- previous audit events

## 9. Investor Claim Policy

External claims should say:

- "building"
- "designed to"
- "MVP targets"
- "future wallet/token infrastructure after legal review"

Avoid saying:

- "books autonomously" until live supplier execution works
- "wallet pays" until payment authority exists
- "EVA token works like dollars" until legal review and implementation exist
- "fully agentic" until monitoring and recovery loops are live
