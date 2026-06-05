"""Policy gates for Evarian's agentic travel execution layer.

The policy engine deliberately decides before any supplier or payment side
effect can happen. It is the backend counterpart to the product rule:
the agent acts only when permission, budget, refund risk, confidence,
supplier reliability, and payment authority are all acceptable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


LOW_RISK_ACTIONS = {"search", "rank", "message", "escalate"}
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
    autonomy_level = int(permissions.get("autonomy_level") or 1)
    cap = _budget_cap_for_action(action_type, permissions)
    autopilot_preapproved = _autopilot_preapproved(action_type, amount, service_type, permissions)

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
    elif any(gate.name in {"supplier_reliability", "supplier_terms", "model_confidence"} for gate in failed):
        decision = "human_review"
        next_step = "Escalate to human travel ops or request more evidence before proceeding."
    else:
        decision = "approval_required"
        next_step = "Ask the traveler to approve or adjust permissions before execution."

    return {
        "decision": decision,
        "action_type": action_type,
        "amount": amount,
        "service_type": service_type,
        "cap": cap,
        "autopilot_preapproved": autopilot_preapproved,
        "gates": [gate.as_dict() for gate in gates],
        "failed_gates": [gate.name for gate in failed],
        "can_execute": decision == "execution_allowed",
        "requires_approval": decision in {"approval_required", "human_review"},
        "next_step": next_step,
    }
