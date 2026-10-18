import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


class PricingTests(unittest.TestCase):
    def test_default_pricing_anchors(self):
        result = app.pricing_anchors({})
        # ((3 + 5) * 700 + 500) * 1.10 = 6,710 -> nearest hundred = 6,700
        self.assertEqual(result["base_estimate_inr"], 6700)
        self.assertEqual(result["anchors"]["Starter"], 5000)
        self.assertEqual(result["anchors"]["Standard"], 6700)
        self.assertEqual(result["anchors"]["Premium"], 9700)

    def test_negative_inputs_are_clamped(self):
        result = app.pricing_anchors({"shoot_hours": -3, "edit_hours": -5, "hourly_rate": -700, "expenses": -500})
        self.assertEqual(result["base_estimate_inr"], 0)

    def test_input_validation_trims_and_caps(self):
        payload = app.validate_payload({"client": "  Cafe  ", "brief": "   Need a short product video for launch   ", "hourly_rate": "750"})
        self.assertEqual(payload["client"], "Cafe")
        self.assertEqual(payload["hourly_rate"], 750)
        self.assertEqual(payload["project_type"], "Social media video")

    def test_short_brief_is_rejected(self):
        with self.assertRaises(ValueError):
            app.validate_payload({"brief": "too short", "client": "Cafe"})

    def test_nonfinite_is_defaulted(self):
        self.assertEqual(app.clamp_number(float("nan"), 0, 100, 10), 10)


if __name__ == "__main__":
    unittest.main()
