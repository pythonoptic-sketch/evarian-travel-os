"""Credential-gated Amadeus supplier client for Evarian.

This module intentionally uses the Amadeus REST API directly so the deployed
backend does not need an additional SDK dependency. It only performs supplier
searches. Booking, payment, cancellation, and rebooking remain separate
approval-gated actions.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


AMADEUS_TEST_BASE_URL = "https://test.api.amadeus.com"
AMADEUS_PRODUCTION_BASE_URL = "https://api.amadeus.com"


class AmadeusConfigError(RuntimeError):
    """Raised when Amadeus credentials are not configured."""


class AmadeusAPIError(RuntimeError):
    """Raised when Amadeus returns an error or cannot be reached."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _amadeus_environment() -> str:
    raw = (
        os.environ.get("AMADEUS_ENV")
        or os.environ.get("AMADEUS_HOSTNAME")
        or "test"
    ).strip().lower()
    if raw in {"production", "prod", "live"}:
        return "production"
    return "test"


def _amadeus_base_url() -> str:
    configured = os.environ.get("AMADEUS_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    if _amadeus_environment() == "production":
        return AMADEUS_PRODUCTION_BASE_URL
    return AMADEUS_TEST_BASE_URL


def amadeus_runtime_status() -> dict[str, Any]:
    """Return supplier status without exposing credentials."""

    client_id = os.environ.get("AMADEUS_CLIENT_ID", "").strip()
    client_secret = os.environ.get("AMADEUS_CLIENT_SECRET", "").strip()
    return {
        "configured": bool(client_id and client_secret),
        "environment": _amadeus_environment(),
        "base_url": _amadeus_base_url(),
        "client_id_configured": bool(client_id),
        "client_secret_configured": bool(client_secret),
        "supported": ["flight_offers_search"],
        "side_effects_enabled": False,
    }


def _safe_error_detail(payload: dict[str, Any] | str, fallback: str) -> str:
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                title = str(first.get("title") or "").strip()
                detail = str(first.get("detail") or "").strip()
                code = str(first.get("code") or "").strip()
                parts = [part for part in (title, detail, code) if part]
                if parts:
                    return " | ".join(parts)[:500]
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()[:500]
    if isinstance(payload, str) and payload.strip():
        return payload.strip()[:500]
    return fallback


class AmadeusClient:
    """Minimal Amadeus REST client for supplier search."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str | None = None,
        timeout: int = 18,
    ) -> None:
        self.client_id = (client_id or os.environ.get("AMADEUS_CLIENT_ID", "")).strip()
        self.client_secret = (client_secret or os.environ.get("AMADEUS_CLIENT_SECRET", "")).strip()
        self.base_url = (base_url or _amadeus_base_url()).rstrip("/")
        self.timeout = timeout
        self._access_token: str | None = None

    def _ensure_configured(self) -> None:
        if not self.client_id or not self.client_secret:
            raise AmadeusConfigError("amadeus credentials are not configured")

    def _request_json(self, req: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                if not body:
                    return {}
                payload = json.loads(body)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = raw
            detail = _safe_error_detail(payload, "amadeus returned an upstream error")
            raise AmadeusAPIError(exc.code, detail) from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise AmadeusAPIError(502, "amadeus request failed") from exc
        except json.JSONDecodeError as exc:
            raise AmadeusAPIError(502, "amadeus returned invalid json") from exc
        if not isinstance(payload, dict):
            raise AmadeusAPIError(502, "amadeus returned an unexpected response")
        return payload

    def access_token(self) -> str:
        self._ensure_configured()
        if self._access_token:
            return self._access_token
        body = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/v1/security/oauth2/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        payload = self._request_json(req)
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise AmadeusAPIError(502, "amadeus token response did not include an access token")
        self._access_token = token
        return token

    def flight_offers_search(
        self,
        *,
        origin_location_code: str,
        destination_location_code: str,
        departure_date: str,
        adults: int = 1,
        return_date: str | None = None,
        children: int = 0,
        infants: int = 0,
        travel_class: str | None = None,
        non_stop: bool | None = None,
        currency_code: str | None = None,
        max_results: int = 10,
    ) -> dict[str, Any]:
        token = self.access_token()
        params: dict[str, str | int] = {
            "originLocationCode": origin_location_code.upper(),
            "destinationLocationCode": destination_location_code.upper(),
            "departureDate": departure_date,
            "adults": adults,
            "max": max_results,
        }
        if return_date:
            params["returnDate"] = return_date
        if children:
            params["children"] = children
        if infants:
            params["infants"] = infants
        if travel_class:
            params["travelClass"] = travel_class.upper()
        if non_stop is not None:
            params["nonStop"] = str(non_stop).lower()
        if currency_code:
            params["currencyCode"] = currency_code.upper()

        query = urllib.parse.urlencode(params)
        req = urllib.request.Request(
            f"{self.base_url}/v2/shopping/flight-offers?{query}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.amadeus+json",
            },
            method="GET",
        )
        payload = self._request_json(req)
        return self._normalize_flight_offers(payload, params)

    def _normalize_flight_offers(
        self,
        payload: dict[str, Any],
        search_params: dict[str, str | int],
    ) -> dict[str, Any]:
        data = payload.get("data")
        offers = data if isinstance(data, list) else []
        return {
            "source": "amadeus",
            "live": True,
            "side_effects": "none",
            "search": search_params,
            "count": len(offers),
            "offers": [self._compact_offer(offer) for offer in offers[:25] if isinstance(offer, dict)],
            "dictionaries": payload.get("dictionaries", {}),
            "meta": payload.get("meta", {}),
        }

    def _compact_offer(self, offer: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": offer.get("id"),
            "source": offer.get("source"),
            "instant_ticketing_required": offer.get("instantTicketingRequired"),
            "one_way": offer.get("oneWay"),
            "last_ticketing_date": offer.get("lastTicketingDate"),
            "number_of_bookable_seats": offer.get("numberOfBookableSeats"),
            "itineraries": [
                self._compact_itinerary(itinerary)
                for itinerary in offer.get("itineraries", [])
                if isinstance(itinerary, dict)
            ],
            "price": offer.get("price", {}),
            "pricing_options": offer.get("pricingOptions", {}),
            "validating_airline_codes": offer.get("validatingAirlineCodes", []),
            "traveler_pricings": offer.get("travelerPricings", [])[:4],
        }

    def _compact_itinerary(self, itinerary: dict[str, Any]) -> dict[str, Any]:
        return {
            "duration": itinerary.get("duration"),
            "segments": [
                self._compact_segment(segment)
                for segment in itinerary.get("segments", [])
                if isinstance(segment, dict)
            ],
        }

    def _compact_segment(self, segment: dict[str, Any]) -> dict[str, Any]:
        return {
            "departure": segment.get("departure", {}),
            "arrival": segment.get("arrival", {}),
            "carrier_code": segment.get("carrierCode"),
            "number": segment.get("number"),
            "aircraft": segment.get("aircraft", {}),
            "duration": segment.get("duration"),
            "number_of_stops": segment.get("numberOfStops"),
            "blacklisted_in_eu": segment.get("blacklistedInEU"),
        }
