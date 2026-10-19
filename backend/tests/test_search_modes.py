import unittest
from datetime import date
from unittest.mock import patch

import main
from models import Journey


class SearchModesTests(unittest.TestCase):
    def test_search_only_returns_train_and_flight_sources(self):
        train = Journey(
            mode="Train", provider="Example Rail", price=500,
            duration_minutes=180, transfers=0,
        )
        flight = Journey(
            mode="Flight", provider="Example Air", price=2500,
            duration_minutes=90, transfers=0,
        )
        with patch("main.scrape_train_with_status", return_value=([train], "ok")), patch(
            "main.scrape_flight_with_status", return_value=([flight], "ok")
        ):
            result = main.search(main.SearchRequest(
                origin="Kochi", destination="Bengaluru", travel_date=date(2026, 10, 21)
            ))

        self.assertEqual([item.mode for item in result["journeys"]], ["Train", "Flight"])
        self.assertEqual([source["name"] for source in result["sources"]], [
            "Indian Railways (eRail)", "Google Flights"
        ])

    def test_vercel_api_path_reaches_search_endpoint(self):
        train = Journey(
            mode="Train", provider="Example Rail", price=500,
            duration_minutes=180, transfers=0,
        )
        with patch("main.scrape_train_with_status", return_value=([train], "ok")), patch(
            "main.scrape_flight_with_status", return_value=([], "no flights")
        ):
            from fastapi.testclient import TestClient

            result = TestClient(main.app).post("/api/search", json={
                "origin": "Kochi",
                "destination": "Bengaluru",
                "travel_date": "2026-10-21",
            })

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["journeys"][0]["mode"], "Train")


if __name__ == "__main__":
    unittest.main()
