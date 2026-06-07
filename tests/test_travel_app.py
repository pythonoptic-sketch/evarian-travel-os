from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover - backend extra not installed
    TestClient = None


@unittest.skipIf(TestClient is None, "FastAPI backend dependencies are not installed")
class TravelAppTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.saved_env = {
            key: os.environ.get(key)
            for key in (
                "EVARIAN_MODEL_AGENTS_ENABLED",
                "EVARIAN_MODEL_PROVIDER",
                "OPENAI_API_KEY",
                "OPENAI_MODEL",
                "GEMINI_API_KEY",
                "GOOGLE_API_KEY",
                "GEMINI_MODEL",
                "AMADEUS_CLIENT_ID",
                "AMADEUS_CLIENT_SECRET",
                "AMADEUS_ENV",
                "AMADEUS_HOSTNAME",
                "AMADEUS_BASE_URL",
                "EVARIAN_SUPPLIER_SIDE_EFFECTS_ENABLED",
            )
        }
        os.environ["EVARIAN_DATABASE_PATH"] = str(Path(self.tmp.name) / "evarian.sqlite3")
        for key in self.saved_env:
            os.environ.pop(key, None)
        import backend.travel_app as travel_app

        self.travel_app = importlib.reload(travel_app)
        self.client = TestClient(self.travel_app.app)

    def tearDown(self) -> None:
        self.tmp.cleanup()
        os.environ.pop("EVARIAN_DATABASE_PATH", None)
        for key, value in self.saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_trip_control_order_permissions_and_events(self) -> None:
        created = self.client.post(
            "/api/trip-orders",
            json={
                "intent": "My flight is delayed. Recalculate pickup and ask before spend above $75.",
                "wallet_cap": 75,
                "risk_mode": "fast",
            },
        )

        self.assertEqual(created.status_code, 200)
        order = created.json()
        self.assertEqual(order["status"], "recovery_prepared")
        self.assertEqual(order["control_center"]["title"], "Live trip control center")
        self.assertEqual(order["permissions"]["level_label"], "prepare")
        self.assertEqual(order["manager"]["id"], "manager")
        self.assertFalse(order["manager"]["model_backed"])
        self.assertIn("recovery", [item["agent_id"] for item in order["delegation_plan"]])
        self.assertIn("verification", [item["agent_id"] for item in order["agent_outputs"]])
        self.assertTrue(order["autopilot"]["requires_approval"])

        fetched = self.client.get(f"/api/trip-orders/{order['id']}")
        self.assertEqual(fetched.status_code, 200)
        self.assertGreaterEqual(len(fetched.json()["events"]), 4)

        permissions = self.client.put(
            f"/api/trip-orders/{order['id']}/permissions",
            json={
                "autonomy_level": 3,
                "airport_ride_cap": 75,
                "auto_book_airport_rides": True,
            },
        )

        self.assertEqual(permissions.status_code, 200)
        self.assertEqual(permissions.json()["permissions"]["level_label"], "approve_execute")

        events = self.client.get(f"/api/trip-orders/{order['id']}/events")
        self.assertEqual(events.status_code, 200)
        self.assertGreaterEqual(len(events.json()["items"]), 5)

    def test_local_preview_cors_allows_agent_requests(self) -> None:
        for origin in ("null", "http://127.0.0.1:8080"):
            with self.subTest(origin=origin):
                response = self.client.options(
                    "/api/trip-orders",
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "content-type",
                    },
                )
                self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], origin)

    def test_manager_agent_delegates_new_trip_order(self) -> None:
        created = self.client.post(
            "/api/trip-orders",
            json={
                "intent": "I need to get from San Francisco to New York next Tuesday for a 10:00 AM investor meeting. Keep it within policy, avoid red-eyes, book airport transfer, and hold a hotel near SoHo.",
                "wallet_cap": 2200,
                "risk_mode": "balanced",
            },
        )

        self.assertEqual(created.status_code, 200)
        order = created.json()
        delegated = [item["agent_id"] for item in order["delegation_plan"]]
        self.assertEqual(order["route"], "San Francisco -> New York")
        self.assertIn("search", delegated)
        self.assertIn("pricing_watch", delegated)
        self.assertIn("points_rewards", delegated)
        self.assertIn("maps_location", delegated)
        self.assertIn("supplier_verification", delegated)
        self.assertIn("recommendation", delegated)
        self.assertIn("execution", delegated)
        self.assertEqual(order["agent_outputs"][0]["agent_id"], "manager")
        self.assertIn("agent_network", order)
        self.assertIn("governance", order)
        self.assertEqual(order["trip_intention"]["mode"], "business")
        self.assertIn("cash price", order["total_trip_value_score"]["dimensions"])
        self.assertIn("flight_optimization", order["scout_teams"])
        self.assertIn("travel_dna", order)
        self.assertIn("flight", order["source_plans"])
        self.assertIn("hotel", order["source_plans"])
        self.assertTrue(all("because" in product for product in order["products"]))
        self.assertIn("command-first traveler intent capture", order["extracted_requirements"])
        self.assertIn("trip intention detection before search", order["extracted_requirements"])
        self.assertIn(
            "total trip value optimization across price, points, comfort, time, taste, location, logistics, status, flexibility, and recovery risk",
            order["extracted_requirements"],
        )
        self.assertIn("recommendations must include because-rationale tied to user fit and evidence", order["extracted_requirements"])
        self.assertFalse(order["autopilot"]["can_auto_execute"])

    def test_health_reports_model_runtime_without_exposing_keys(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        health = response.json()
        self.assertFalse(health["model_agents_enabled"])
        self.assertEqual(health["model_provider"], "openai")
        self.assertFalse(health["model_key_configured"])
        self.assertFalse(health["gemini_key_configured"])
        self.assertEqual(health["gemini_model"], "gemini-3.5-flash")
        self.assertFalse(health["suppliers"]["amadeus"]["configured"])
        self.assertIn("flight_create_order", health["suppliers"]["amadeus"]["supported"])
        self.assertIn("hotel_create_booking", health["suppliers"]["amadeus"]["supported"])
        self.assertFalse(health["execution"]["side_effects_enabled"])
        self.assertFalse(health["suppliers"]["amadeus"]["client_id_configured"])
        self.assertFalse(health["suppliers"]["amadeus"]["client_secret_configured"])
        self.assertNotIn("api_key", health)
        self.assertNotIn("client_secret", health["suppliers"]["amadeus"])

    def test_amadeus_status_endpoint_is_credential_gated(self) -> None:
        response = self.client.get("/api/suppliers/amadeus/status")

        self.assertEqual(response.status_code, 200)
        status = response.json()
        self.assertFalse(status["configured"])
        self.assertEqual(status["environment"], "test")
        self.assertIn("flight_offers_search", status["supported"])
        self.assertIn("flight_offers_price", status["supported"])
        self.assertIn("hotel_offers_search", status["supported"])
        self.assertFalse(status["side_effects_enabled"])

    def test_amadeus_flight_offers_requires_credentials(self) -> None:
        response = self.client.post(
            "/api/suppliers/amadeus/flight-offers",
            json={
                "origin_location_code": "SFO",
                "destination_location_code": "JFK",
                "departure_date": "2026-07-15",
                "adults": 1,
                "max_results": 3,
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "amadeus credentials are not configured")

    def test_amadeus_hotel_search_requires_credentials(self) -> None:
        response = self.client.post(
            "/api/suppliers/amadeus/hotels/by-city",
            json={"city_code": "PAR", "radius": 20, "radius_unit": "KM"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "amadeus credentials are not configured")

    def test_policy_gate_blocks_irreversible_action_without_approval(self) -> None:
        created = self.client.post(
            "/api/trip-orders",
            json={
                "intent": "Book my airport transfer tomorrow morning under $75.",
                "wallet_cap": 75,
                "risk_mode": "balanced",
            },
        )
        self.assertEqual(created.status_code, 200)
        order = created.json()

        evaluation = self.client.post(
            f"/api/trip-orders/{order['id']}/actions/evaluate",
            json={
                "action_type": "book",
                "description": "Book black car airport transfer",
                "amount": 72,
                "refundable": True,
                "supplier_reliable": True,
                "within_supplier_terms": True,
                "model_confidence": 92,
                "payment_authorized": False,
                "user_approved": False,
            },
        )

        self.assertEqual(evaluation.status_code, 200)
        policy = evaluation.json()["policy"]
        self.assertFalse(policy["can_execute"])
        self.assertTrue(policy["requires_approval"])
        self.assertIn("payment_authority", policy["failed_gates"])
        self.assertIn("traveler_approval", policy["failed_gates"])

    def test_policy_gate_allows_low_risk_search_preparation(self) -> None:
        created = self.client.post(
            "/api/trip-orders",
            json={
                "intent": "Find a quiet hotel near SoHo for next Tuesday.",
                "wallet_cap": 500,
                "risk_mode": "balanced",
            },
        )
        self.assertEqual(created.status_code, 200)
        order = created.json()

        evaluation = self.client.post(
            f"/api/trip-orders/{order['id']}/actions/evaluate",
            json={
                "action_type": "search",
                "description": "Search hotel candidates",
                "amount": 0,
                "supplier_reliable": True,
                "within_supplier_terms": True,
                "model_confidence": 90,
            },
        )

        self.assertEqual(evaluation.status_code, 200)
        policy = evaluation.json()["policy"]
        self.assertEqual(policy["decision"], "prepare")
        self.assertFalse(policy["can_execute"])
        self.assertFalse(policy["requires_approval"])

    def test_policy_gate_requires_hotel_ranking_evidence(self) -> None:
        created = self.client.post(
            "/api/trip-orders",
            json={
                "intent": "Find a quiet hotel near SoHo for next Tuesday.",
                "wallet_cap": 500,
                "risk_mode": "balanced",
            },
        )
        self.assertEqual(created.status_code, 200)
        order = created.json()

        missing_evidence = self.client.post(
            f"/api/trip-orders/{order['id']}/actions/evaluate",
            json={
                "action_type": "rank",
                "service_type": "hotel",
                "description": "Rank hotel candidates",
                "supplier_reliable": True,
                "within_supplier_terms": True,
                "model_confidence": 91,
            },
        )
        self.assertEqual(missing_evidence.status_code, 200)
        policy = missing_evidence.json()["policy"]
        self.assertEqual(policy["decision"], "research_required")
        self.assertIn("traveler_profile", policy["failed_gates"])
        self.assertIn("because_rationale", policy["failed_gates"])
        self.assertIn("source_comparison", policy["failed_gates"])
        self.assertIn("maps_location", policy["failed_gates"])

        complete_evidence = self.client.post(
            f"/api/trip-orders/{order['id']}/actions/evaluate",
            json={
                "action_type": "rank",
                "service_type": "hotel",
                "description": "Rank hotel candidates",
                "supplier_reliable": True,
                "within_supplier_terms": True,
                "model_confidence": 91,
                "because": "This hotel set fits the traveler because it balances SoHo access, room quality, refundability, and price.",
                "source_count": 3,
                "maps_verified": True,
                "traveler_profile_applied": True,
            },
        )
        self.assertEqual(complete_evidence.status_code, 200)
        policy = complete_evidence.json()["policy"]
        self.assertEqual(policy["decision"], "prepare")
        self.assertNotIn("because_rationale", policy["failed_gates"])
        self.assertNotIn("source_comparison", policy["failed_gates"])
        self.assertNotIn("maps_location", policy["failed_gates"])

    def test_policy_gate_requires_points_for_long_flight_hold(self) -> None:
        created = self.client.post(
            "/api/trip-orders",
            json={
                "intent": "Hold a business class option from Los Angeles to Paris next Friday if the points value is good.",
                "wallet_cap": 2000,
                "risk_mode": "balanced",
            },
        )
        self.assertEqual(created.status_code, 200)
        order = created.json()

        evaluation = self.client.post(
            f"/api/trip-orders/{order['id']}/actions/evaluate",
            json={
                "action_type": "hold",
                "service_type": "flight",
                "description": "Hold a long-haul business class flight",
                "amount": 0,
                "refundable": True,
                "supplier_reliable": True,
                "within_supplier_terms": True,
                "model_confidence": 93,
                "because": "This flight is recommended because it protects sleep, arrival timing, and business-class redemption value.",
                "source_count": 2,
                "direct_supplier_verified": True,
                "traveler_profile_applied": True,
                "duration_hours": 10,
                "premium_cabin": True,
            },
        )
        self.assertEqual(evaluation.status_code, 200)
        policy = evaluation.json()["policy"]
        self.assertEqual(policy["decision"], "research_required")
        self.assertIn("points_rewards", policy["failed_gates"])

        with_points = self.client.post(
            f"/api/trip-orders/{order['id']}/actions/evaluate",
            json={
                "action_type": "hold",
                "service_type": "flight",
                "description": "Hold a long-haul business class flight",
                "amount": 0,
                "refundable": True,
                "supplier_reliable": True,
                "within_supplier_terms": True,
                "model_confidence": 93,
                "because": "This flight is recommended because it protects sleep, arrival timing, and business-class redemption value.",
                "source_count": 2,
                "direct_supplier_verified": True,
                "traveler_profile_applied": True,
                "duration_hours": 10,
                "premium_cabin": True,
                "points_checked": True,
            },
        )
        self.assertEqual(with_points.status_code, 200)
        policy = with_points.json()["policy"]
        self.assertEqual(policy["decision"], "hold")
        self.assertNotIn("points_rewards", policy["failed_gates"])

    def test_scoped_autopilot_can_authorize_airport_ride_under_cap(self) -> None:
        created = self.client.post(
            "/api/trip-orders",
            json={
                "intent": "Book my airport transfer tomorrow morning under $85.",
                "wallet_cap": 85,
                "risk_mode": "balanced",
            },
        )
        self.assertEqual(created.status_code, 200)
        order = created.json()

        permissions = self.client.put(
            f"/api/trip-orders/{order['id']}/permissions",
            json={
                "autonomy_level": 4,
                "airport_ride_cap": 85,
                "auto_book_airport_rides": True,
                "use_card_backup_under_cap": True,
            },
        )
        self.assertEqual(permissions.status_code, 200)

        evaluation = self.client.post(
            f"/api/trip-orders/{order['id']}/actions/evaluate",
            json={
                "action_type": "book",
                "service_type": "airport_ride",
                "description": "Book airport transfer",
                "amount": 82,
                "refundable": True,
                "supplier_reliable": True,
                "within_supplier_terms": True,
                "model_confidence": 93,
                "payment_authorized": True,
                "user_approved": False,
                "because": "This airport transfer fits because it is under the approved cap, matches flight timing, and has verified pickup logistics.",
                "source_count": 1,
                "maps_verified": True,
                "logistics_verified": True,
                "traveler_profile_applied": True,
            },
        )

        self.assertEqual(evaluation.status_code, 200)
        policy = evaluation.json()["policy"]
        self.assertEqual(policy["decision"], "execution_allowed")
        self.assertTrue(policy["can_execute"])
        self.assertTrue(policy["autopilot_preapproved"])
        self.assertNotIn("traveler_approval", policy["failed_gates"])

    def test_stage_supplier_action_persists_policy_and_payload(self) -> None:
        created = self.client.post(
            "/api/trip-orders",
            json={
                "intent": "Book a flight from SFO to JFK next Tuesday after I approve the final fare.",
                "wallet_cap": 1200,
                "risk_mode": "balanced",
            },
        )
        self.assertEqual(created.status_code, 200)
        order = created.json()

        staged = self.client.post(
            f"/api/trip-orders/{order['id']}/supplier-actions",
            json={
                "supplier": "amadeus",
                "proposed_action": {
                    "action_type": "book",
                    "service_type": "flight",
                    "description": "Create Amadeus flight order after final fare confirmation",
                    "amount": 640,
                    "refundable": True,
                    "supplier_reliable": True,
                    "within_supplier_terms": True,
                    "model_confidence": 92,
                    "payment_authorized": True,
                    "user_approved": True,
                    "because": "This flight fits because the final fare was checked directly, it matches the requested route, and the traveler approved the charge.",
                    "source_count": 3,
                    "direct_supplier_verified": True,
                    "points_checked": True,
                    "price_history_checked": True,
                    "credit_card_fit_checked": True,
                    "traveler_profile_applied": True,
                },
                "execution_payload": {
                    "flight_offers": [{"type": "flight-offer", "id": "1"}],
                    "travelers": [{"id": "1", "dateOfBirth": "1990-01-01", "name": {"firstName": "ALEX", "lastName": "TRAVELER"}}],
                },
            },
        )

        self.assertEqual(staged.status_code, 200)
        action = staged.json()["action"]
        self.assertEqual(action["status"], "ready")
        self.assertEqual(action["supplier"], "amadeus")
        self.assertEqual(action["service_type"], "flight")
        self.assertTrue(action["policy"]["can_execute"])
        self.assertEqual(action["execution_payload"]["flight_offers"][0]["id"], "1")

        listed = self.client.get(f"/api/trip-orders/{order['id']}/supplier-actions")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["items"]), 1)

    def test_execute_supplier_action_is_blocked_until_side_effects_enabled(self) -> None:
        created = self.client.post(
            "/api/trip-orders",
            json={
                "intent": "Book a refundable hotel after I approve the rate.",
                "wallet_cap": 900,
                "risk_mode": "balanced",
            },
        )
        self.assertEqual(created.status_code, 200)
        order = created.json()

        staged = self.client.post(
            f"/api/trip-orders/{order['id']}/supplier-actions",
            json={
                "supplier": "amadeus",
                "proposed_action": {
                    "action_type": "book",
                    "service_type": "hotel",
                    "description": "Create Amadeus hotel booking",
                    "amount": 420,
                    "refundable": True,
                    "supplier_reliable": True,
                    "within_supplier_terms": True,
                    "model_confidence": 94,
                    "payment_authorized": True,
                    "user_approved": True,
                    "because": "This hotel fits because the room offer was verified directly, the location works, and the traveler approved the rate.",
                    "source_count": 3,
                    "direct_supplier_verified": True,
                    "maps_verified": True,
                    "price_history_checked": True,
                    "credit_card_fit_checked": True,
                    "traveler_profile_applied": True,
                },
                "execution_payload": {
                    "booking_data": {
                        "offerId": "ABC123",
                        "guests": [{"id": 1, "name": {"title": "MR", "firstName": "ALEX", "lastName": "TRAVELER"}}],
                        "payments": [{"id": 1, "method": "creditCard", "card": {"vendorCode": "VI"}}],
                    }
                },
            },
        )
        self.assertEqual(staged.status_code, 200)
        action_id = staged.json()["action"]["id"]

        executed = self.client.post(
            f"/api/trip-orders/{order['id']}/supplier-actions/{action_id}/execute",
            json={"user_approved": True, "payment_authorized": True},
        )

        self.assertEqual(executed.status_code, 200)
        payload = executed.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["response"]["status"], "blocked")
        self.assertEqual(payload["response"]["required_env"], "EVARIAN_SUPPLIER_SIDE_EFFECTS_ENABLED=true")
        self.assertEqual(payload["action"]["status"], "blocked")

    def test_execute_supplier_action_supports_dry_run(self) -> None:
        created = self.client.post(
            "/api/trip-orders",
            json={
                "intent": "Book a refundable flight after I approve the final fare.",
                "wallet_cap": 1200,
                "risk_mode": "balanced",
            },
        )
        self.assertEqual(created.status_code, 200)
        order = created.json()

        staged = self.client.post(
            f"/api/trip-orders/{order['id']}/supplier-actions",
            json={
                "supplier": "amadeus",
                "proposed_action": {
                    "action_type": "book",
                    "service_type": "flight",
                    "description": "Dry run Amadeus flight order",
                    "amount": 640,
                    "refundable": True,
                    "supplier_reliable": True,
                    "within_supplier_terms": True,
                    "model_confidence": 92,
                    "payment_authorized": True,
                    "user_approved": True,
                    "because": "This flight fits because the fare was verified directly, the itinerary matches, and the traveler approved it.",
                    "source_count": 3,
                    "direct_supplier_verified": True,
                    "points_checked": True,
                    "price_history_checked": True,
                    "credit_card_fit_checked": True,
                    "traveler_profile_applied": True,
                },
                "execution_payload": {
                    "flight_offers": [{"type": "flight-offer", "id": "1"}],
                    "travelers": [{"id": "1", "dateOfBirth": "1990-01-01", "name": {"firstName": "ALEX", "lastName": "TRAVELER"}}],
                },
            },
        )
        self.assertEqual(staged.status_code, 200)
        action_id = staged.json()["action"]["id"]

        executed = self.client.post(
            f"/api/trip-orders/{order['id']}/supplier-actions/{action_id}/execute",
            json={"user_approved": True, "payment_authorized": True, "dry_run": True},
        )

        self.assertEqual(executed.status_code, 200)
        payload = executed.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["response"]["status"], "dry_run")
        self.assertEqual(payload["action"]["status"], "dry_run")


if __name__ == "__main__":
    unittest.main()
