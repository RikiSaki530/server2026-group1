"""Poll all Nature Remo devices. Sensor timestamps are distinct from poll time."""
import logging
import math
import os
import signal
import threading
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError

from common.storage import DEMO, INDEX, STATUS_INDEX, ensure_indices, es, request_json, save_reading

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
stop = threading.Event()


def iso(value):
    return value.isoformat().replace("+00:00", "Z")


def normalize_device(device, collected_at):
    events = device.get("newest_events", {})
    reading = {"@timestamp": iso(collected_at), "device_id": device["id"],
               "device_name": device.get("name") or device["id"], "source": "nature_remo"}
    if isinstance(device.get("online"), bool):
        reading["online"] = device["online"]
    for code, metric in (("te", "temperature"), ("hu", "humidity"), ("il", "illumination")):
        event = events.get(code) or {}
        val = event.get("val")
        if isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val):
            reading[metric] = val
            if event.get("created_at"):
                reading[f"{metric}_updated_at"] = event["created_at"]
    motion = events.get("mo") or {}
    if motion.get("created_at"):
        reading["motion_detected_at"] = motion["created_at"]
    return reading


def demo_readings(at):
    for i, name in enumerate(("研究室", "サーバー室", "実習室")):
        phase = at.timestamp() / 3600
        yield {"@timestamp": iso(at), "device_id": f"demo-{i}", "device_name": name, "source": "demo",
               "temperature": round(23 + i + 1.6 * math.sin(phase / 4 + i), 1),
               "humidity": round(48 + i * 3 + 7 * math.cos(phase / 5 + i), 1),
               "illumination": round(max(0, 220 + 180 * math.sin(phase / 4 + i))),
               **{f"{m}_updated_at": iso(at) for m in ("temperature", "humidity", "illumination")},
               "motion_detected_at": iso(at - timedelta(minutes=i * 4))}


def collect_once():
    now = datetime.now(timezone.utc)
    if DEMO:
        readings = list(demo_readings(now))
    else:
        token = os.getenv("NATURE_TOKEN", "").strip()
        if not token:
            raise ValueError("NATURE_TOKEN が未設定です。.env にトークンを設定してください。")
        devices = request_json("https://api.nature.global/1/devices", headers={"Authorization": f"Bearer {token}"})
        if not isinstance(devices, list):
            raise ValueError("Nature Remo の応答形式が不正です。")
        readings = [normalize_device(d, now) for d in devices if d.get("id")]
    for reading in readings:
        save_reading(reading)
    # Visibility for the immediately following UI request, once per collection cycle.
    es(f"{INDEX}/_refresh", "POST")
    es(f"{STATUS_INDEX}/_doc/{INDEX}?refresh=true", "POST", {"last_attempt": iso(now), "last_success": iso(now), "error": "", "device_count": len(readings)})
    logging.info("Saved %s devices (%s)", len(readings), INDEX)
    return {"collected_at": iso(now), "device_count": len(readings)}


def record_failure(exc):
    if isinstance(exc, HTTPError):
        message = f"外部サービスの応答エラー (HTTP {exc.code})"
    elif isinstance(exc, ValueError):
        message = str(exc)
    else:
        message = f"接続または保存に失敗しました ({type(exc).__name__})"
    logging.error("%s", message)
    try:
        es(f"{STATUS_INDEX}/_update/{INDEX}?refresh=true", "POST", {"doc": {"last_attempt": iso(datetime.now(timezone.utc)), "error": message}, "doc_as_upsert": True})
    except Exception:
        logging.error("Failed to save collector status")


def seed_demo():
    # Seed only an empty, separate demo index; never write generated values as real data.
    if es(f"{INDEX}/_count")["count"]:
        return
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    for step in range(288, 0, -1):
        for reading in demo_readings(now - timedelta(minutes=step * 5)):
            save_reading(reading)
    es(f"{INDEX}/_refresh", "POST")


def main():
    interval = int(os.getenv("COLLECTION_INTERVAL_SECONDS", "300"))
    if interval < 60:
        raise ValueError("COLLECTION_INTERVAL_SECONDS must be at least 60")
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    while not stop.is_set():
        try:
            ensure_indices()
            if DEMO:
                seed_demo()
            break
        except Exception as exc:
            record_failure(exc)
            stop.wait(15)
    while not stop.is_set():
        try:
            collect_once()
        except Exception as exc:
            record_failure(exc)
        stop.wait(interval)


if __name__ == "__main__":
    main()
