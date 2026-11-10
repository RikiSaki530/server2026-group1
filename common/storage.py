"""Shared Elasticsearch schema and HTTP transport; no credentials in browser code."""
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

DEMO = os.getenv("DEMO_MODE", "false").lower() == "true"
INDEX = "temperature-demo-v1" if DEMO else "temperature-readings-v1"
STATUS_INDEX = "temperature-collector-status-v1"
ES_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200").rstrip("/")
METRICS = ("temperature", "humidity", "illumination")


def request_json(url, method="GET", body=None, headers=None):
    data = None if body is None else json.dumps(body, allow_nan=False).encode()
    req = Request(url, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    with urlopen(req, timeout=25) as response:
        raw = response.read()
        return json.loads(raw) if raw else {}


def es(path, method="GET", body=None):
    return request_json(f"{ES_URL}/{path.lstrip('/')}", method, body)


def ensure_indices():
    properties = {
        "@timestamp": {"type": "date"},
        "device_id": {"type": "keyword"},
        "device_name": {"type": "keyword"},
        "source": {"type": "keyword"},
        "motion_detected_at": {"type": "date"},
        **{name: {"type": "float"} for name in METRICS},
        **{f"{name}_updated_at": {"type": "date"} for name in METRICS},
    }
    for name, mapping in ((INDEX, {"dynamic": "strict", "properties": properties}),
                          (STATUS_INDEX, {"properties": {"last_attempt": {"type": "date"}, "last_success": {"type": "date"}, "error": {"type": "keyword"}}})):
        try:
            es(name, "PUT", {"settings": {"number_of_shards": 1, "number_of_replicas": 0}, "mappings": mapping})
        except HTTPError as exc:
            payload = json.loads(exc.read())
            if exc.code != 400 or payload.get("error", {}).get("type") != "resource_already_exists_exception":
                raise


def save_reading(reading):
    from hashlib import sha256
    # Retrying one sample overwrites it rather than creating duplicate measurements.
    key = sha256(f"{reading['device_id']}:{reading['@timestamp']}".encode()).hexdigest()
    es(f"{INDEX}/_doc/{key}", "PUT", reading)
