"""FastAPI app for the Evarian travel control prototype."""

from __future__ import annotations

import os
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.agentic_travel import model_runtime_status, run_agentic_travel_agents
from backend.amadeus_client import (
    AmadeusAPIError,
    AmadeusClient,
    AmadeusConfigError,
    amadeus_runtime_status,
)
from backend.travel_execution import execute_supplier_action, execution_runtime_status
from backend.travel_policy import evaluate_action_policy


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def database_path() -> Path:
    configured = os.environ.get("EVARIAN_DATABASE_PATH")
    if configured:
        return Path(configured)
    return Path(os.environ.get("DATA_DIR", "/var/lib/evarian")) / "evarian.sqlite3"


DB_PATH = database_path()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS waitlist (
              id TEXT PRIMARY KEY,
              email TEXT NOT NULL UNIQUE,
              source TEXT,
              product TEXT,
              payload_json TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trip_orders (
              id TEXT PRIMARY KEY,
              intent TEXT NOT NULL,
              wallet_cap INTEGER NOT NULL,
              risk_mode TEXT NOT NULL,
              route TEXT NOT NULL,
              score INTEGER NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trip_permissions (
              order_id TEXT PRIMARY KEY,
              payload_json TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(order_id) REFERENCES trip_orders(id)
            );

            CREATE TABLE IF NOT EXISTS trip_events (
              id TEXT PRIMARY KEY,
              order_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              title TEXT NOT NULL,
              detail TEXT NOT NULL,
              actor TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(order_id) REFERENCES trip_orders(id)
            );

            CREATE TABLE IF NOT EXISTS supplier_actions (
              id TEXT PRIMARY KEY,
              order_id TEXT NOT NULL,
              supplier TEXT NOT NULL,
              action_type TEXT NOT NULL,
              service_type TEXT NOT NULL,
              status TEXT NOT NULL,
              idempotency_key TEXT,
              proposed_action_json TEXT NOT NULL,
              execution_payload_json TEXT NOT NULL,
              policy_json TEXT NOT NULL,
              response_json TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(order_id) REFERENCES trip_orders(id)
            );
            """
        )


class WaitlistBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    source: Optional[str] = None
    product: Optional[str] = None
    joined_at: Optional[str] = None


class TripOrderBody(BaseModel):
    intent: str = Field(min_length=2, max_length=1200)
    wallet_cap: int = Field(default=250, ge=0, le=50000)
    risk_mode: str = Field(default="balanced", pattern="^(balanced|strict|fast)$")


class PermissionSettingsBody(BaseModel):
    autonomy_level: int = Field(default=2, ge=1, le=4)
    airport_ride_cap: int = Field(default=75, ge=0, le=50000)
    flight_change_cap: int = Field(default=50, ge=0, le=50000)
    hotel_nightly_cap: int = Field(default=350, ge=0, le=50000)
    auto_adjust_airport_rides: bool = True
    auto_book_airport_rides: bool = False
    cancel_refundable_hotels: bool = True
    book_non_refundable_hotels: bool = False
    auto_change_flights: bool = False
    hold_replacement_flights: bool = True
    use_wallet_first: bool = True
    use_card_backup_under_cap: bool = True


class TripEventBody(BaseModel):
    event_type: str = Field(default="note", min_length=2, max_length=64)
    title: str = Field(min_length=2, max_length=140)
    detail: str = Field(min_length=2, max_length=1000)
    actor: str = Field(default="agent", min_length=2, max_length=64)


class ProposedActionBody(BaseModel):
    action_type: str = Field(pattern="^(search|rank|compare|monitor|hold|book|pay|cancel|refund|rebook|modify|message|escalate)$")
    service_type: str = Field(default="airport_ride", max_length=80)
    description: str = Field(default="", max_length=1000)
    amount: int = Field(default=0, ge=0, le=50000)
    refundable: bool = True
    supplier_reliable: bool = False
    within_supplier_terms: bool = False
    model_confidence: int = Field(default=0, ge=0, le=100)
    payment_authorized: bool = False
    user_approved: bool = False
    because: str = Field(default="", max_length=1200)
    source_count: int = Field(default=0, ge=0, le=30)
    direct_supplier_verified: bool = False
    maps_verified: bool = False
    points_checked: bool = False
    price_history_checked: bool = False
    credit_card_fit_checked: bool = False
    insurance_verified: bool = False
    logistics_verified: bool = False
    traveler_profile_applied: bool = False
    duration_hours: Optional[float] = Field(default=None, ge=0, le=72)
    premium_cabin: bool = False
    points_requested: bool = False


class FlightOffersSearchBody(BaseModel):
    origin_location_code: str = Field(pattern="^[A-Za-z]{3}$")
    destination_location_code: str = Field(pattern="^[A-Za-z]{3}$")
    departure_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    adults: int = Field(default=1, ge=1, le=9)
    return_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    children: int = Field(default=0, ge=0, le=9)
    infants: int = Field(default=0, ge=0, le=9)
    travel_class: Optional[str] = Field(
        default=None,
        pattern="^(ECONOMY|PREMIUM_ECONOMY|BUSINESS|FIRST)$",
    )
    non_stop: Optional[bool] = None
    currency_code: Optional[str] = Field(default=None, pattern="^[A-Za-z]{3}$")
    max_results: int = Field(default=10, ge=1, le=50)


class FlightOffersPriceBody(BaseModel):
    flight_offers: list[dict[str, Any]] = Field(min_length=1, max_length=6)
    include_detailed_fare_rules: bool = False


class HotelListByCityBody(BaseModel):
    city_code: str = Field(pattern="^[A-Za-z]{3}$")
    radius: Optional[int] = Field(default=None, ge=1, le=300)
    radius_unit: Optional[str] = Field(default=None, pattern="^(KM|MILE|km|mile)$")
    chain_codes: Optional[str] = Field(default=None, max_length=80)
    amenities: Optional[str] = Field(default=None, max_length=240)
    ratings: Optional[str] = Field(default=None, max_length=20)
    hotel_source: Optional[str] = Field(default=None, pattern="^(ALL|BEDBANK|DIRECTCHAIN|all|bedbank|directchain)$")


class HotelOffersSearchBody(BaseModel):
    hotel_ids: list[str] = Field(min_length=1, max_length=20)
    adults: int = Field(default=1, ge=1, le=9)
    check_in_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    check_out_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    room_quantity: int = Field(default=1, ge=1, le=9)
    currency_code: Optional[str] = Field(default=None, pattern="^[A-Za-z]{3}$")
    best_rate_only: Optional[bool] = None


class HotelOfferGetBody(BaseModel):
    offer_id: str = Field(min_length=4, max_length=220)


class SupplierActionStageBody(BaseModel):
    supplier: str = Field(default="amadeus", pattern="^(amadeus|manual)$")
    proposed_action: ProposedActionBody
    execution_payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = Field(default=None, max_length=160)


class SupplierActionExecuteBody(BaseModel):
    user_approved: bool = False
    payment_authorized: bool = False
    dry_run: bool = False
    additional_evidence: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(title="Evarian Travel OS", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://drinknile.com",
        "https://www.drinknile.com",
        "https://api.drinknile.com",
        "null",
    ],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
init_db()


def default_permissions(wallet_cap: int) -> dict[str, Any]:
    ride_cap = min(wallet_cap, 75) if wallet_cap else 0
    return {
        "autonomy_level": 2,
        "level_label": "prepare",
        "airport_rides": {
            "auto_adjust_pickup_if_flight_changes": True,
            "auto_book_if_under": ride_cap,
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
            "ask_before_fare_difference_above": 50,
        },
        "payments": {
            "use_wallet_balance_first": True,
            "use_card_backup_under": ride_cap,
            "use_card_backup_above_cap_without_approval": False,
        },
    }


def build_control_center(route: str, status: str, products: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "title": "Live trip control center",
        "trip": route,
        "status": status,
        "risk": "medium" if status.startswith("recovery") else "low",
        "monitors": [
            "flight_status",
            "traffic",
            "ride_eta",
            "hotel_late_arrival",
            "refund_deadlines",
        ],
        "next_approval": next(
            (product["label"] for product in products if product["state"] in {"staged", "approval", "actionable"}),
            "No approval required right now",
        ),
    }


def default_events(order: dict[str, Any]) -> list[dict[str, str]]:
    if str(order["status"]).startswith("recovery"):
        return [
            {"event_type": "monitor", "title": "Flight delay detected", "detail": "The backend agent flagged delay, traffic, ride, and hotel risk.", "actor": "agent"},
            {"event_type": "prepare", "title": "Pickup recalculated", "detail": "The agent prepared a new pickup window and held the action for approval.", "actor": "agent"},
            {"event_type": "permission", "title": "Permission checked", "detail": "Airport ride cap and hotel approval rules were evaluated before action.", "actor": "system"},
        ]
    return [
        {"event_type": "monitor", "title": "Trip state created", "detail": "The control center was created from traveler intent.", "actor": "agent"},
        {"event_type": "permission", "title": "Permission profile attached", "detail": "Spending caps and approval rules were bound to the trip.", "actor": "system"},
        {"event_type": "prepare", "title": "Action path prepared", "detail": "Supplier action is staged until approval or pre-authorized limits allow execution.", "actor": "agent"},
    ]


def build_trip_order(intent: str, wallet_cap: int, risk_mode: str) -> dict[str, Any]:
    managed = run_agentic_travel_agents(intent, wallet_cap, risk_mode)
    return {
        "id": f"EV-{uuid4().hex[:8].upper()}",
        "status": managed["status"],
        "route": managed["route"],
        "score": managed["score"],
        "intent": intent,
        "wallet_cap": wallet_cap,
        "risk_mode": risk_mode,
        **managed,
    }


def row_to_order(row: sqlite3.Row) -> dict[str, Any]:
    return json.loads(row["payload_json"])


def fetch_order(conn: sqlite3.Connection, order_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT payload_json FROM trip_orders WHERE id = ?", (order_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="trip order not found")
    return row_to_order(row)


def insert_event(conn: sqlite3.Connection, order_id: str, event: dict[str, str]) -> dict[str, str]:
    row = {
        "id": f"EVT-{uuid4().hex[:10].upper()}",
        "order_id": order_id,
        "event_type": event["event_type"],
        "title": event["title"],
        "detail": event["detail"],
        "actor": event["actor"],
        "created_at": utc_now(),
    }
    conn.execute(
        """
        INSERT INTO trip_events(id, order_id, event_type, title, detail, actor, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["id"],
            row["order_id"],
            row["event_type"],
            row["title"],
            row["detail"],
            row["actor"],
            row["created_at"],
        ),
    )
    return row


def action_status_from_policy(policy: dict[str, Any]) -> str:
    if policy["decision"] == "execution_allowed":
        return "ready"
    return str(policy["decision"])


def row_to_supplier_action(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "order_id": row["order_id"],
        "supplier": row["supplier"],
        "action_type": row["action_type"],
        "service_type": row["service_type"],
        "status": row["status"],
        "idempotency_key": row["idempotency_key"],
        "proposed_action": json.loads(row["proposed_action_json"]),
        "execution_payload": json.loads(row["execution_payload_json"]),
        "policy": json.loads(row["policy_json"]),
        "response": json.loads(row["response_json"]) if row["response_json"] else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def fetch_supplier_action(conn: sqlite3.Connection, order_id: str, action_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT *
        FROM supplier_actions
        WHERE order_id = ? AND id = ?
        """,
        (order_id, action_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="supplier action not found")
    return row_to_supplier_action(row)


@app.get("/api/health")
def health() -> dict[str, Any]:
    model_status = model_runtime_status()
    return {
        "ok": True,
        "service": "evarian-travel-os",
        "database": str(DB_PATH),
        **model_status,
        "suppliers": {
            "amadeus": amadeus_runtime_status(),
        },
        "execution": execution_runtime_status(),
        "time": utc_now(),
    }


@app.get("/api/suppliers/amadeus/status")
def amadeus_status() -> dict[str, Any]:
    return amadeus_runtime_status()


@app.post("/api/suppliers/amadeus/flight-offers")
def amadeus_flight_offers(body: FlightOffersSearchBody) -> dict[str, Any]:
    try:
        result = AmadeusClient().flight_offers_search(
            origin_location_code=body.origin_location_code,
            destination_location_code=body.destination_location_code,
            departure_date=body.departure_date,
            adults=body.adults,
            return_date=body.return_date,
            children=body.children,
            infants=body.infants,
            travel_class=body.travel_class,
            non_stop=body.non_stop,
            currency_code=body.currency_code,
            max_results=body.max_results,
        )
    except AmadeusConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AmadeusAPIError as exc:
        status_code = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status_code, detail=exc.detail) from exc
    return result


@app.post("/api/suppliers/amadeus/flight-offers/price")
def amadeus_flight_offers_price(body: FlightOffersPriceBody) -> dict[str, Any]:
    try:
        result = AmadeusClient().flight_offers_price(
            flight_offers=body.flight_offers,
            include_detailed_fare_rules=body.include_detailed_fare_rules,
        )
    except AmadeusConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AmadeusAPIError as exc:
        status_code = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status_code, detail=exc.detail) from exc
    return result


@app.post("/api/suppliers/amadeus/hotels/by-city")
def amadeus_hotels_by_city(body: HotelListByCityBody) -> dict[str, Any]:
    try:
        result = AmadeusClient().hotel_list_by_city(
            city_code=body.city_code,
            radius=body.radius,
            radius_unit=body.radius_unit,
            chain_codes=body.chain_codes,
            amenities=body.amenities,
            ratings=body.ratings,
            hotel_source=body.hotel_source,
        )
    except AmadeusConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AmadeusAPIError as exc:
        status_code = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status_code, detail=exc.detail) from exc
    return result


@app.post("/api/suppliers/amadeus/hotel-offers")
def amadeus_hotel_offers(body: HotelOffersSearchBody) -> dict[str, Any]:
    try:
        result = AmadeusClient().hotel_offers_search(
            hotel_ids=body.hotel_ids,
            adults=body.adults,
            check_in_date=body.check_in_date,
            check_out_date=body.check_out_date,
            room_quantity=body.room_quantity,
            currency_code=body.currency_code,
            best_rate_only=body.best_rate_only,
        )
    except AmadeusConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AmadeusAPIError as exc:
        status_code = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status_code, detail=exc.detail) from exc
    return result


@app.post("/api/suppliers/amadeus/hotel-offer")
def amadeus_hotel_offer(body: HotelOfferGetBody) -> dict[str, Any]:
    try:
        result = AmadeusClient().hotel_offer_get(offer_id=body.offer_id)
    except AmadeusConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AmadeusAPIError as exc:
        status_code = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status_code, detail=exc.detail) from exc
    return result


@app.get("/api/demo-trip")
def demo_trip() -> dict[str, Any]:
    return build_trip_order(
        "My SFO flight leaves at 9:15. Monitor traffic, prepare pickup options, and ask before spend above $75.",
        75,
        "balanced",
    )


@app.post("/api/waitlist")
def waitlist(body: WaitlistBody) -> dict[str, Any]:
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=400, detail="invalid email address")
    row_id = uuid4().hex
    payload_json = body.model_dump_json()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO waitlist(id, email, source, product, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
              source = excluded.source,
              product = excluded.product,
              payload_json = excluded.payload_json
            """,
            (
                row_id,
                email,
                body.source,
                body.product,
                payload_json,
                utc_now(),
            ),
        )
    return {"ok": True, "email": email}


@app.get("/api/trip-orders")
def list_trip_orders(limit: int = 25) -> dict[str, Any]:
    bounded_limit = max(1, min(limit, 100))
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT payload_json FROM trip_orders
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (bounded_limit,),
        ).fetchall()
    return {"items": [row_to_order(row) for row in rows]}


@app.post("/api/trip-orders")
def create_trip_order(body: TripOrderBody) -> dict[str, Any]:
    order = build_trip_order(body.intent, body.wallet_cap, body.risk_mode)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO trip_orders(id, intent, wallet_cap, risk_mode, route, score, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order["id"],
                body.intent,
                body.wallet_cap,
                body.risk_mode,
                order["route"],
                order["score"],
                json.dumps(order, sort_keys=True),
                utc_now(),
            ),
        )
        conn.execute(
            """
            INSERT INTO trip_permissions(order_id, payload_json, updated_at)
            VALUES (?, ?, ?)
            """,
            (
                order["id"],
                json.dumps(order["permissions"], sort_keys=True),
                utc_now(),
            ),
        )
        for event in order["audit_events"]:
            insert_event(conn, order["id"], event)
    return order


@app.get("/api/trip-orders/{order_id}")
def get_trip_order(order_id: str) -> dict[str, Any]:
    with connect() as conn:
        order = fetch_order(conn, order_id)
        permissions_row = conn.execute(
            "SELECT payload_json FROM trip_permissions WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        event_rows = conn.execute(
            """
            SELECT id, order_id, event_type, title, detail, actor, created_at
            FROM trip_events
            WHERE order_id = ?
            ORDER BY created_at ASC
            """,
            (order_id,),
        ).fetchall()
    order["permissions"] = json.loads(permissions_row["payload_json"]) if permissions_row else order["permissions"]
    order["events"] = [dict(row) for row in event_rows]
    return order


@app.put("/api/trip-orders/{order_id}/permissions")
def update_trip_permissions(order_id: str, body: PermissionSettingsBody) -> dict[str, Any]:
    permissions = {
        "autonomy_level": body.autonomy_level,
        "level_label": ["notify", "prepare", "approve_execute", "auto_execute"][body.autonomy_level - 1],
        "airport_rides": {
            "auto_adjust_pickup_if_flight_changes": body.auto_adjust_airport_rides,
            "auto_book_if_under": body.airport_ride_cap if body.auto_book_airport_rides else 0,
            "ask_before_premium_above": max(body.airport_ride_cap, 100),
        },
        "hotels": {
            "cancel_refundable_before_deadline": body.cancel_refundable_hotels,
            "book_non_refundable_automatically": body.book_non_refundable_hotels,
            "ask_before_above_per_night": body.hotel_nightly_cap,
        },
        "flights": {
            "auto_change_flights": body.auto_change_flights,
            "hold_replacement_options": body.hold_replacement_flights,
            "ask_before_fare_difference_above": body.flight_change_cap,
        },
        "payments": {
            "use_wallet_balance_first": body.use_wallet_first,
            "use_card_backup_under": body.airport_ride_cap if body.use_card_backup_under_cap else 0,
            "use_card_backup_above_cap_without_approval": False,
        },
    }
    with connect() as conn:
        fetch_order(conn, order_id)
        conn.execute(
            """
            INSERT INTO trip_permissions(order_id, payload_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(order_id) DO UPDATE SET
              payload_json = excluded.payload_json,
              updated_at = excluded.updated_at
            """,
            (order_id, json.dumps(permissions, sort_keys=True), utc_now()),
        )
        event = insert_event(
            conn,
            order_id,
            {
                "event_type": "permission",
                "title": "Permissions updated",
                "detail": f"Autonomy level set to {permissions['level_label']}.",
                "actor": "user",
            },
        )
    return {"ok": True, "permissions": permissions, "event": event}


@app.get("/api/trip-orders/{order_id}/events")
def list_trip_events(order_id: str) -> dict[str, Any]:
    with connect() as conn:
        fetch_order(conn, order_id)
        rows = conn.execute(
            """
            SELECT id, order_id, event_type, title, detail, actor, created_at
            FROM trip_events
            WHERE order_id = ?
            ORDER BY created_at ASC
            """,
            (order_id,),
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.post("/api/trip-orders/{order_id}/events")
def create_trip_event(order_id: str, body: TripEventBody) -> dict[str, Any]:
    with connect() as conn:
        fetch_order(conn, order_id)
        event = insert_event(
            conn,
            order_id,
            {
                "event_type": body.event_type,
                "title": body.title,
                "detail": body.detail,
                "actor": body.actor,
            },
        )
    return event


@app.post("/api/trip-orders/{order_id}/actions/evaluate")
def evaluate_trip_action(order_id: str, body: ProposedActionBody) -> dict[str, Any]:
    with connect() as conn:
        order = fetch_order(conn, order_id)
        permissions_row = conn.execute(
            "SELECT payload_json FROM trip_permissions WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        permissions = json.loads(permissions_row["payload_json"]) if permissions_row else order["permissions"]
        result = evaluate_action_policy(permissions, body.model_dump())
        event = insert_event(
            conn,
            order_id,
            {
                "event_type": "policy",
                "title": f"Action policy evaluated: {result['decision']}",
                "detail": f"{body.action_type} evaluated. Failed gates: {', '.join(result['failed_gates']) or 'none'}.",
                "actor": "policy",
            },
        )
    return {"ok": True, "order_id": order_id, "policy": result, "event": event}


@app.get("/api/trip-orders/{order_id}/supplier-actions")
def list_supplier_actions(order_id: str) -> dict[str, Any]:
    with connect() as conn:
        fetch_order(conn, order_id)
        rows = conn.execute(
            """
            SELECT *
            FROM supplier_actions
            WHERE order_id = ?
            ORDER BY created_at DESC
            """,
            (order_id,),
        ).fetchall()
    return {"items": [row_to_supplier_action(row) for row in rows]}


@app.post("/api/trip-orders/{order_id}/supplier-actions")
def stage_supplier_action(order_id: str, body: SupplierActionStageBody) -> dict[str, Any]:
    proposed_action = body.proposed_action.model_dump()
    with connect() as conn:
        order = fetch_order(conn, order_id)
        permissions_row = conn.execute(
            "SELECT payload_json FROM trip_permissions WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        permissions = json.loads(permissions_row["payload_json"]) if permissions_row else order["permissions"]
        policy = evaluate_action_policy(permissions, proposed_action)
        action_id = f"ACT-{uuid4().hex[:10].upper()}"
        now = utc_now()
        status = action_status_from_policy(policy)
        conn.execute(
            """
            INSERT INTO supplier_actions(
              id, order_id, supplier, action_type, service_type, status,
              idempotency_key, proposed_action_json, execution_payload_json,
              policy_json, response_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                order_id,
                body.supplier,
                policy["action_type"],
                policy["service_type"],
                status,
                body.idempotency_key,
                json.dumps(proposed_action, sort_keys=True),
                json.dumps(body.execution_payload, sort_keys=True),
                json.dumps(policy, sort_keys=True),
                None,
                now,
                now,
            ),
        )
        event = insert_event(
            conn,
            order_id,
            {
                "event_type": "supplier_action",
                "title": f"Supplier action staged: {status}",
                "detail": f"{body.supplier}.{policy['service_type']}.{policy['action_type']} staged. Failed gates: {', '.join(policy['failed_gates']) or 'none'}.",
                "actor": "execution",
            },
        )
        action = fetch_supplier_action(conn, order_id, action_id)
    return {"ok": True, "order_id": order_id, "action": action, "event": event}


@app.get("/api/trip-orders/{order_id}/supplier-actions/{action_id}")
def get_supplier_action(order_id: str, action_id: str) -> dict[str, Any]:
    with connect() as conn:
        fetch_order(conn, order_id)
        action = fetch_supplier_action(conn, order_id, action_id)
    return action


@app.post("/api/trip-orders/{order_id}/supplier-actions/{action_id}/execute")
def execute_staged_supplier_action(
    order_id: str,
    action_id: str,
    body: SupplierActionExecuteBody,
) -> dict[str, Any]:
    with connect() as conn:
        order = fetch_order(conn, order_id)
        action = fetch_supplier_action(conn, order_id, action_id)
        permissions_row = conn.execute(
            "SELECT payload_json FROM trip_permissions WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        permissions = json.loads(permissions_row["payload_json"]) if permissions_row else order["permissions"]
        proposed_action = dict(action["proposed_action"])
        if body.user_approved:
            proposed_action["user_approved"] = True
        if body.payment_authorized:
            proposed_action["payment_authorized"] = True
        proposed_action.update(body.additional_evidence)
        policy = evaluate_action_policy(permissions, proposed_action)

        if not policy["can_execute"]:
            response = {
                "status": "blocked",
                "reason": "policy did not allow execution",
                "policy_decision": policy["decision"],
                "failed_gates": policy["failed_gates"],
                "side_effects": "none",
            }
            status = policy["decision"]
        else:
            try:
                response = execute_supplier_action(
                    supplier=action["supplier"],
                    action_type=policy["action_type"],
                    service_type=policy["service_type"],
                    execution_payload=action["execution_payload"],
                    dry_run=body.dry_run,
                )
            except (AmadeusConfigError, ValueError) as exc:
                response = {
                    "status": "blocked",
                    "reason": str(exc),
                    "side_effects": "none",
                }
            except AmadeusAPIError as exc:
                response = {
                    "status": "supplier_error",
                    "status_code": exc.status_code,
                    "reason": exc.detail,
                    "side_effects": "unknown",
                }
            status = str(response.get("status") or "executed")

        now = utc_now()
        conn.execute(
            """
            UPDATE supplier_actions
            SET status = ?,
                proposed_action_json = ?,
                policy_json = ?,
                response_json = ?,
                updated_at = ?
            WHERE id = ? AND order_id = ?
            """,
            (
                status,
                json.dumps(proposed_action, sort_keys=True),
                json.dumps(policy, sort_keys=True),
                json.dumps(response, sort_keys=True),
                now,
                action_id,
                order_id,
            ),
        )
        event = insert_event(
            conn,
            order_id,
            {
                "event_type": "supplier_execution",
                "title": f"Supplier execution: {status}",
                "detail": f"{action['supplier']}.{policy['service_type']}.{policy['action_type']} execution evaluated with side effects: {response.get('side_effects', 'none')}.",
                "actor": "execution",
            },
        )
        updated_action = fetch_supplier_action(conn, order_id, action_id)
    return {
        "ok": status in {"executed", "dry_run"},
        "order_id": order_id,
        "action": updated_action,
        "policy": policy,
        "response": response,
        "event": event,
    }
