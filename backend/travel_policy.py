"""Policy gates for Evarian's agentic travel execution layer.

The policy engine deliberately decides before any supplier or payment side
effect can happen. It is the backend counterpart to the product rule:
the agent acts only when permission, budget, refund risk, confidence,
supplier reliability, and payment authority are all acceptable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.travel_governance import GOVERNANCE_VERSION, evidence_requirements_for_action


LOW_RISK_ACTIONS = {"search", "rank", "compare", "monitor", "message", "escalate"}
IRREVERSIBLE_ACTIONS = {"book", "pay", "cancel", "refund", "rebook", "modify"}
SUPPORTED_ACTIONS = LOW_RISK_ACTIONS | IRREVERSIBLE_ACTIONS | {"hold"}


@dataclass(frozen=True)
class PolicyGate:
    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def _payment_cap(permissions: dict[str, Any]) -> int:
    payments = permissions.get("payments", {})
    return int(payments.get("use_card_backup_under") or 0)


def _flight_change_cap(permissions: dict[str, Any]) -> int:
    flights = permissions.get("flights", {})
    return int(flights.get("ask_before_fare_difference_above") or 0)


def _hotel_cap(permissions: dict[str, Any]) -> int:
    hotels = permissions.get("hotels", {})
    return int(hotels.get("ask_before_above_per_night") or 0)


def _ride_cap(permissions: dict[str, Any]) -> int:
    rides = permissions.get("airport_rides", {})
    return int(rides.get("auto_book_if_under") or 0)


def _budget_cap_for_action(action_type: str, permissions: dict[str, Any]) -> int:
    if action_type in {"book", "pay"}:
        return max(_payment_cap(permissions), _ride_cap(permissions))
    if action_type in {"rebook", "modify"}:
        return _flight_change_cap(permissions)
    if action_type == "hold":
        return max(_flight_change_cap(permissions), _hotel_cap(permissions), _payment_cap(permissions))
    return 0


def _autopilot_preapproved(action_type: str, amount: int, service_type: str, permissions: dict[str, Any]) -> bool:
    """Return whether prior user settings authorize this irreversible action."""

    autonomy_level = int(permissions.get("autonomy_level") or 1)
    if autonomy_level < 4:
        return False
    if action_type not in {"book", "pay"}:
        return False
    if service_type != "airport_ride":
        return False
    ride_cap = _ride_cap(permissions)
    return ride_cap > 0 and amount > 0 and amount <= ride_cap


def evaluate_action_policy(permissions: dict[str, Any], proposed_action: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a proposed action without executing it."""

    action_type = str(proposed_action.get("action_type", "")).strip().lower()
    service_type = str(proposed_action.get("service_type", "airport_ride")).strip().lower()
    amount = int(proposed_action.get("amount") or 0)
    refundable = bool(proposed_action.get("refundable", True))
    supplier_reliable = bool(proposed_action.get("supplier_reliable", False))
    payment_authorized = bool(proposed_action.get("payment_authorized", False))
    user_approved = bool(proposed_action.get("user_approved", False))
    within_supplier_terms = bool(proposed_action.get("within_supplier_terms", False))
    model_confidence = int(proposed_action.get("model_confidence") or 0)
    because = str(proposed_action.get("because") or "").strip()
    source_count = int(proposed_action.get("source_count") or 0)
    direct_supplier_verified = bool(proposed_action.get("direct_supplier_verified", False))
    maps_verified = bool(proposed_action.get("maps_verified", False))
    points_checked = bool(proposed_action.get("points_checked", False))
    price_history_checked = bool(proposed_action.get("price_history_checked", False))
    credit_card_fit_checked = bool(proposed_action.get("credit_card_fit_checked", False))
    insurance_verified = bool(proposed_action.get("insurance_verified", False))
    logistics_verified = bool(proposed_action.get("logistics_verified", False))
    traveler_profile_applied = bool(proposed_action.get("traveler_profile_applied", False))
    autonomy_level = int(permissions.get("autonomy_level") or 1)
    cap = _budget_cap_for_action(action_type, permissions)
    autopilot_preapproved = _autopilot_preapproved(action_type, amount, service_type, permissions)
    evidence_requirements = evidence_requirements_for_action(action_type, service_type, proposed_action)
    canonical_service_type = str(evidence_requirements["service_type"])

    gates = [
        PolicyGate(
            "supported_action",
            action_type in SUPPORTED_ACTIONS,
            f"{action_type or 'unknown'} action type",
        ),
        PolicyGate(
            "permission_scope",
            autonomy_level >= 2 if action_type in LOW_RISK_ACTIONS | {"hold"} else autonomy_level >= 3,
            f"autonomy level {autonomy_level}",
        ),
        PolicyGate(
            "budget",
            amount <= cap if amount > 0 else True,
            f"amount {amount}, cap {cap}",
        ),
        PolicyGate(
            "refund_risk",
            refundable or action_type not in IRREVERSIBLE_ACTIONS or user_approved,
            "irreversible non-refundable actions require explicit action-level approval",
        ),
        PolicyGate(
            "model_confidence",
            model_confidence >= 85,
            f"confidence {model_confidence}",
        ),
        PolicyGate(
            "supplier_reliability",
            supplier_reliable,
            "supplier API and status must be reliable",
        ),
        PolicyGate(
            "supplier_terms",
            within_supplier_terms,
            "fare, refund, cancellation, and service terms must be verified",
        ),
        PolicyGate(
            "payment_authority",
            payment_authorized if action_type in {"book", "pay", "rebook", "modify"} else True,
            "payment must be authorized for spend-bearing actions",
        ),
        PolicyGate(
            "traveler_approval",
            user_approved or autopilot_preapproved if action_type in IRREVERSIBLE_ACTIONS else True,
            "traveler approval or scoped autopilot preapproval is required before irreversible execution",
        ),
        PolicyGate(
            "traveler_profile",
            traveler_profile_applied or not evidence_requirements["requires_traveler_profile"],
            "recommendations and supplier actions must apply the traveler's preference profile",
        ),
        PolicyGate(
            "because_rationale",
            len(because) >= 12 or not evidence_requirements["requires_because"],
            "ranked, held, and executable actions must explain why this option fits the traveler",
        ),
        PolicyGate(
            "source_comparison",
            source_count >= int(evidence_requirements["minimum_source_count"]),
            f"{source_count} sources checked, {evidence_requirements['minimum_source_count']} required",
        ),
        PolicyGate(
            "direct_supplier_verification",
            direct_supplier_verified or not evidence_requirements["requires_direct_supplier_verification"],
            "price, availability, and terms must be verified directly with the supplier before holds or side effects",
        ),
        PolicyGate(
            "maps_location",
            maps_verified or not evidence_requirements["requires_maps_verification"],
            "location, distance, traffic, access, and pickup/dropoff logistics must be checked when relevant",
        ),
        PolicyGate(
            "points_rewards",
            points_checked or not evidence_requirements["requires_points_check"],
            "long-haul, premium, or points-sensitive flights require cash-versus-points analysis",
        ),
        PolicyGate(
            "price_history",
            price_history_checked or not evidence_requirements["requires_price_history_check"],
            "spend-bearing travel actions require current price and price-history/outlier review",
        ),
        PolicyGate(
            "credit_card_fit",
            credit_card_fit_checked or not evidence_requirements["requires_credit_card_fit_check"],
            "flight, hotel, and car spend must consider points, portal, insurance, and card fit",
        ),
        PolicyGate(
            "insurance",
            insurance_verified or not evidence_requirements["requires_insurance_check"],
            "car rental actions require credit-card and supplier insurance checks",
        ),
        PolicyGate(
            "logistics",
            logistics_verified or not evidence_requirements["requires_logistics_check"],
            "ground, villa, and car decisions must verify arrival, baggage, group, and pickup logistics",
        ),
        PolicyGate(
            "human_review_scope",
            not evidence_requirements["human_review_required"],
            "private aviation and high-complexity supplier actions require human ops review before execution",
        ),
    ]

    failed = [gate for gate in gates if not gate.passed]
    if action_type in LOW_RISK_ACTIONS and not failed:
        decision = "prepare"
        next_step = "Proceed with low-risk preparation; no supplier or payment side effect."
    elif action_type == "hold" and not failed:
        decision = "hold"
        next_step = "Create a reversible hold only if the supplier API supports a no-spend hold."
    elif action_type in IRREVERSIBLE_ACTIONS and not failed:
        decision = "execution_allowed"
        next_step = "Execution is allowed by policy, but the execution controller must still record an audit event."
    elif any(
        gate.name
        in {
            "traveler_profile",
            "because_rationale",
            "source_comparison",
            "direct_supplier_verification",
            "maps_location",
            "points_rewards",
            "price_history",
            "credit_card_fit",
            "insurance",
            "logistics",
        }
        for gate in failed
    ):
        decision = "research_required"
        next_step = "Gather the missing travel evidence before recommending, holding, booking, paying, cancelling, modifying, or rebooking."
    elif any(gate.name in {"supplier_reliability", "supplier_terms", "model_confidence"} for gate in failed):
        decision = "human_review"
        next_step = "Escalate to human travel ops or request more evidence before proceeding."
    elif any(gate.name == "human_review_scope" for gate in failed):
        decision = "human_review"
        next_step = "Escalate this supplier action to human travel ops before execution."
    else:
        decision = "approval_required"
        next_step = "Ask the traveler to approve or adjust permissions before execution."

    return {
        "decision": decision,
        "action_type": action_type,
        "amount": amount,
        "service_type": canonical_service_type,
        "cap": cap,
        "governance_version": GOVERNANCE_VERSION,
        "evidence_requirements": evidence_requirements,
        "autopilot_preapproved": autopilot_preapproved,
        "gates": [gate.as_dict() for gate in gates],
        "failed_gates": [gate.name for gate in failed],
        "can_execute": decision == "execution_allowed",
        "requires_approval": decision in {"approval_required", "human_review", "research_required"},
        "next_step": next_step,
    }
