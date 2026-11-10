"""Run after startup: docker compose exec -T backend python - < tests/smoke.py"""
import json
from urllib.error import HTTPError
from urllib.request import urlopen

for period in ("30m", "1h", "1d", "1w"):
    with urlopen(f"http://localhost:8000/dashboard?period={period}") as response:
        data = json.load(response)
    assert data["period"] == period
    assert isinstance(data["devices"], list)
    assert data["collection_interval_seconds"] >= 60
    for device in data["devices"]:
        assert device["id"]
        times = [p["timestamp"] for p in device["history"]]
        assert times == sorted(times)
        assert all(set(p) == {"timestamp", "temperature", "humidity", "illumination"} for p in device["history"])
    print(period, "OK", len(data["devices"]), "devices")
try:
    urlopen("http://localhost:8000/dashboard?period=invalid")
    raise AssertionError("Invalid period must be rejected")
except HTTPError as exc:
    assert exc.code == 422
print("Invalid period rejected: OK")
