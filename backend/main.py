import os
from threading import Lock
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError
from typing import Literal
from collections import defaultdict

from pydantic import BaseModel, Field

from fastapi import FastAPI, HTTPException, Query
from collector.main import collect_once, record_failure
from common.storage import DEMO, INDEX, METRICS, STATUS_INDEX, ensure_indices, es

PERIODS = {"30m": (30, "5m"), "1h": (60, "5m"), "1d": (1440, "5m"), "1w": (10080, "1h")}


@asynccontextmanager
async def lifespan(app):
    # Startup fails visibly if schema initialization fails.
    ensure_indices()
    yield


app = FastAPI(title="Temperature Temple API", lifespan=lifespan)
manual_collection_lock = Lock()


@app.post("/collect")
def collect_now():
    if not manual_collection_lock.acquire(blocking=False):
        raise HTTPException(409, "データを取得中です。完了するまでお待ちください。")
    try:
        return collect_once()
    except Exception as exc:
        record_failure(exc)
        if isinstance(exc, HTTPError) and exc.code == 429:
            raise HTTPException(429, "Nature Remo の取得回数制限に達しました。時間をおいて再試行してください。", headers={"Retry-After": "60"})
        raise HTTPException(503, "Nature Remo のデータ取得・保存に失敗しました。トークンと接続状態を確認してください。")
    finally:
        manual_collection_lock.release()


@app.get("/health")
def health():
    try:
        es("_cluster/health")
        return {"status": "ok"}
    except Exception:
        raise HTTPException(503, "Elasticsearch に接続できません。")


def dashboard_query(period, now, start_date=None, end_date=None):
    minutes, interval = PERIODS[period]
    start = now - timedelta(minutes=minutes)
    end = now
    end_operator = "lte"
    if start_date is not None and end_date is not None:
        jst = timezone(timedelta(hours=9))
        start = datetime.combine(start_date, datetime.min.time(), jst)
        end = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), jst)
        days = (end_date - start_date).days + 1
        interval = "5m" if days == 1 else "1h" if days <= 7 else "3h" if days <= 31 else "1d"
        end_operator = "lt"
    last_bucket = end - timedelta(milliseconds=1) if end_operator == "lt" else end
    return {"size": 0, "query": {"range": {"@timestamp": {"gte": start.isoformat(), end_operator: end.isoformat()}}},
            "aggs": {"devices": {"terms": {"field": "device_id", "size": 100}, "aggs": {
                "latest": {"top_hits": {"size": 1, "sort": [{"@timestamp": "desc"}]}},
                "history": {"date_histogram": {"field": "@timestamp", "fixed_interval": interval, "min_doc_count": 0,
                    "time_zone": "+09:00", "extended_bounds": {"min": start.isoformat(), "max": last_bucket.isoformat()}},
                    "aggs": {metric: {"avg": {"field": metric}} for metric in METRICS}}}}}}


def connection_status(reading, now, collection_failed=False):
    if reading.get("source") == "demo":
        return "demo"
    if collection_failed or not isinstance(reading.get("online"), bool):
        return "unknown"
    sampled = datetime.fromisoformat(reading["@timestamp"].replace("Z", "+00:00"))
    if not 0 <= (now - sampled).total_seconds() <= 900:
        return "unknown"
    return "online" if reading["online"] else "offline"


def validate_dates(start, end):
    today = datetime.now(timezone(timedelta(hours=9))).date()
    if (start is not None or end is not None) and (
        start is None or end is None or not start <= end <= today or (end - start).days >= 366
    ):
        raise HTTPException(400, "表示期間は日本時間の今日までの366日以内で指定してください。")


class CsvExportRequest(BaseModel):
    mode: Literal["hourly", "raw"]
    period: Literal["30m", "1h", "1d", "1w"] = "1d"
    start: date | None = None
    end: date | None = None
    device_ids: list[str] = Field(min_length=1, max_length=100)


def export_readings(filters):
    scroll_id = None
    try:
        page = es(f"{INDEX}/_search?scroll=1m", "POST", {
            "size": 2000,
            "sort": [{"@timestamp": "desc"}],
            "_source": ["@timestamp", "device_id", "device_name", *METRICS],
            "query": {"bool": {"filter": filters}},
        })
        while True:
            scroll_id = page["_scroll_id"]
            hits = page["hits"]["hits"]
            if not hits:
                break
            for hit in hits:
                yield hit["_source"]
            page = es("_search/scroll", "POST", {"scroll_id": scroll_id, "scroll": "1m"})
    finally:
        if scroll_id:
            try:
                es("_search/scroll", "DELETE", {"scroll_id": [scroll_id]})
            except Exception:
                pass  # Elasticsearch expires the search context automatically.


def export_rows(readings, mode):
    jst = timezone(timedelta(hours=9))
    hourly = defaultdict(lambda: [[0.0, 0] for _ in METRICS])
    names = {}
    rows = []
    for reading in readings:
        timestamp = datetime.fromisoformat(reading["@timestamp"]).astimezone(jst)
        name = reading["device_name"]
        values = [reading.get(metric) for metric in METRICS]
        if mode == "raw":
            rows.append([timestamp.strftime("%Y/%m/%d %H:%M:%S"), name, *values])
            continue
        if all(value is None for value in values):
            continue
        hour = timestamp.replace(minute=0, second=0, microsecond=0)
        key = (hour, reading["device_id"])
        names.setdefault(key, name)
        for total, value in zip(hourly[key], values):
            if value is not None:
                total[0] += value
                total[1] += 1

    for key, metrics in hourly.items():
        averages = [round(total / count, 3) if count else None for total, count in metrics]
        rows.append([key[0].strftime("%Y/%m/%d %H:%M:%S"), names[key], *averages])
    return rows


@app.post("/export")
def export_csv(request: CsvExportRequest):
    validate_dates(request.start, request.end)
    now = datetime.now(timezone.utc)
    query = dashboard_query(request.period, now, request.start, request.end)["query"]
    filters = [query, {"terms": {"device_id": request.device_ids}}]
    try:
        return export_rows(export_readings(filters), request.mode)
    except Exception:
        raise HTTPException(503, "CSV用の測定データを取得できません。")


@app.get("/dashboard")
def dashboard(period: str = Query("1d", pattern="^(30m|1h|1d|1w)$"),
              start: date | None = None, end: date | None = None):
    validate_dates(start, end)
    try:
        now = datetime.now(timezone.utc)
        latest = es(f"{INDEX}/_search", "POST", {"size": 0, "aggs": {"devices": {
            "terms": {"field": "device_id", "size": 100}, "aggs": {"latest": {"top_hits": {"size": 1, "sort": [{"@timestamp": "desc"}]}}}}}})
        history = es(f"{INDEX}/_search", "POST", dashboard_query(period, now, start, end))
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
        for device in devices:
            reading = device["latest"]
            device["connection_status"] = connection_status(reading, now, bool(status.get("error")))
            device["connection_checked_at"] = reading["@timestamp"] if isinstance(reading.get("online"), bool) else None
        return {"devices": sorted(devices, key=lambda d: d["name"]), "collector": status, "demo": DEMO,
                "period": period, "collection_interval_seconds": int(os.getenv("COLLECTION_INTERVAL_SECONDS", "300")), "generated_at": now.isoformat()}
    except Exception:
        raise HTTPException(503, "測定データを取得できません。Elasticsearch と Collector のログを確認してください。")
