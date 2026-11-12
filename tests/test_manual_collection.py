import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from fastapi import HTTPException
from backend.main import collect_now, manual_collection_lock


class ManualCollectionTests(unittest.TestCase):
    @patch('backend.main.collect_once', return_value={'device_count': 3, 'collected_at': 'now'})
    def test_button_request_collects_and_returns_result(self, collect):
        self.assertEqual(collect_now()['device_count'], 3)
        collect.assert_called_once_with()
        self.assertFalse(manual_collection_lock.locked())

    @patch('backend.main.collect_once')
    def test_concurrent_request_is_rejected(self, collect):
        with manual_collection_lock:
            with self.assertRaises(HTTPException) as caught:
                collect_now()
        self.assertEqual(caught.exception.status_code, 409)
        collect.assert_not_called()

    @patch('backend.main.record_failure')
    @patch('backend.main.collect_once', side_effect=ValueError('secret'))
    def test_failure_reported_without_leaking_details_and_lock_released(self, collect, failure):
        with self.assertRaises(HTTPException) as caught:
            collect_now()
        self.assertEqual(caught.exception.status_code, 503)
        self.assertNotIn('secret', caught.exception.detail)
        failure.assert_called_once()
        self.assertFalse(manual_collection_lock.locked())

    @patch('backend.main.record_failure')
    @patch('backend.main.collect_once', side_effect=HTTPError('https://api.nature.global', 429, 'limit', {}, None))
    def test_rate_limit_is_reported(self, collect, failure):
        with self.assertRaises(HTTPException) as caught:
            collect_now()
        self.assertEqual(caught.exception.status_code, 429)
        self.assertEqual(caught.exception.headers['Retry-After'], '60')
        self.assertFalse(manual_collection_lock.locked())
