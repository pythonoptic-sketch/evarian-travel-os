"""Supplier execution controller for Evarian.

This module is the only place where supplier side effects should be called.
It assumes policy has already returned ``execution_allowed`` and still keeps a
runtime kill switch so deployments can expose booking endpoints without
accidentally creating supplier orders.
"""

from __future__ import annotations

import os
from typing import Any

from backend.amadeus_client import AmadeusClient


def supplier_side_effects_enabled() -> bool:
    return os.environ.get("EVARIAN_SUPPLIER_SIDE_EFFECTS_ENABLED", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def execution_runtime_status() -> dict[str, Any]:
    return {
        "side_effects_enabled": supplier_side_effects_enabled(),
        "controller": "policy_gated",
        "supported_suppliers": ["amadeus"],
        "supported_side_effects": [
            "amadeus.flight.book",
            "amadeus.hotel.book",
        ],
        "dry_run_supported": True,
    }


def _require_keys(payload: dict[str, Any], keys: list[str]) -> None:
    missing = [key for key in keys if key not in payload or payload[key] in (None, "", [])]
    if missing:
        raise ValueError(f"missing execution payload keys: {', '.join(missing)}")


def _blocked(action_type: str, service_type: str, supplier: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "supplier": supplier,
        "action_type": action_type,
        "service_type": service_type,
        "side_effects": "none",
        "reason": "supplier side effects are disabled",
        "required_env": "EVARIAN_SUPPLIER_SIDE_EFFECTS_ENABLED=true",
    }


def execute_supplier_action(
    *,
    supplier: str,
    action_type: str,
    service_type: str,
    execution_payload: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    supplier = supplier.strip().lower()
    action_type = action_type.strip().lower()
    service_type = service_type.strip().lower()

    if supplier != "amadeus":
        return {
            "status": "unsupported",
            "supplier": supplier,
            "action_type": action_type,
            "service_type": service_type,
            "side_effects": "none",
            "reason": "only amadeus is wired as a supplier execution rail",
        }

    if dry_run:
        return {
            "status": "dry_run",
            "supplier": supplier,
            "action_type": action_type,
            "service_type": service_type,
            "side_effects": "none",
            "would_execute": f"{supplier}.{service_type}.{action_type}",
            "payload_keys": sorted(execution_payload.keys()),
        }

    if not supplier_side_effects_enabled():
        return _blocked(action_type, service_type, supplier)

    client = AmadeusClient()
    if service_type == "flight" and action_type == "book":
        _require_keys(execution_payload, ["flight_offers", "travelers"])
        result = client.create_flight_order(
            flight_offers=execution_payload["flight_offers"],
            travelers=execution_payload["travelers"],
            contacts=execution_payload.get("contacts"),
            remarks=execution_payload.get("remarks"),
            ticketing_agreement=execution_payload.get("ticketing_agreement"),
        )
        return {"status": "executed", **result}

    if service_type == "hotel" and action_type == "book":
        _require_keys(execution_payload, ["booking_data"])
        result = client.create_hotel_booking(booking_data=execution_payload["booking_data"])
        return {"status": "executed", **result}

    return {
        "status": "unsupported",
        "supplier": supplier,
        "action_type": action_type,
        "service_type": service_type,
        "side_effects": "none",
        "reason": "this supplier action is not implemented yet",
    }
