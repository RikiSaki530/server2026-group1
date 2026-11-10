"""Idempotently create a Kibana data view for the active real/demo index."""
import os
import time
from urllib.error import HTTPError
from common.storage import INDEX, request_json

url = os.getenv("KIBANA_URL", "http://kibana:5601")
headers = {"kbn-xsrf": "temperature-setup"}
for attempt in range(120):
    try:
        request_json(f"{url}/api/status")
        break
    except Exception:
        time.sleep(5)
else:
    raise SystemExit("Kibana did not become ready within 10 minutes")

try:
    request_json(f"{url}/api/data_views/data_view/{INDEX}", headers=headers)
    print(f"Data view already exists: {INDEX}")
except HTTPError as exc:
    if exc.code != 404:
        raise
    request_json(f"{url}/api/data_views/data_view", "POST", {
        "data_view": {"id": INDEX, "title": INDEX, "name": "Temperature Temple" + (" (Demo)" if "demo" in INDEX else ""), "timeFieldName": "@timestamp", "allowNoIndex": True}}, headers=headers)
    print(f"Created Kibana data view: {INDEX}")
