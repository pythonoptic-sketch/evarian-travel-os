# Amadeus Supplier Integration

Evarian now has a server-side Amadeus supplier rail for live flight offer
search.

## Implemented

- `GET /api/suppliers/amadeus/status`
  - Reports whether Amadeus credentials are configured.
  - Does not expose the client secret or token.
- `POST /api/suppliers/amadeus/flight-offers`
  - Calls Amadeus Flight Offers Search.
  - Returns normalized live flight offer data.
  - Performs no booking, payment, cancellation, refund, hold, or rebooking.
- `/api/health`
  - Includes `suppliers.amadeus` readiness metadata.

## Required Server Environment

Set these values in `/etc/evarian/evarian-api.env` on the Hetzner backend:

```bash
AMADEUS_ENV=test
AMADEUS_CLIENT_ID=your_amadeus_api_key
AMADEUS_CLIENT_SECRET=your_amadeus_api_secret
```

Use `AMADEUS_ENV=production` only after the Amadeus production app is approved.
`AMADEUS_BASE_URL` can override the default base URL for controlled testing.

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

This integration is search-only. Supplier side effects still require:

1. A trip order.
2. Policy evaluation through
   `POST /api/trip-orders/{order_id}/actions/evaluate`.
3. Traveler approval or an explicit pre-authorized permission scope.
4. Audit logging.

No Amadeus booking endpoint should be added until the execution agent can
record supplier references, payment state, refund terms, cancellation windows,
and recovery obligations inside the Universal Trip Order.
