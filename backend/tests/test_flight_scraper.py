import unittest

from services.browser_scrapers import _parse_google_flight_card


class GoogleFlightCardTests(unittest.TestCase):
    source_url = "https://www.google.com/travel/flights?q=sample"

    def test_parses_indian_rupee_accessible_label(self):
        # fixture mirrors the text google puts on a flight result card
        label = (
            "From 6,522 Indian rupees. with Air India Express. "
            "Leaves Kochi at 10:25 AM and arrives Bengaluru at 11:35 AM. "
            "Total duration 1 hr 10 min. Nonstop."
        )

        result = _parse_google_flight_card(label, self.source_url)

        self.assertIsNotNone(result)
        self.assertEqual(result.provider, "Air India Express")
        self.assertEqual(result.price, 6522)
        self.assertEqual(result.duration_minutes, 70)
        self.assertEqual(result.transfers, 0)

    def test_parses_rupee_symbol_and_stop_count(self):
        label = (
            "From ₹8,100. with IndiGo. Leaves Kochi at 8:00 AM and arrives Delhi at 1:05 PM. "
            "Total duration 5 hr 5 min. 1 stop."
        )

        result = _parse_google_flight_card(label, self.source_url)

        self.assertIsNotNone(result)
        self.assertEqual(result.provider, "IndiGo")
        self.assertEqual(result.price, 8100)
        self.assertEqual(result.duration_minutes, 305)
        self.assertEqual(result.transfers, 1)

    def test_rejects_a_label_without_a_fare_or_duration(self):
        # incomplete cards should not become results with invented values
        result = _parse_google_flight_card("with IndiGo. Nonstop.", self.source_url)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
