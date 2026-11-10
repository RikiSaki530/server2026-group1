import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from collector.main import collect_once, demo_readings, normalize_device, record_failure


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)

    def test_preserves_sensor_time_and_motion_detection_time(self):
        sensor_time = "2026-11-09T23:50:00Z"
        result = normalize_device({"id": "one", "name": "研究室", "newest_events": {
            "te": {"val": 24.1, "created_at": sensor_time},
            "hu": {"val": 0, "created_at": sensor_time},
            "mo": {"val": 1, "created_at": sensor_time},
        }}, self.now)
        self.assertEqual(result["@timestamp"], "2026-11-10T00:00:00Z")
        self.assertEqual(result["temperature_updated_at"], sensor_time)
        self.assertEqual(result["motion_detected_at"], sensor_time)
        self.assertEqual(result["humidity"], 0)
        self.assertNotIn("illumination", result)

    def test_missing_or_invalid_sensors_are_not_zero_measurements(self):
        result = normalize_device({"id": "mini", "newest_events": {
            "te": {"val": float("nan")}, "hu": {"val": True}, "il": None,
        }}, self.now)
        self.assertNotIn("temperature", result)
        self.assertNotIn("humidity", result)
        self.assertNotIn("illumination", result)
        self.assertNotIn("motion_detected_at", result)

    @patch("collector.main.DEMO", False)
    @patch.dict(os.environ, {"NATURE_TOKEN": "test-token"})
    @patch("collector.main.es")
    @patch("collector.main.save_reading")
    @patch("collector.main.request_json")
    def test_all_devices_saved_and_success_only_after_writes(self, request, save, es):
        request.return_value = [{"id": str(i), "newest_events": {"te": {"val": 20 + i}}} for i in range(3)]
        collect_once()
        self.assertEqual(save.call_count, 3)
        status = es.call_args.args[2]
        self.assertEqual(status["device_count"], 3)
        self.assertEqual(status["error"], "")
        self.assertIn("last_success", status)

    @patch("collector.main.DEMO", False)
    @patch.dict(os.environ, {"NATURE_TOKEN": ""})
    @patch("collector.main.request_json")
    def test_no_token_does_not_call_api(self, request):
        with self.assertRaisesRegex(ValueError, "NATURE_TOKEN"):
            collect_once()
        request.assert_not_called()

    @patch("collector.main.es")
    def test_failure_preserves_last_success(self, es):
        record_failure(ConnectionError("secret"))
        update = es.call_args.args[2]
        self.assertNotIn("last_success", update["doc"])
        self.assertNotIn("secret", update["doc"]["error"])

    def test_demo_is_explicitly_marked(self):
        readings = list(demo_readings(self.now))
        self.assertEqual(len(readings), 3)
        self.assertTrue(all(r["source"] == "demo" and r["device_id"].startswith("demo-") for r in readings))


if __name__ == "__main__":
    unittest.main()
