"""Action parameters and governing structure for Evarian travel decisions.

This module turns the product playbook into executable backend constraints.
It is deliberately deterministic: model agents may enrich the order, but they
do not get to redefine what evidence is required before Evarian recommends,
holds, books, pays, cancels, modifies, or recovers a trip.
"""

from __future__ import annotations

from typing import Any


GOVERNANCE_VERSION = "2026-06-05.evarian-action-governance.v1"

RECOMMENDATION_ACTIONS = {"rank", "compare", "hold"}
SIDE_EFFECT_ACTIONS = {"book", "pay", "cancel", "refund", "rebook", "modify"}

SERVICE_ALIASES = {
    "air": "flight",
    "airline": "flight",
    "flights": "flight",
    "hotel": "hotel",
    "hotels": "hotel",
    "stay": "hotel",
    "stays": "hotel",
    "villa": "villa",
    "villas": "villa",
    "airbnb": "villa",
    "vrbo": "villa",
    "ride": "airport_ride",
    "rides": "airport_ride",
    "airport_ride": "airport_ride",
    "airport_transfer": "airport_ride",
    "transfer": "airport_ride",
    "ground": "ground_transport",
    "ground_transport": "ground_transport",
    "car": "car_rental",
    "cars": "car_rental",
    "car_rental": "car_rental",
    "rental_car": "car_rental",
    "private": "private_aviation",
    "private_aviation": "private_aviation",
    "empty_leg": "private_aviation",
}

ACTION_PARAMETERS: dict[str, Any] = {
    "global": {
        "recommendation_requires_because": True,
        "irreversible_actions_require_policy_gate": True,
        "personal_preferences_are_primary": True,
        "approval_before_supplier_side_effects": True,
        "audit_every_decision": True,
        "disallowed_shortcuts": [
            "claiming a live booking without supplier confirmation",
            "using rate codes unless traveler eligibility and supplier terms are verified",
            "spending, cancelling, refunding, rebooking, or modifying without approval or scoped autopilot",
        ],
    },
    "flight": {
        "overview_sources": ["skyscanner", "google_flights"],
        "direct_verification": ["airline_site", "ticketing_provider_site"],
        "nearby_airport_check": True,
        "price_history_required_for_booking": True,
        "long_flight_hours": 3.5,
        "points_programs": ["klm_flying_blue", "british_airways_avios", "qatar_privilege_club"],
        "points_required_when": ["flight_duration_over_3_5h", "premium_cabin_requested", "traveler_mentions_points"],
        "monitoring": ["price_outliers", "same_day_changes", "night_before_changes", "fare_waivers"],
    },
    "hotel": {
        "discovery_sources": ["tablet_hotels", "google_maps"],
        "comparison_sources": ["booking.com", "trip.com", "credit_card_portal", "agoda", "super.com", "expedia", "airbnb", "vrbo"],
        "direct_verification": ["hotel_site", "supplier_site"],
        "maps_verification": ["distance", "neighborhood", "topography", "accessibility", "arrival_logistics"],
        "points_focus": ["hyatt", "chase_ultimate_rewards", "bilt"],
        "image_weighting": "images_and_room_fit_before_reviews",
        "room_size_filter": "surface compact-market options above 300_sq_ft when useful",
        "rate_policy": "company, status, and agent rates may be used only when eligibility and terms are verified",
    },
    "villa": {
        "comparison_sources": ["airbnb", "vrbo", "google_maps", "direct_owner_site"],
        "maps_verification": ["location", "access", "driver_access", "group_logistics"],
        "group_services": ["cleaning", "breakfast", "driver_on_call"],
    },
    "airport_ride": {
        "comparison_sources": ["ride_provider_api", "black_car_provider", "local_transfer_provider"],
        "maps_verification": ["pickup_location", "traffic", "flight_timing", "baggage_fit"],
        "autopilot_scope": "only low-risk ride booking under explicit cap",
    },
    "ground_transport": {
        "comparison_sources": ["ride_provider_api", "black_car_provider", "local_transfer_provider", "google_maps"],
        "maps_verification": ["route", "traffic", "pickup_dropoff", "group_and_baggage_fit"],
    },
    "car_rental": {
        "comparison_sources": ["direct_rental_company", "credit_card_portal", "company_rate_if_eligible"],
        "insurance_required": True,
        "logistics_first": ["counter_location", "airport_pickup_complexity", "vehicle_capacity"],
        "credit_card_checks": ["primary_rental_insurance", "points_value", "status_match"],
    },
    "private_aviation": {
        "comparison_sources": ["empty_leg_provider", "private_membership_provider", "charter_marketplace"],
        "group_threshold": "consider for multi-person event or Europe-hopping itinerary",
        "human_review_required": True,
    },
    "recovery": {
        "monitors": ["flight_status", "weather", "traffic", "fare_waivers", "refund_deadlines", "hotel_late_arrival"],
        "allowed_preparation": ["replacement_options", "refund_argument", "hotel_message", "pickup_retime"],
        "human_fallback": ["supplier_phone_call", "reward_flight_rebooking", "complex_refund_negotiation"],
    },
}

AGENT_EXECUTION_TREE = [
    {
        "agent_id": "manager",
        "role": "strong managing LLM",
        "job": "observe the request, assign specialist agents, enforce policy order, and own the Universal Trip Order",
    },
    {
        "agent_id": "context",
        "role": "intent parser",
        "job": "turn messy chat into route, dates, budget, group, purpose, and missing inputs",
    },
    {
        "agent_id": "profile",
        "role": "personal heuristic agent",
        "job": "apply and update the traveler's evolving preference file",
    },
    {
        "agent_id": "search",
        "role": "supplier swarm",
        "job": "fan out across aggregators, maps, direct supplier sites, and supplier APIs",
    },
    {
        "agent_id": "pricing_watch",
        "role": "price monitor",
        "job": "compare continuously, detect outliers, and keep live price evidence fresh",
    },
    {
        "agent_id": "points_rewards",
        "role": "points and card optimizer",
        "job": "compare cash, points, credit-card portal, transfer bonus, and status logic",
    },
    {
        "agent_id": "maps_location",
        "role": "maps verifier",
        "job": "verify distance, access, traffic, topography, and arrival logistics",
    },
    {
        "agent_id": "supplier_verification",
        "role": "direct supplier verifier",
        "job": "confirm price, availability, refund rules, cancellation windows, and eligibility directly",
    },
    {
        "agent_id": "recommendation",
        "role": "ranking agent",
        "job": "recommend only with because-rationale tied to user preference and evidence",
    },
    {
        "agent_id": "policy",
        "role": "permission engine",
        "job": "block action until approval, budget, confidence, payment, and evidence gates pass",
    },
    {
        "agent_id": "execution",
        "role": "booking executor",
        "job": "stage or execute supplier tools only after policy clearance",
    },
    {
        "agent_id": "recovery",
        "role": "recovery agent",
        "job": "prepare rebooking, refund, cancellation, pickup, hotel, and human fallback work",
    },
]

TRAVELER_PROFILE_SCAFFOLD: dict[str, Any] = {
    "profile_status": "session_inferred_until_user_account",
    "fundamental_truth": "optimize the user's resources for maximum travel value, comfort, timing, and personal fit",
    "learns_from": [
        "requests",
        "recommendations accepted",
        "recommendations rejected",
        "booked products",
        "trip purpose",
        "destination patterns",
        "budget bands",
        "credit card portfolio",
        "loyalty programs",
        "room, seat, location, baggage, and group constraints",
        "post-trip satisfaction",
    ],
    "default_heuristics": [
        "protect arrival certainty before cosmetic savings",
        "direct short economy flights usually do not justify points research",
        "flights over 3.5 hours require cash-versus-points analysis",
        "hotel recommendations must consider location, room fit, images, and cancellation terms",
        "group trips require logistics, space, baggage, drivers, and villa-style options",
        "car rentals require pickup friction and insurance checks before status optimization",
        "every recommendation must explain why it fits this traveler now",
    ],
}


def canonical_service(service_type: str) -> str:
    service = str(service_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    return SERVICE_ALIASES.get(service, service or "travel")


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def infer_services_for_intent(intent: str) -> list[str]:
    lowered = intent.lower()
    services: list[str] = []
    if _contains_any(
        lowered,
        (
            "flight",
            "airline",
            "airport",
            "fly",
            "flying",
            "business class",
            "first class",
            "premium cabin",
            "long haul",
            "long-haul",
            "pnr",
            "ticket",
            "avios",
            "klm",
            "qatar",
        ),
    ):
        services.append("flight")
    if _contains_any(lowered, ("hotel", "stay", "room", "hyatt", "tablet", "booking.com", "trip.com", "agoda", "resort")):
        services.append("hotel")
    if _contains_any(lowered, ("villa", "airbnb", "vrbo", "house", "ibiza", "group", "friends", "wedding", "birthday")):
        services.append("villa")
    if _contains_any(lowered, ("ride", "pickup", "transfer", "driver", "black car", "uber", "airport transfer")):
        services.append("airport_ride")
    if _contains_any(lowered, ("car rental", "rental car", "rent a car", "sixt", "hertz", "avis")):
        services.append("car_rental")
    if _contains_any(lowered, ("private", "empty leg", "charter", "jet")):
        services.append("private_aviation")
    if not services:
        services = ["flight", "hotel", "airport_ride"]
    return _unique(services)


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        value = str(item)
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def infer_trip_traits(intent: str) -> dict[str, bool]:
    lowered = intent.lower()
    return {
        "long_flight_or_premium": _contains_any(
            lowered,
            ("business", "first class", "long haul", "long-haul", "paris", "amsterdam", "tokyo", "qatar", "klm", "avios", "points"),
        ),
        "points_requested": _contains_any(lowered, ("points", "miles", "avios", "redemption", "transfer bonus", "chase", "amex", "bilt", "hyatt")),
        "group_or_event": _contains_any(lowered, ("group", "friends", "wedding", "birthday", "event", "ibiza", "capri", "villa")),
        "hotel_location_sensitive": _contains_any(lowered, ("hotel", "villa", "view", "coast", "central", "downtown", "near", "soho", "room", "sunset")),
        "car_or_ground_sensitive": _contains_any(lowered, ("pickup", "driver", "rental", "car", "baggage", "suitcases", "transfer")),
        "recovery": _contains_any(lowered, ("delay", "cancel", "missed", "refund", "waiver", "rebook", "stranded")),
    }


def source_plan_for_service(service_type: str) -> dict[str, Any]:
    service = canonical_service(service_type)
    parameters = ACTION_PARAMETERS.get(service, {})
    sources: list[str] = []
    for key in ("overview_sources", "discovery_sources", "comparison_sources", "direct_verification"):
        value = parameters.get(key)
        if isinstance(value, list):
            sources.extend(str(item) for item in value)
    return {
        "service_type": service,
        "minimum_comparison_sources": 2 if service in {"flight", "hotel", "villa", "car_rental", "private_aviation"} else 1,
        "sources": _unique(sources),
        "direct_supplier_required": service in {"flight", "hotel", "villa", "car_rental", "private_aviation"},
        "maps_required": service in {"hotel", "villa", "airport_ride", "ground_transport", "car_rental"},
        "points_required_when": parameters.get("points_required_when", []),
        "insurance_required": bool(parameters.get("insurance_required", False)),
    }


def evidence_requirements_for_action(
    action_type: str,
    service_type: str,
    proposed_action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return evidence requirements for the given action and service."""

    action = str(action_type or "").strip().lower()
    service = canonical_service(service_type)
    proposed = proposed_action or {}
    duration = float(proposed.get("duration_hours") or 0)
    premium_or_points = bool(proposed.get("premium_cabin") or proposed.get("points_requested"))
    service_plan = source_plan_for_service(service)
    is_recommendation = action in RECOMMENDATION_ACTIONS
    is_side_effect = action in SIDE_EFFECT_ACTIONS
    needs_decision_evidence = is_recommendation or is_side_effect
    points_required = (
        service == "flight"
        and needs_decision_evidence
        and (duration >= ACTION_PARAMETERS["flight"]["long_flight_hours"] or premium_or_points)
    )
    return {
        "service_type": service,
        "requires_because": needs_decision_evidence,
        "requires_traveler_profile": needs_decision_evidence,
        "minimum_source_count": service_plan["minimum_comparison_sources"] if needs_decision_evidence else 0,
        "requires_direct_supplier_verification": service_plan["direct_supplier_required"] and (action == "hold" or is_side_effect),
        "requires_maps_verification": service_plan["maps_required"] and needs_decision_evidence,
        "requires_points_check": points_required,
        "requires_price_history_check": service in {"flight", "hotel", "car_rental", "private_aviation"} and is_side_effect,
        "requires_credit_card_fit_check": service in {"flight", "hotel", "car_rental"} and is_side_effect,
        "requires_insurance_check": service == "car_rental" and is_side_effect,
        "requires_logistics_check": service in {"airport_ride", "ground_transport", "car_rental", "villa"} and needs_decision_evidence,
        "human_review_required": service == "private_aviation" and is_side_effect,
    }


def build_governance_context(intent: str, wallet_cap: int, risk_mode: str) -> dict[str, Any]:
    services = infer_services_for_intent(intent)
    traits = infer_trip_traits(intent)
    return {
        "version": GOVERNANCE_VERSION,
        "wallet_cap": wallet_cap,
        "risk_mode": risk_mode,
        "services": services,
        "traits": traits,
        "traveler_profile_scaffold": TRAVELER_PROFILE_SCAFFOLD,
        "agent_execution_tree": AGENT_EXECUTION_TREE,
        "action_parameters": {service: ACTION_PARAMETERS.get(service, {}) for service in services},
        "global_action_parameters": ACTION_PARAMETERS["global"],
        "source_plans": {service: source_plan_for_service(service) for service in services},
        "recommendation_contract": {
            "must_explain_because": True,
            "must_show_user_fit": True,
            "must_show_evidence_summary": True,
            "must_preserve_approval_before_booking": True,
        },
        "learning_contract": {
            "profile_file_required": True,
            "profile_file_status": "session_scaffold_until_login_memory_store",
            "update_after_every_trip_order": ["preferences", "constraints", "accepted_tradeoffs", "rejected_tradeoffs"],
        },
    }
