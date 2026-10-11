import json
import math
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="eShopCo Latency Metrics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "telemetry.json"
with DATA_PATH.open("r", encoding="utf-8") as f:
    TELEMETRY = json.load(f)


class MetricsRequest(BaseModel):
    regions: list[str] = Field(min_length=1)
    threshold_ms: float


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolated percentile (same convention as NumPy's default)."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


@app.post("/api")
async def calculate_metrics(payload: MetricsRequest):
    results = {}
    for region in payload.regions:
        rows = [row for row in TELEMETRY if row.get("region") == region]
        if not rows:
            results[region] = {
                "avg_latency": 0,
                "p95_latency": 0,
                "avg_uptime": 0,
                "breaches": 0,
            }
            continue

        latencies = [float(row["latency_ms"]) for row in rows]
        uptimes = [float(row["uptime_pct"]) for row in rows]
        results[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": percentile(latencies, 0.95),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(value > payload.threshold_ms for value in latencies),
        }

    return {"results": results}


@app.get("/")
async def health():
    return {"status": "ok", "endpoint": "/api", "method": "POST"}
