import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError

from fastapi import FastAPI, HTTPException, Query
from common.storage import DEMO, INDEX, METRICS, STATUS_INDEX, ensure_indices, es

PERIODS = {"30m": (30, "5m"), "1h": (60, "5m"), "1d": (1440, "5m"), "1w": (10080, "1h")}


@asynccontextmanager
async def lifespan(app):
    # Startup fails visibly if schema initialization fails.
    ensure_indices()
    yield


app = FastAPI(title="Temperature Temple API", lifespan=lifespan)


@app.get("/health")
def health():
    try:
        es("_cluster/health")
        return {"status": "ok"}
    except Exception:
        raise HTTPException(503, "Elasticsearch に接続できません。")


def dashboard_query(period, now):
    minutes, interval = PERIODS[period]
    start = now - timedelta(minutes=minutes)
    return {"size": 0, "query": {"range": {"@timestamp": {"gte": start.isoformat(), "lte": now.isoformat()}}},
            "aggs": {"devices": {"terms": {"field": "device_id", "size": 100}, "aggs": {
                "latest": {"top_hits": {"size": 1, "sort": [{"@timestamp": "desc"}]}},
                "history": {"date_histogram": {"field": "@timestamp", "fixed_interval": interval, "min_doc_count": 0,
                    "extended_bounds": {"min": start.isoformat(), "max": now.isoformat()}},
                    "aggs": {metric: {"avg": {"field": metric}} for metric in METRICS}}}}}}


@app.get("/dashboard")
def dashboard(period: str = Query("1d", pattern="^(30m|1h|1d|1w)$")):
    try:
        now = datetime.now(timezone.utc)
        latest = es(f"{INDEX}/_search", "POST", {"size": 0, "aggs": {"devices": {
            "terms": {"field": "device_id", "size": 100}, "aggs": {"latest": {"top_hits": {"size": 1, "sort": [{"@timestamp": "desc"}]}}}}}})
        history = es(f"{INDEX}/_search", "POST", dashboard_query(period, now))
        histories = {b["key"]: [{"timestamp": p["key_as_string"], **{metric: p[metric]["value"] for metric in METRICS}} for p in b["history"]["buckets"]]
                     for b in history["aggregations"]["devices"]["buckets"]}
        devices = []
        for b in latest["aggregations"]["devices"]["buckets"]:
            reading = b["latest"]["hits"]["hits"][0]["_source"]
            sampled = datetime.fromisoformat(reading["@timestamp"].replace("Z", "+00:00"))
            devices.append({"id": b["key"], "name": reading["device_name"], "latest": reading,
                            "stale": (now - sampled).total_seconds() > 900, "history": histories.get(b["key"], [])})
        try:
            status = es(f"{STATUS_INDEX}/_doc/{INDEX}")["_source"]
        except HTTPError as exc:
            if exc.code != 404:
                raise
            status = {"error": "初回のデータ収集を待っています。"}
        return {"devices": sorted(devices, key=lambda d: d["name"]), "collector": status, "demo": DEMO,
                "period": period, "collection_interval_seconds": int(os.getenv("COLLECTION_INTERVAL_SECONDS", "300")), "generated_at": now.isoformat()}
    except Exception:
        raise HTTPException(503, "測定データを取得できません。Elasticsearch と Collector のログを確認してください。")
