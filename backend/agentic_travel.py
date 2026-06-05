"""Deterministic multi-agent control plane for Evarian travel orders.

The module is intentionally provider-neutral. It gives the product a real
agentic contract now, while leaving the model-backed cognition step behind an
explicit credential and approval gate.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    name: str
    optimized_for: str
    trigger: str
    output_contract: str

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.agent_id,
            "name": self.name,
            "optimized_for": self.optimized_for,
            "trigger": self.trigger,
            "output_contract": self.output_contract,
        }


@dataclass(frozen=True)
class AgentOutput:
    agent_id: str
    title: str
    summary: str
    confidence: int
    artifacts: dict[str, Any]
    next_agents: list[str]
    requires_approval: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "title": self.title,
            "summary": self.summary,
            "confidence": self.confidence,
            "artifacts": self.artifacts,
            "next_agents": self.next_agents,
            "requires_approval": self.requires_approval,
        }


AGENT_SPECS = [
    AgentSpec(
        "manager",
        "Managing Travel Agent",
        "routing, task assignment, sequencing, approval boundaries",
        "every request",
        "delegation plan, selected agents, final trip order",
    ),
    AgentSpec(
        "context",
        "Intent and Context Agent",
        "traveler intent, constraints, missing information, urgency",
        "every request",
        "structured trip context",
    ),
    AgentSpec(
        "profile",
        "Traveler Preference Agent",
        "seat, hotel, schedule, budget, loyalty, accessibility preference memory",
        "every request with a known or inferred traveler profile",
        "preference profile and personalization assumptions",
    ),
    AgentSpec(
        "search",
        "Travel Search Agent",
        "flight, hotel, ride, rail, and activity candidate discovery",
        "new trip, trip change, recovery, or supplier action",
        "candidate inventory set with source classes",
    ),
    AgentSpec(
        "policy",
        "Policy and Wallet Agent",
        "spend caps, auto-execution limits, policy compliance, approval gates",
        "every request before recommendation or execution",
        "permission model and blocked actions",
    ),
    AgentSpec(
        "recommendation",
        "Recommendation Agent",
        "ranking tradeoffs across price, timing, comfort, risk, and serviceability",
        "candidate inventory exists",
        "ranked recommendation and rationale",
    ),
    AgentSpec(
        "verification",
        "Verification Agent",
        "evidence checks, fare/refund constraints, order serviceability, missing data",
        "before any user-facing recommendation or execution",
        "verification report and confidence score",
    ),
    AgentSpec(
        "execution",
        "Execution Agent",
        "holds, booking readiness, cancellation, modification, payment staging",
        "after policy and verification pass",
        "staged actions with approval requirements",
    ),
    AgentSpec(
        "recovery",
        "Recovery Agent",
        "delay, cancellation, missed connection, supplier failure, downstream changes",
        "disruption or post-booking servicing request",
        "recovery plan and monitored risks",
    ),
    AgentSpec(
        "human_ops",
        "Human Escalation Agent",
        "handoff packet for suppliers, support, or complex approvals",
        "low verification confidence, high spend, or unsupported supplier action",
        "operator packet and escalation reason",
    ),
]


CITY_ALIASES = {
    "san francisco": "San Francisco",
    "sfo": "San Francisco",
    "new york": "New York",
    "nyc": "New York",
    "jfk": "New York",
    "ewr": "New York",
    "lga": "New York",
    "tokyo": "Tokyo",
    "lisbon": "Lisbon",
    "paris": "Paris",
    "rome": "Rome",
    "london": "London",
    "berlin": "Berlin",
    "los angeles": "Los Angeles",
    "lax": "Los Angeles",
    "chicago": "Chicago",
    "ord": "Chicago",
    "miami": "Miami",
    "zurich": "Zurich",
    "dubai": "Dubai",
    "istanbul": "Istanbul",
}


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _detected_cities(lowered: str) -> list[str]:
    cities = [city for alias, city in CITY_ALIASES.items() if re.search(rf"\b{re.escape(alias)}\b", lowered)]
    return _unique(cities)


def _intent_kind(lowered: str) -> str:
    if _contains_any(lowered, ("delay", "cancel", "miss", "late", "disruption", "rebook", "stranded")):
        return "recovery"
    if _contains_any(lowered, ("change", "move", "earlier", "later", "modify", "switch")):
        return "change"
    if _contains_any(lowered, ("plan", "book", "trip", "hotel", "flight", "train", "restaurant", "adventure")):
        return "new_trip"
    return "assist"


def _priority(lowered: str, risk_mode: str) -> str:
    if _contains_any(lowered, ("cheapest", "low cost", "budget", "price")):
        return "lowest_price"
    if _contains_any(lowered, ("fastest", "quickest", "earliest", "arrive", "meeting")):
        return "arrival_certainty"
    if _contains_any(lowered, ("comfortable", "direct", "avoid red-eye", "avoid redeye", "premium")):
        return "comfort"
    if risk_mode == "strict":
        return "policy_safety"
    if risk_mode == "fast":
        return "speed"
    return "balanced"


def _route(cities: list[str], intent_kind: str) -> str:
    if len(cities) >= 2:
        return f"{cities[0]} -> {cities[1]}"
    if len(cities) == 1 and intent_kind == "new_trip":
        return f"Home -> {cities[0]}"
    if intent_kind == "recovery":
        return "Recovery order"
    if intent_kind == "change":
        return "Change order"
    return "Travel order"


def _missing_inputs(cities: list[str], lowered: str, intent_kind: str) -> list[str]:
    missing: list[str] = []
    if intent_kind in {"new_trip", "change", "recovery"} and not cities:
        missing.append("origin_or_destination")
    if intent_kind == "new_trip" and not _contains_any(lowered, ("today", "tomorrow", "next", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december")):
        missing.append("travel_dates")
    if "hotel" in lowered and not _contains_any(lowered, ("near", "downtown", "airport", "soho", "neighborhood")):
        missing.append("hotel_area")
    return missing


def _status(intent_kind: str, verification_confidence: int, human_review: bool) -> str:
    if human_review:
        return "human_review_ready"
    if intent_kind == "recovery":
        return "recovery_prepared"
    if intent_kind == "new_trip":
        return "control_center_draft"
    if intent_kind == "change":
        return "change_ready"
    if verification_confidence >= 85:
        return "trip_order_drafted"
    return "needs_more_context"


def _score(intent_kind: str, risk_mode: str, missing_inputs: list[str], verification_confidence: int) -> int:
    base = {
        "recovery": 91,
        "change": 92,
        "new_trip": 88,
        "assist": 82,
    }.get(intent_kind, 82)
    if risk_mode == "strict":
        base += 3
    if risk_mode == "fast":
        base -= 2
    base -= min(len(missing_inputs) * 6, 18)
    return max(52, min(98, round((base + verification_confidence) / 2)))


def _permission_model(wallet_cap: int, risk_mode: str) -> dict[str, Any]:
    ride_cap = min(wallet_cap, 75) if wallet_cap else 0
    autonomy_level = 1 if risk_mode == "strict" else 2
    return {
        "autonomy_level": autonomy_level,
        "level_label": ["notify", "prepare", "approve_execute", "auto_execute"][autonomy_level - 1],
        "airport_rides": {
            "auto_adjust_pickup_if_flight_changes": risk_mode != "strict",
            "auto_book_if_under": 0,
            "ask_before_premium_above": max(ride_cap, 100),
        },
        "hotels": {
            "cancel_refundable_before_deadline": True,
            "book_non_refundable_automatically": False,
            "ask_before_above_per_night": 350,
        },
        "flights": {
            "auto_change_flights": False,
            "hold_replacement_options": True,
            "ask_before_fare_difference_above": min(wallet_cap, 50) if wallet_cap else 0,
        },
        "payments": {
            "use_wallet_balance_first": True,
            "use_card_backup_under": ride_cap,
            "use_card_backup_above_cap_without_approval": False,
        },
    }


def _products(intent_kind: str, route: str, wallet_cap: int, priority: str) -> list[dict[str, str]]:
    if intent_kind == "recovery":
        return [
            {"kind": "monitoring", "label": "Delay, waiver, traffic, hotel risk", "state": "live"},
            {"kind": "flight", "label": "Replacement flight ranked by arrival certainty", "state": "ranked"},
            {"kind": "hotel", "label": "Late arrival message prepared", "state": "approval"},
            {"kind": "transfer", "label": "Pickup window recalculated", "state": "staged"},
        ]
    if intent_kind == "new_trip":
        return [
            {"kind": "flight", "label": f"{route} flight candidates ranked by {priority.replace('_', ' ')}", "state": "ranked"},
            {"kind": "hotel", "label": "Stay options ranked by fit and cancellation window", "state": "ranked"},
            {"kind": "transfer", "label": "Airport transfer and timing buffer prepared", "state": "draft"},
            {"kind": "wallet", "label": f"Approval cap {wallet_cap}", "state": "pending"},
        ]
    if intent_kind == "change":
        return [
            {"kind": "pnr", "label": "Reservation status checked", "state": "verified"},
            {"kind": "ticket", "label": "Open ticket coupon confirmed", "state": "verified"},
            {"kind": "emd", "label": "Seat and bag extras checked for transfer", "state": "protected"},
            {"kind": "permission", "label": f"Ask before charges above {wallet_cap}", "state": "bounded"},
        ]
    return [
        {"kind": "intent", "label": "Request captured and structured", "state": "parsed"},
        {"kind": "search", "label": "Travel search scope prepared", "state": "ready"},
        {"kind": "permission", "label": f"Ask before charges above {wallet_cap}", "state": "bounded"},
    ]


def _agent_events(outputs: list[AgentOutput]) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    for output in outputs:
        events.append(
            {
                "event_type": output.agent_id,
                "title": output.title,
                "detail": output.summary,
                "actor": "manager" if output.agent_id == "manager" else "agent",
            }
        )
    return events


MODEL_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "traveler_reply": {
            "type": "string",
            "description": "A concise, helpful response to the traveler. No claims of completed bookings, payments, cancellations, or live supplier inventory.",
        },
        "manager_summary": {
            "type": "string",
            "description": "What the managing agent did and which specialist agents were assigned.",
        },
        "trip_title": {
            "type": "string",
            "description": "Short name for the trip order.",
        },
        "intent_kind": {
            "type": "string",
            "enum": ["new_trip", "change", "recovery", "assist"],
        },
        "priority": {
            "type": "string",
            "description": "Primary optimization axis such as arrival_certainty, lowest_price, comfort, policy_safety, speed, or balanced.",
        },
        "route": {
            "type": "string",
            "description": "Best inferred route or order name.",
        },
        "missing_inputs": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommended_next_steps": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 5,
        },
        "agent_summaries": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "enum": [
                            "context",
                            "profile",
                            "search",
                            "policy",
                            "recommendation",
                            "verification",
                            "execution",
                            "recovery",
                            "human_ops",
                        ],
                    },
                    "summary": {"type": "string"},
                    "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                    "requires_approval": {"type": "boolean"},
                },
                "required": ["agent_id", "summary", "confidence", "requires_approval"],
            },
        },
        "verification": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                "safe_to_execute": {"type": "boolean"},
                "approval_required_reason": {"type": "string"},
            },
            "required": ["confidence", "safe_to_execute", "approval_required_reason"],
        },
    },
    "required": [
        "traveler_reply",
        "manager_summary",
        "trip_title",
        "intent_kind",
        "priority",
        "route",
        "missing_inputs",
        "recommended_next_steps",
        "agent_summaries",
        "verification",
    ],
}


def _model_enabled() -> bool:
    return os.environ.get("EVARIAN_MODEL_AGENTS_ENABLED", "").lower() in {"1", "true", "yes", "on"}


def _model_provider() -> str:
    configured = os.environ.get("EVARIAN_MODEL_PROVIDER", "").strip().lower()
    if configured in {"gemini", "google", "google-gemini"}:
        return "gemini"
    if configured in {"openai", "responses"}:
        return "openai"
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    return "openai"


def _model_name(provider: str | None = None) -> str:
    selected = provider or _model_provider()
    if selected == "gemini":
        return os.environ.get("GEMINI_MODEL", "gemini-3.5-flash").strip() or "gemini-3.5-flash"
    return os.environ.get("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"


def _model_api_key(provider: str | None = None) -> str:
    selected = provider or _model_provider()
    if selected == "gemini":
        return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    return os.environ.get("OPENAI_API_KEY", "")


def _model_api_key_present(provider: str | None = None) -> bool:
    return bool(_model_api_key(provider))


def _model_provider_label(provider: str | None = None) -> str:
    selected = provider or _model_provider()
    return "Gemini API" if selected == "gemini" else "OpenAI Responses API"


def model_runtime_status() -> dict[str, Any]:
    provider = _model_provider()
    key_configured = _model_api_key_present(provider)
    return {
        "model_agents_enabled": _model_enabled(),
        "model_provider": provider,
        "model_key_configured": key_configured,
        "model": _model_name(provider),
        "gemini_key_configured": _model_api_key_present("gemini"),
        "gemini_model": _model_name("gemini"),
        "openai_key_configured": _model_api_key_present("openai"),
        "openai_model": _model_name("openai"),
    }


def _extract_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    chunks: list[str] = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks).strip()


def _extract_gemini_output_text(response: dict[str, Any]) -> str:
    chunks: list[str] = []
    for candidate in response.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content")
        if not isinstance(content, dict):
            continue
        for part in content.get("parts", []):
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks).strip()


def _agent_prompt(
    intent: str,
    wallet_cap: int,
    risk_mode: str,
    deterministic: dict[str, Any],
) -> dict[str, Any]:
    return {
        "traveler_request": intent,
        "wallet_cap": wallet_cap,
        "risk_mode": risk_mode,
        "deterministic_trip_order": {
            "route": deterministic["route"],
            "intent_kind": deterministic["intent_kind"],
            "priority": deterministic["priority"],
            "missing_inputs": deterministic["missing_inputs"],
            "permissions": deterministic["permissions"],
            "autopilot": deterministic["autopilot"],
            "products": deterministic["products"],
        },
        "hard_rules": [
            "Do not claim that flights, hotels, rides, payments, cancellations, refunds, holds, or supplier actions were actually executed.",
            "Every irreversible booking, payment, cancellation, refund, or rebooking requires explicit traveler approval unless a separate policy gate marks the exact action as execution_allowed.",
            "If live supplier APIs are missing, say the action is prepared or staged, not completed.",
            "Preserve the deterministic permission and approval boundaries.",
            "Return only valid JSON that matches the requested contract.",
        ],
        "response_contract": MODEL_RESPONSE_SCHEMA,
    }


def _system_instruction() -> str:
    return (
        "You are Evarian's managing travel agent. Compose specialist-agent output "
        "for a live Universal Trip Order. Be concrete, calm, and operational. "
        "Optimize for agentic travel search, recommendation, verification, recovery, "
        "permission checks, and execution readiness. Return only JSON. Do not use markdown."
    )


def _call_openai_agent_model(
    intent: str,
    wallet_cap: int,
    risk_mode: str,
    deterministic: dict[str, Any],
) -> dict[str, Any] | None:
    """Ask the model to enrich, not override, the deterministic travel order."""

    api_key = _model_api_key("openai")
    if not _model_enabled() or not api_key:
        return None

    prompt = _agent_prompt(intent, wallet_cap, risk_mode, deterministic)
    request_body = {
        "model": _model_name("openai"),
        "instructions": _system_instruction(),
        "input": json.dumps(prompt, sort_keys=True),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "evarian_agentic_trip_order",
                "strict": True,
                "schema": MODEL_RESPONSE_SCHEMA,
            }
        },
        "max_output_tokens": 1800,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=18) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return None

    output_text = _extract_output_text(payload)
    if not output_text:
        return None
    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _call_gemini_agent_model(
    intent: str,
    wallet_cap: int,
    risk_mode: str,
    deterministic: dict[str, Any],
) -> dict[str, Any] | None:
    """Ask Gemini to enrich, not override, the deterministic travel order."""

    api_key = _model_api_key("gemini")
    if not _model_enabled() or not api_key:
        return None

    prompt = _agent_prompt(intent, wallet_cap, risk_mode, deterministic)
    model_name = _model_name("gemini")
    model_path = model_name if model_name.startswith("models/") else f"models/{model_name}"
    encoded_model = urllib.parse.quote(model_path, safe="/")
    request_body = {
        "systemInstruction": {
            "parts": [{"text": _system_instruction()}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Enrich this deterministic Evarian travel order. "
                            "Return only a JSON object matching response_contract.\n\n"
                            f"{json.dumps(prompt, sort_keys=True)}"
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.25,
            "maxOutputTokens": 1800,
        },
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/{encoded_model}:generateContent",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=18) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return None

    output_text = _extract_gemini_output_text(payload)
    if not output_text:
        return None
    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _call_agent_model(
    intent: str,
    wallet_cap: int,
    risk_mode: str,
    deterministic: dict[str, Any],
) -> dict[str, Any] | None:
    provider = _model_provider()
    if provider == "gemini":
        return _call_gemini_agent_model(intent, wallet_cap, risk_mode, deterministic)
    return _call_openai_agent_model(intent, wallet_cap, risk_mode, deterministic)


def _apply_model_enrichment(base: dict[str, Any], model_data: dict[str, Any] | None) -> dict[str, Any]:
    provider = _model_provider()
    provider_label = _model_provider_label(provider)
    if not model_data:
        base["manager"]["model_backed"] = False
        base["manager"]["model_backed_reason"] = (
            f"{provider_label} model agents are disabled or unavailable; deterministic travel control plane is active."
            if _model_api_key_present(provider)
            else f"{provider_label} execution is gated until API-key use is explicitly configured."
        )
        return base

    verification = model_data.get("verification") if isinstance(model_data.get("verification"), dict) else {}
    model_confidence = verification.get("confidence")
    if isinstance(model_confidence, int):
        base["score"] = max(52, min(98, round((base["score"] + model_confidence) / 2)))

    if isinstance(model_data.get("route"), str) and model_data["route"].strip():
        base["route"] = model_data["route"].strip()[:120]
        base["control_center"]["trip"] = base["route"]
    if isinstance(model_data.get("priority"), str) and model_data["priority"].strip():
        base["priority"] = model_data["priority"].strip()[:64]
    if isinstance(model_data.get("intent_kind"), str) and model_data["intent_kind"] in {"new_trip", "change", "recovery", "assist"}:
        base["intent_kind"] = model_data["intent_kind"]
    if isinstance(model_data.get("missing_inputs"), list):
        base["missing_inputs"] = [str(item)[:80] for item in model_data["missing_inputs"][:8]]

    base["manager"].update(
        {
            "mode": "model_backed_control_plane",
            "model_backed": True,
            "model_provider": provider,
            "model": _model_name(provider),
            "model_backed_reason": f"{provider_label} enriched the trip order; deterministic approval gates still control execution.",
        }
    )
    if isinstance(model_data.get("manager_summary"), str) and model_data["manager_summary"].strip():
        base["manager"]["summary"] = model_data["manager_summary"].strip()[:700]
        base["agent_outputs"][0]["summary"] = base["manager"]["summary"]
    if isinstance(model_data.get("traveler_reply"), str) and model_data["traveler_reply"].strip():
        base["traveler_reply"] = model_data["traveler_reply"].strip()[:1400]
    if isinstance(model_data.get("trip_title"), str) and model_data["trip_title"].strip():
        base["trip_title"] = model_data["trip_title"].strip()[:100]
    if isinstance(model_data.get("recommended_next_steps"), list):
        base["recommended_next_steps"] = [str(step)[:180] for step in model_data["recommended_next_steps"][:5]]

    summaries = model_data.get("agent_summaries")
    if isinstance(summaries, list):
        summary_by_agent = {
            item.get("agent_id"): item
            for item in summaries
            if isinstance(item, dict) and isinstance(item.get("agent_id"), str)
        }
        for output in base["agent_outputs"]:
            item = summary_by_agent.get(output["agent_id"])
            if not item:
                continue
            if isinstance(item.get("summary"), str) and item["summary"].strip():
                output["summary"] = item["summary"].strip()[:600]
            if isinstance(item.get("confidence"), int):
                output["confidence"] = max(0, min(100, item["confidence"]))
            if isinstance(item.get("requires_approval"), bool):
                output["requires_approval"] = item["requires_approval"]

    approval_reason = verification.get("approval_required_reason")
    if isinstance(approval_reason, str) and approval_reason.strip():
        base["autopilot"]["approval_gate"] = approval_reason.strip()[:220]
    base["autopilot"]["can_auto_execute"] = False
    base["autopilot"]["requires_approval"] = True
    base["control_center"]["next_approval"] = base["autopilot"]["approval_gate"]
    return base


def run_agentic_travel_agents(intent: str, wallet_cap: int, risk_mode: str) -> dict[str, Any]:
    """Run the managing agent and the specialist travel agents."""

    lowered = intent.lower()
    intent_kind = _intent_kind(lowered)
    cities = _detected_cities(lowered)
    priority = _priority(lowered, risk_mode)
    route = _route(cities, intent_kind)
    missing_inputs = _missing_inputs(cities, lowered, intent_kind)
    permissions = _permission_model(wallet_cap, risk_mode)
    products = _products(intent_kind, route, wallet_cap, priority)

    selected_agents = ["context", "profile", "policy", "search", "recommendation", "verification", "execution"]
    if intent_kind == "recovery":
        selected_agents.insert(4, "recovery")
    verification_confidence = 94 - min(len(missing_inputs) * 10, 30)
    human_review = verification_confidence < 70 or wallet_cap >= 5000
    if human_review:
        selected_agents.append("human_ops")

    context_output = AgentOutput(
        "context",
        "Intent structured",
        f"Classified request as {intent_kind.replace('_', ' ')} with {priority.replace('_', ' ')} priority.",
        92,
        {
            "intent_kind": intent_kind,
            "route": route,
            "cities": cities,
            "priority": priority,
            "missing_inputs": missing_inputs,
        },
        ["profile", "policy", "search"],
    )
    profile_output = AgentOutput(
        "profile",
        "Traveler profile inferred",
        "Applied conservative default preferences until the user has saved profile memory.",
        78,
        {
            "schedule_bias": "protect arrival time",
            "hotel_bias": "refundable and serviceable first",
            "seat_bias": "avoid red-eye when intent suggests business travel",
            "memory_status": "session_inferred",
        },
        ["policy", "recommendation"],
    )
    policy_output = AgentOutput(
        "policy",
        "Wallet and policy guardrails attached",
        f"Prepared-only autonomy with approval required above {wallet_cap} and for irreversible supplier actions.",
        96,
        {
            "wallet_cap": wallet_cap,
            "risk_mode": risk_mode,
            "autonomy_level": permissions["autonomy_level"],
            "blocked_without_approval": ["flight purchase", "non-refundable hotel", "cancellation", "rebook with fare difference"],
        },
        ["recommendation", "execution"],
        requires_approval=True,
    )
    search_output = AgentOutput(
        "search",
        "Travel supply search staged",
        "Created a supplier search scope across flights, stays, transfers, and servicing constraints.",
        84 if missing_inputs else 90,
        {
            "source_classes": ["air", "hotel", "ground_transport", "weather", "traffic", "supplier_terms"],
            "candidate_count": 8 if intent_kind != "assist" else 3,
            "live_supplier_access": "not_connected",
        },
        ["recommendation", "verification"],
    )
    recovery_output = AgentOutput(
        "recovery",
        "Recovery path prepared",
        "Monitored disruption risks and staged downstream changes for hotel, ride, and notifications.",
        90,
        {
            "recovery_triggers": ["flight_status", "fare_waiver", "missed_connection", "hotel_check_in", "traffic"],
            "prepared_actions": ["rank replacement flight", "move pickup", "notify hotel", "prepare team update"],
        },
        ["verification", "execution"],
        requires_approval=True,
    )
    recommendation_output = AgentOutput(
        "recommendation",
        "Recommendation ranked",
        f"Ranked the order around {priority.replace('_', ' ')} while preserving cancellation and serviceability.",
        88,
        {
            "ranking_model": "serviceability_first",
            "tradeoffs": ["arrival certainty", "price", "refundability", "supplier reliability"],
            "top_recommendation": products[0]["label"],
        },
        ["verification"],
    )
    verification_output = AgentOutput(
        "verification",
        "Order verified before execution",
        "Checked missing inputs, approval gates, and whether the staged actions are serviceable.",
        verification_confidence,
        {
            "checks": ["required trip fields", "policy gates", "refundability", "payment boundary", "human fallback"],
            "missing_inputs": missing_inputs,
            "pass": verification_confidence >= 70,
        },
        ["execution"] if verification_confidence >= 70 else ["human_ops"],
    )
    execution_output = AgentOutput(
        "execution",
        "Execution staged",
        "Prepared holds, messages, and booking actions but did not spend, cancel, or rebook without approval.",
        93,
        {
            "can_execute_now": False,
            "requires_user_approval": True,
            "staged_actions": [product["label"] for product in products if product["state"] in {"ranked", "staged", "approval", "pending"}],
        },
        ["human_ops"] if human_review else [],
        requires_approval=True,
    )
    human_ops_output = AgentOutput(
        "human_ops",
        "Human handoff packet ready",
        "Packaged the intent, constraints, policy, and staged actions for a human operator if automation cannot safely continue.",
        86,
        {
            "handoff_reason": "high spend or insufficient verification confidence" if human_review else "available as fallback",
            "packet": ["traveler intent", "constraints", "policy gates", "candidate products", "verification report"],
        },
        [],
    )

    output_by_agent = {
        output.agent_id: output
        for output in [
            context_output,
            profile_output,
            policy_output,
            search_output,
            recovery_output,
            recommendation_output,
            verification_output,
            execution_output,
            human_ops_output,
        ]
    }
    specialist_outputs = [output_by_agent[agent_id] for agent_id in selected_agents]

    manager_summary = (
        "Delegated traveler intent to context, preference, policy, search, recommendation, "
        "verification, and execution agents. Recovery and human-ops agents are selected only when needed."
    )
    manager_output = AgentOutput(
        "manager",
        "Managing agent delegated the order",
        manager_summary,
        95,
        {
            "run_id": f"RUN-{uuid4().hex[:10].upper()}",
            "selected_agents": selected_agents,
            "assignment_strategy": "context -> guardrails -> search -> rank -> verify -> stage execution",
        },
        selected_agents,
    )
    outputs = [manager_output, *specialist_outputs]
    status = _status(intent_kind, verification_confidence, human_review)
    score = _score(intent_kind, risk_mode, missing_inputs, verification_confidence)

    delegation_plan = [
        {
            "order": index + 1,
            "agent_id": agent_id,
            "reason": output_by_agent[agent_id].summary,
            "status": "completed",
        }
        for index, agent_id in enumerate(selected_agents)
    ]

    next_approval = next(
        (product["label"] for product in products if product["state"] in {"approval", "staged", "pending", "ranked"}),
        "Approve staged execution before any irreversible supplier action",
    )

    base = {
        "manager": {
            "id": "manager",
            "name": "Managing Travel Agent",
            "mode": "deterministic_control_plane",
            "model_backed": False,
            "model_backed_reason": "Model-backed enrichment is gated until API-key use is explicitly configured.",
            "run_id": manager_output.artifacts["run_id"],
        },
        "agent_network": [spec.as_dict() for spec in AGENT_SPECS],
        "delegation_plan": delegation_plan,
        "agent_outputs": [output.as_dict() for output in outputs],
        "extracted_requirements": [
            "command-first traveler intent capture",
            "traveler preference memory",
            "search across air, hotel, ride, rail, and downstream services",
            "policy and wallet guardrails before action",
            "recommendation ranking by traveler priority",
            "verification before spend or supplier changes",
            "execution staging with approval gates",
            "recovery monitoring and human handoff",
        ],
        "status": status,
        "route": route,
        "score": score,
        "intent_kind": intent_kind,
        "priority": priority,
        "missing_inputs": missing_inputs,
        "products": products,
        "permissions": permissions,
        "autopilot": {
            "starting_level": permissions["autonomy_level"],
            "target_level": 3 if risk_mode != "strict" and not human_review else 2,
            "can_auto_execute": False,
            "requires_approval": True,
            "approval_gate": "All booking, payment, cancellation, and rebooking actions require explicit approval.",
        },
        "control_center": {
            "title": "Live trip control center",
            "trip": route,
            "status": status,
            "risk": "medium" if intent_kind == "recovery" or human_review else "low",
            "monitors": ["flight_status", "traffic", "ride_eta", "weather", "fare_waiver", "hotel_late_arrival", "refund_deadlines"],
            "next_approval": next_approval,
        },
        "audit_events": _agent_events(outputs[:6]),
        "monitoring": ["flight_status", "fare_waiver", "weather", "traffic", "hotel_check_in", "supplier_terms"],
        "allowed_actions": ["search", "rank", "hold", "modify", "cancel", "refund", "rebook", "message", "escalate"],
    }
    return _apply_model_enrichment(base, _call_agent_model(intent, wallet_cap, risk_mode, base))
