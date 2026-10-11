
import json
import math
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "telemetry.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    TELEMETRY = json.load(f)


class MetricsRequest(BaseModel):
    regions: list[str] = Field(min_length=1)
    threshold_ms: float


def percentile(values, q=0.95):
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (
        position - lower
    )


@app.post("/")
async def calculate_metrics(payload: MetricsRequest):
    # Keep your existing function body here
    results = {}

    for region in payload.regions:
        rows = [r for r in TELEMETRY if r["region"] == region]

        if not rows:
            results[region] = {
                "avg_latency": 0,
                "p95_latency": 0,
                "avg_uptime": 0,
                "breaches": 0,
            }
            continue

        latencies = [float(r["latency_ms"]) for r in rows]
        uptimes = [float(r["uptime_pct"]) for r in rows]

        results[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": percentile(latencies),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(
                value > payload.threshold_ms for value in latencies
            ),
        }

    return {"results": results}
