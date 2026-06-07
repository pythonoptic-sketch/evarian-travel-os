# Amadeus Supplier Integration

Evarian now has a server-side Amadeus supplier rail for flight and hotel
search, flight price confirmation, and policy-gated booking execution.

## Implemented

- `GET /api/suppliers/amadeus/status`
  - Reports whether Amadeus credentials are configured.
  - Does not expose the client secret or token.
- `POST /api/suppliers/amadeus/flight-offers`
  - Calls Amadeus Flight Offers Search.
  - Returns normalized live flight offer data.
  - Performs no booking, payment, cancellation, refund, hold, or rebooking.
- `POST /api/suppliers/amadeus/flight-offers/price`
  - Calls Amadeus Flight Offers Price to confirm availability and final fare.
  - Can include detailed fare rules.
- `POST /api/suppliers/amadeus/hotels/by-city`
  - Lists hotels by IATA city code.
- `POST /api/suppliers/amadeus/hotel-offers`
  - Searches available room offers for selected hotel IDs.
- `POST /api/suppliers/amadeus/hotel-offer`
  - Rechecks one hotel offer by offer ID before booking.
- `POST /api/trip-orders/{order_id}/supplier-actions`
  - Stages a supplier action with policy evaluation and audit logging.
- `POST /api/trip-orders/{order_id}/supplier-actions/{action_id}/execute`
  - Re-evaluates policy and calls the execution controller.
  - Supports `dry_run`.
  - Blocks real supplier side effects unless
    `EVARIAN_SUPPLIER_SIDE_EFFECTS_ENABLED=true`.
- `/api/health`
  - Includes `suppliers.amadeus` readiness metadata.
  - Includes execution-controller readiness metadata.

## Required Server Environment

Set these values in `/etc/evarian/evarian-api.env` on the Hetzner backend:

```bash
AMADEUS_ENV=test
AMADEUS_CLIENT_ID=your_amadeus_api_key
AMADEUS_CLIENT_SECRET=your_amadeus_api_secret
EVARIAN_SUPPLIER_SIDE_EFFECTS_ENABLED=false
```

Use `AMADEUS_ENV=production` only after the Amadeus production app is approved.
`AMADEUS_BASE_URL` can override the default base URL for controlled testing.

Keep `EVARIAN_SUPPLIER_SIDE_EFFECTS_ENABLED=false` until the business has:

1. Production supplier credentials.
2. Flight ticketing authority or a consolidator relationship.
3. Payment authority and chargeback/refund handling.
4. Traveler approval UX for the exact supplier action.
5. Human-ops fallback for failures.

## Flight Offer Request

```json
{
  "origin_location_code": "SFO",
  "destination_location_code": "JFK",
  "departure_date": "2026-07-15",
  "adults": 1,
  "max_results": 10
}
```

Optional fields:

- `return_date`
- `children`
- `infants`
- `travel_class`
- `non_stop`
- `currency_code`

## Execution Boundary

Supplier side effects require:

1. A trip order.
2. A staged supplier action.
3. Policy evaluation through `backend/travel_policy.py`.
4. Traveler approval or an explicit pre-authorized permission scope.
5. Payment authority when spend is involved.
6. The production kill switch:
   `EVARIAN_SUPPLIER_SIDE_EFFECTS_ENABLED=true`.
7. Audit logging before and after execution.

The execution controller currently supports:

- `amadeus.flight.book`
- `amadeus.hotel.book`

Flight order creation is not ticket issuance. Amadeus states that production
use of Flight Create Orders requires the ability to issue tickets, either
through an airline consolidator or direct accreditation.
