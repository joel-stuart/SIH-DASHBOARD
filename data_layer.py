"""
data_layer.py — MineWatch data abstraction layer
"""

from __future__ import annotations

import os
import math
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from esp32_connection import get_latest_node_data


RAW_FEATURE_NAMES = [
    "ax_g", "ay_g", "az_g",
    "gx_dps", "gy_dps", "gz_dps",
    "pitch_deg", "roll_deg",
    "vibration_intensity", "temp_c",
]

FEATURE_LABEL_MAP = {
    "pitch_deg": "Pitch",
    "roll_deg": "Roll",
    "vibration_intensity": "Vibration",
    "temp_c": "Temperature",
}

NODE_IDS = ["N01", "N02", "N03", "N04", "N05", "N06"]

NODE_POSITIONS = {
    "N01": (34.2, 23.0),
    "N02": (50.8, 16.0),
    "N03": (34.2, 77.0),
    "N04": (70.0, 50.0),
    "N05": (50.8, 84.0),
    "N06": (84.2, 38.0),
}

NODE_LOCATION_LABEL = {
    "N01": "Level 1 — NW gallery",
    "N02": "Level 2 — W gallery",
    "N03": "Level 1 — NE gallery",
    "N04": "Level 3 — central chamber (LoRa Receiver Hub)",
    "N05": "Level 2 — E gallery",
    "N06": "Level 4 — lower gallery",
}

ACTIVE_NODES = ["N04"]

DEMO_SEVERITY = {
    "N04": "Critical",
}

# Live-mode switch — set to True when testing with hardware
LIVE_MODE = os.environ.get("MINEWATCH_LIVE", "1") == "1"

STALE_TIMEOUT_SECONDS = 30
RISK_THRESHOLDS = {"Warning": 35, "Critical": 80}


@dataclass
class NodeReading:
    node_id: str
    timestamp: datetime
    active: bool
    online: bool
    status: str

    pitch: float = 0.0
    roll: float = 0.0
    vibration: float = 0.0
    temperature: float = 0.0

    risk: int = 0
    displacement: float = 0.0
    crack: float = 0.0
    anomaly: bool = False

    signal: int = 0
    health: int = 0

    location_label: str = ""
    stale: bool = False
    stage_label: str = ""
    alert_level: str = ""
    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp.isoformat(timespec="seconds"),
            "active": self.active,
            "online": self.online,
            "status": self.status,
            "pitch": round(self.pitch, 2),
            "roll": round(self.roll, 2),
            "vibration": round(self.vibration, 2),
            "temperature": round(self.temperature, 1),
            "risk": int(self.risk),
            "displacement": round(self.displacement, 1),
            "crack": round(self.crack, 2),
            "anomaly": self.anomaly,
            "signal": int(self.signal),
            "health": int(self.health),
            "location_label": self.location_label,
            "stale": self.stale,
            "stage_label": self.stage_label,
            "alert_level": self.alert_level,
        }


def classify_status(risk: int, online: bool) -> str:
    if not online:
        return "Offline"
    if risk >= RISK_THRESHOLDS["Critical"]:
        return "Critical"
    if risk >= RISK_THRESHOLDS["Warning"]:
        return "Warning"
    return "Normal"


def _offline_reading(node_id: str, now: datetime) -> NodeReading:
    return NodeReading(
        node_id=node_id,
        timestamp=now,
        active=node_id in ACTIVE_NODES,
        online=False,
        status="Offline",
        pitch=0.0, roll=0.0, vibration=0.0, temperature=0.0,
        risk=0, displacement=0.0, crack=0.0, anomaly=False,
        signal=0, health=0,
        location_label=NODE_LOCATION_LABEL.get(node_id, ""),
        stale=True,
    )


_rng = random.Random(42)


def _demo_reading_for_active_node(node_id: str, now: datetime, tick: int) -> NodeReading:
    severity = DEMO_SEVERITY.get(node_id, "Normal")
    phase = hash(node_id) % 360
    wave = math.sin(math.radians(tick * 6 + phase))

    if severity == "Critical":
        base_risk, risk_span = 70, 18
        pitch_base, roll_base = 4.4, 2.6
        vib_base, temp_base = 1.05, 34.0
    elif severity == "Warning":
        base_risk, risk_span = 42, 14
        pitch_base, roll_base = 2.6, 1.4
        vib_base, temp_base = 0.55, 30.5
    else:
        base_risk, risk_span = 16, 10
        pitch_base, roll_base = 0.8, 0.5
        vib_base, temp_base = 0.18, 26.0

    noise = _rng.uniform(-1, 1)
    risk = int(max(2, min(99, base_risk + wave * risk_span + noise * 3)))
    pitch = round(pitch_base + wave * 0.6 + _rng.uniform(-0.15, 0.15), 2)
    roll = round(roll_base + wave * 0.4 + _rng.uniform(-0.1, 0.1), 2)
    vibration = round(max(0.02, vib_base + wave * 0.12 + _rng.uniform(-0.03, 0.03)), 2)
    temperature = round(temp_base + wave * 1.2 + _rng.uniform(-0.3, 0.3), 1)
    displacement = round(max(0, (risk / 100) * 32 + _rng.uniform(-1, 1)), 1)
    crack = round(max(0, (risk / 100) * 3.4 + _rng.uniform(-0.1, 0.1)), 2)
    anomaly = risk >= RISK_THRESHOLDS["Critical"] and wave > 0.5

    return NodeReading(
        node_id=node_id,
        timestamp=now,
        active=True,
        online=True,
        status=classify_status(risk, online=True),
        pitch=pitch, roll=roll, vibration=vibration, temperature=temperature,
        risk=risk, displacement=displacement, crack=crack, anomaly=anomaly,
        signal=int(max(60, 96 - risk * 0.25 + _rng.uniform(-3, 3))),
        health=int(max(55, 100 - risk * 0.35 + _rng.uniform(-2, 2))),
        location_label=NODE_LOCATION_LABEL.get(node_id, ""),
        stale=False,
    )


def get_demo_data(tick: int = 0) -> dict[str, NodeReading]:
    now = datetime.now()
    readings: dict[str, NodeReading] = {}
    for node_id in NODE_IDS:
        if node_id in ACTIVE_NODES:
            readings[node_id] = _demo_reading_for_active_node(node_id, now, tick)
        else:
            readings[node_id] = _offline_reading(node_id, now)
    return readings


def get_demo_history(hours: int, node_ids: Optional[list[str]] = None) -> dict:
    node_ids = node_ids or ACTIVE_NODES
    now = datetime.now()
    step_minutes = max(1, (hours * 60) // 96)
    n_points = min(96, max(12, (hours * 60) // step_minutes))
    times = [now - timedelta(minutes=step_minutes * i) for i in range(n_points)][::-1]

    series = {}
    for node_id in node_ids:
        if node_id not in ACTIVE_NODES:
            series[node_id] = [0.0 for _ in times]
            continue
        severity = DEMO_SEVERITY.get(node_id, "Normal")
        base = {"Normal": 16, "Warning": 40, "Critical": 62}[severity]
        rng = random.Random(hash(node_id) & 0xFFFF)
        vals, cur = [], base
        for _ in times:
            cur = max(2, min(99, cur + rng.normalvariate(0, 2.1)))
            vals.append(round(cur, 1))
        series[node_id] = vals

    overall = [
        round(sum(series[n][i] for n in node_ids) / max(1, len(node_ids)), 1)
        for i in range(len(times))
    ]
    return {"times": times, "series": series, "overall": overall}


def get_demo_alerts(readings: dict[str, NodeReading]) -> list[dict]:
    alerts = []
    now = datetime.now()

    for node_id in ACTIVE_NODES:
        r = readings.get(node_id)
        if not r or not r.online:
            continue
        if r.status == "Critical":
            alerts.append({"node": node_id, "event": "Risk level elevated to critical",
                            "severity": "Critical", "timestamp": now - timedelta(minutes=2)})
        if r.vibration > 0.8:
            alerts.append({"node": node_id, "event": "High vibration detected",
                            "severity": "Critical" if r.vibration > 1.1 else "Warning",
                            "timestamp": now - timedelta(minutes=14)})
        if abs(r.pitch) > 3.5:
            alerts.append({"node": node_id, "event": "Tilt / Pitch deviation detected",
                            "severity": "Warning", "timestamp": now - timedelta(minutes=41)})

    alerts.append({"node": "System", "event": "LoRa USB receiver active",
                   "severity": "Normal", "timestamp": now - timedelta(hours=1)})

    alerts.sort(key=lambda a: a["timestamp"], reverse=True)
    return alerts[:8]


def get_live_data() -> dict[str, NodeReading]:
    """LIVE hardware data path. Calls esp32_connection.get_latest_nodes()."""
    try:
        from esp32_connection import get_latest_nodes
        raw_nodes = get_latest_nodes()
    except Exception:
        raw_nodes = {}

    now = datetime.now()
    readings: dict[str, NodeReading] = {}

    for node_id in NODE_IDS:
        raw = raw_nodes.get(node_id) if raw_nodes else None

        if not raw:
            readings[node_id] = _offline_reading(node_id, now)
            continue

        last_seen = raw.get("timestamp", now)
        age = (now - last_seen).total_seconds() if isinstance(last_seen, datetime) else 9999
        online = age <= STALE_TIMEOUT_SECONDS

        if not online:
            readings[node_id] = _offline_reading(node_id, now)
            continue

        risk = int(raw.get("risk", 0))
        readings[node_id] = NodeReading(
            node_id=node_id,
            timestamp=last_seen,
            active=True,
            online=True,
            status=classify_status(risk, online=True),
            pitch=float(raw.get("pitch_deg", 0.0)),
            roll=float(raw.get("roll_deg", 0.0)),
            vibration=float(raw.get("vibration_intensity", 0.0)),
            temperature=float(raw.get("temp_c", 0.0)),
            risk=risk,
            displacement=float(raw.get("displacement", 0.0)),
            crack=float(raw.get("crack", 0.0)),
            anomaly=bool(raw.get("anomaly", False)),
            signal=int(raw.get("signal", 0)),
            health=int(raw.get("health", 0)),
            location_label=NODE_LOCATION_LABEL.get(node_id, ""),
            stale=False,
        )

    return readings


STAGE_TO_STATUS = {
    0: "Normal",    # STABLE_BASELINE
    1: "Normal",    # MICRO_VIBRATION
    2: "Warning",   # SLOW_TILT_SUBSIDENCE
    3: "Critical",  # ABNORMAL_DEFORMATION
}

STAGE_RISK_RANGE = {
    0: (0, 20),
    1: (20, 100),
    2: (60, 100),
    3: (80, 100),
}

def _risk_from_stage(stage: int, confidence: float) -> int:
    low, high = STAGE_RISK_RANGE.get(stage, (0, 20))
    conf = max(0.0, min(100.0, confidence)) / 100.0
    return int(round(low + conf * (high - low)))


def get_dashboard_data(tick: int = 0) -> dict[str, NodeReading]:
    readings = get_live_data() if LIVE_MODE else get_demo_data(tick)

    for nid in readings:
        live_data = get_latest_node_data(nid)
        if live_data and (time.time() - live_data["last_update"] < 10):
            r = readings[nid]
            stage = live_data.get("stage", 0)
            r.pitch = live_data["tilt"]
            r.roll = live_data["pred_tilt"]
            r.stage_label = live_data.get("stage_label", "")
            r.alert_level = live_data.get("alert_level", "")
            r.risk = _risk_from_stage(stage, live_data["confidence"])
            r.status = classify_status(r.risk, online=True)
            r.online = True
            r.stale = False

    return readings


def summarize(readings: dict[str, NodeReading]) -> dict:
    active = [r for r in readings.values() if r.active]
    online = [r for r in active if r.online]

    counts = {"Normal": 0, "Warning": 0, "Critical": 0, "Offline": 0}
    for r in readings.values():
        counts[r.status] = counts.get(r.status, 0) + 1

    overall_risk = int(round(sum(r.risk for r in online) / len(online))) if online else 0
    if overall_risk >= RISK_THRESHOLDS["Critical"]:
        overall_label = "Critical"
    elif overall_risk >= RISK_THRESHOLDS["Warning"]:
        overall_label = "Elevated"
    else:
        overall_label = "Stable"

    return {
        "total_nodes": len(readings),
        "active_nodes": len(active),
        "online_nodes": len(online),
        "offline_nodes": len(readings) - len(online),
        "counts": counts,
        "overall_risk": overall_risk,
        "overall_label": overall_label,
    }