import unittest
from datetime import datetime, timedelta, timezone
from backend.main import connection_status
from collector.main import normalize_device


class ConnectionStatusTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 12, tzinfo=timezone.utc)
        self.reading = {'@timestamp': self.now.isoformat(), 'source': 'nature_remo', 'online': True}

    def test_online_and_offline_follow_api_flag(self):
        self.assertEqual(connection_status(self.reading, self.now), 'online')
        self.reading['online'] = False
        self.assertEqual(connection_status(self.reading, self.now), 'offline')

    def test_old_and_future_confirmation_are_unknown(self):
        self.assertEqual(connection_status(self.reading, self.now + timedelta(minutes=16)), 'unknown')
        self.assertEqual(connection_status(self.reading, self.now - timedelta(minutes=1)), 'unknown')

    def test_api_failure_is_not_device_offline(self):
        self.assertEqual(connection_status(self.reading, self.now, True), 'unknown')

    def test_legacy_and_missing_flag_are_unknown(self):
        for value in (None, 'true', 1):
            self.reading['online'] = value
            self.assertEqual(connection_status(self.reading, self.now), 'unknown')

    def test_demo_is_not_reported_online(self):
        self.reading['source'] = 'demo'
        self.assertEqual(connection_status(self.reading, self.now), 'demo')

    def test_normalization_keeps_boolean_only(self):
        for value in (True, False):
            self.assertIs(normalize_device({'id': 'one', 'online': value}, self.now)['online'], value)
        for value in ('false', None, 0):
            self.assertNotIn('online', normalize_device({'id': 'one', 'online': value}, self.now))
