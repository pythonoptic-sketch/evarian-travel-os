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
    action_type: str = Field(pattern="^(search|rank|hold|book|pay|cancel|refund|rebook|modify|message|escalate)$")
    service_type: str = Field(default="airport_ride", max_length=80)
    description: str = Field(default="", max_length=1000)
    amount: int = Field(default=0, ge=0, le=50000)
    refundable: bool = True
    supplier_reliable: bool = False
    within_supplier_terms: bool = False
    model_confidence: int = Field(default=0, ge=0, le=100)
    payment_authorized: bool = False
    user_approved: bool = False


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


@app.get("/api/health")
def health() -> dict[str, Any]:
    model_status = model_runtime_status()
    return {
        "ok": True,
        "service": "evarian-travel-os",
        "database": str(DB_PATH),
        **model_status,
        "time": utc_now(),
    }


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
