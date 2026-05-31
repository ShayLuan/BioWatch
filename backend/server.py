# server.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import random
import httpx
from datetime import datetime
from typing import Dict, List
import logging
import time

from calculate_real_time_risk import AMRRiskEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BioWatch Sensor Backend")

# Gap 3 — CORS: allow the Vite dev server to open WebSocket + HTTP connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Risk engine ───────────────────────────────────────────────────────────────
risk_engine = AMRRiskEngine()

# ── Flag / tier thresholds — kept in sync with src/config.js ─────────────────
TURB_FLAG_NTU    = 4.5
WARM_TEMP_C      = 26.0
WINDOW_HOURS     = 6
FLAG_DEBOUNCE_MS = 30_000   # 30 s minimum between flags — primary gate at high send rate
FLAG_WARN  = 5              # ~2.5 min sustained contamination
FLAG_WARN2 = 10             # ~5 min
FLAG_PANIC = 18             # ~9 min of repeated contamination in 6 h window

TIER_ACTION = {
    "passed": None,
    "warn":   "Drain clean cold water for 2 minutes.",
    "warn2":  "Drain hot water immediately, then flush cold.",
    "panic":  "PANIC: Immediate sanitisation required.",
}

def tier_from_count(n: int) -> str:
    if n >= FLAG_PANIC:  return "panic"
    if n >= FLAG_WARN2:  return "warn2"
    if n >= FLAG_WARN:   return "warn"
    return "passed"

# ── Panic log ─────────────────────────────────────────────────────────────────
import json as _json
_panic_log: List[dict] = []
_PANIC_LOG_PATH = os.path.join(os.path.dirname(__file__), "panic_log.json")

def _cleaning_steps(peak_temp: float, peak_turb: float) -> List[str]:
    steps = ["Isolate the drain — stop use immediately."]
    if peak_temp > 30:
        steps.append("Shut off the hot-water source feeding this drain trap.")
    steps.append("Flush with cold water (below 15°C) for 3 minutes.")
    if peak_turb > 10:
        steps.append("Physically scrub the drain interior and trap housing.")
    steps += [
        "Apply enzymatic drain cleaner — leave for 20 minutes.",
        "Rinse thoroughly with cold water.",
        "Leave drain dry for 4 hours minimum.",
        "Re-run BioWatch and confirm Passed tier before resuming use.",
    ]
    return steps

def _log_panic(device_id: str, historical: list) -> dict:
    temps = [r["temp"] for r in historical] if historical else []
    turbs = [r["turbidity"] for r in historical] if historical else []
    peak_temp = round(max(temps), 2) if temps else 0.0
    peak_turb = round(max(turbs), 2) if turbs else 0.0
    avg_temp  = round(sum(temps) / len(temps), 2) if temps else 0.0
    avg_turb  = round(sum(turbs) / len(turbs), 2) if turbs else 0.0
    entry = {
        "ts":         int(time.time() * 1000),
        "device_id":  device_id,
        "peak_temp":  peak_temp,
        "peak_turb":  peak_turb,
        "avg_temp":   avg_temp,
        "avg_turb":   avg_turb,
        "steps":      _cleaning_steps(peak_temp, peak_turb),
    }
    _panic_log.append(entry)
    try:
        with open(_PANIC_LOG_PATH, "w") as fh:
            _json.dump(_panic_log, fh, indent=2)
    except Exception as e:
        logger.error(f"Panic log write failed: {e}")
    return entry

# ── Per-device sliding-window state ──────────────────────────────────────────
_device_state: Dict[str, dict] = {}

def _get_state(device_id: str) -> dict:
    if device_id not in _device_state:
        _device_state[device_id] = {
            "flags": [],        # list of {ts, temp, turbidity}
            "last_flag_at": 0,  # ms epoch
            "last_tier": None,
            "last_count": -1,
        }
    return _device_state[device_id]

# Dashboard WebSocket manager
class DashboardManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.remove(ws)

dashboard_manager = DashboardManager()

# Device WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.data_buffer: Dict[str, List] = {}

    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[device_id] = websocket
        self.data_buffer[device_id] = []
        logger.info(f"Device {device_id} connected")

    async def disconnect(self, device_id: str):
        if device_id in self.active_connections:
            del self.active_connections[device_id]
        logger.info(f"Device {device_id} disconnected")

    def get_device_status(self):
        return {
            device_id: {
                "connected": True,
                "last_data_count": len(self.data_buffer.get(device_id, []))
            }
            for device_id in self.active_connections
        }

manager = ConnectionManager()

# ── Virtual sensor simulation (mirrors SEED + step() from mockBackend.js) ─────
EMIT_INTERVAL = 1.5   # seconds between ticks
INJECT_TICKS  = 2     # how many ticks a contamination pulse lasts

_virtual_sensors = [
    {"id": "S-01", "baseTemp": 27.2, "baseTurb": 1.1},
    {"id": "S-02", "baseTemp": 22.8, "baseTurb": 0.9},
    {"id": "S-03", "baseTemp": 28.4, "baseTurb": 2.0},
    {"id": "S-04", "baseTemp": 29.1, "baseTurb": 2.4},
]

_sim_state: Dict[str, dict] = {
    s["id"]: {"baseTemp": s["baseTemp"], "baseTurb": s["baseTurb"], "inject": 0}
    for s in _virtual_sensors
}

async def simulation_loop():
    """Emit mock readings for every sensor that has no real device connected."""
    while True:
        await asyncio.sleep(EMIT_INTERVAL)
        if not dashboard_manager.connections:
            continue
        now_ms = int(time.time() * 1000)
        for s in _virtual_sensors:
            sid = s["id"]
            if sid in manager.active_connections:
                continue   # real device is live — skip virtual
            ss = _sim_state[sid]
            temp = ss["baseTemp"] + (random.random() - 0.5) * 0.6
            if ss["inject"] > 0:
                temp += 1.8
            temp = max(15.0, min(40.0, temp))
            t = ss["baseTurb"] + random.random() * 0.7
            if ss["inject"] > 0:
                t += 6 + random.random() * 3
                ss["inject"] -= 1
            elif random.random() < 0.012:
                t += 3 + random.random() * 2
            turb = max(0.0, t)
            # Keep a buffer for virtual sensors so compute_features has history
            if sid not in manager.data_buffer:
                manager.data_buffer[sid] = []
            manager.data_buffer[sid].append({"ts": now_ms, "temp": temp, "turbidity": turb})
            await process_reading(sid, temp, turb, now_ms)

@app.on_event("startup")
async def startup():
    asyncio.create_task(simulation_loop())

ML_ENDPOINT = "http://localhost:8001/predict"

async def send_to_ml_endpoint(sensor_data: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(ML_ENDPOINT, json=sensor_data)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"ML endpoint request error: {e}")
        return {"error": str(e), "prediction": None}
    except Exception as e:
        logger.error(f"Unexpected ML endpoint error: {e}")
        return {"error": str(e), "prediction": None}

# Core processing — runs on every device reading
async def process_reading(device_id: str, temp: float, turb: float, ts_ms: int):
    """
    Gap 2: Applies the flag/tier logic from mockBackend.js on the server side,
    then broadcasts the three message types the React dashboard expects.
    """
    state = _get_state(device_id)

    # 1. reading → dashboard
    await dashboard_manager.broadcast({
        "type":      "reading",
        "ts":        ts_ms,
        "sensorId":  device_id,
        "temp":      temp,
        "turbidity": turb,
    })

    # 2. flag detection
    if (turb >= TURB_FLAG_NTU and temp >= WARM_TEMP_C and
            ts_ms - state["last_flag_at"] >= FLAG_DEBOUNCE_MS):
        state["last_flag_at"] = ts_ms
        state["flags"].append({"ts": ts_ms, "temp": temp, "turbidity": turb})
        flag_number = len(state["flags"])
        await dashboard_manager.broadcast({
            "type":       "flag",
            "ts":         ts_ms,
            "sensorId":   device_id,
            "temp":       temp,
            "turbidity":  turb,
            "flagNumber": flag_number,
            "flagTier":   tier_from_count(flag_number),
        })

    # 3. sliding-window tier (prune expired flags, then escalate)
    cutoff = ts_ms - WINDOW_HOURS * 3_600_000
    state["flags"] = [f for f in state["flags"] if f["ts"] >= cutoff]
    count    = len(state["flags"])
    tier     = tier_from_count(count)
    old_tier = state["last_tier"]

    if tier != old_tier or count != state["last_count"]:
        state["last_tier"]  = tier
        state["last_count"] = count

        steps = None
        if tier == "panic" and old_tier != "panic":
            historical = manager.data_buffer.get(device_id, [])[-100:]
            entry  = _log_panic(device_id, historical)
            steps  = entry["steps"]
            logger.warning(f"PANIC logged for {device_id} — peak {entry['peak_temp']}°C / {entry['peak_turb']} NTU")

        await dashboard_manager.broadcast({
            "type":          "status",
            "sensorId":      device_id,
            "tier":          tier,
            "flagsInWindow": count,
            "windowHours":   WINDOW_HOURS,
            "action":        TIER_ACTION.get(tier),
            "steps":         steps,
        })

# TODO: confirm function
# ── Derived feature computation from rolling buffer ──────────────────────────
def compute_features(device_id: str, temp: float, turb: float, ts_ms: int) -> dict:
    """
    Build the full feature dict the ML service expects.
    Derives time-windowed features from the device's data buffer.
    Omitted sensor types (flow) default to 0.
    """
    history = manager.data_buffer.get(device_id, [])
    ms_24h  = 24 * 3_600_000
    ms_48h  = 48 * 3_600_000

    readings_24h = [r for r in history if r["ts"] >= ts_ms - ms_24h]
    readings_48h = [r for r in history if r["ts"] >= ts_ms - ms_48h]

    turb_delta_24h = (turb - readings_24h[0]["turbidity"]) if readings_24h else 0.0
    turb_max_48h   = max((r["turbidity"] for r in readings_48h), default=turb)
    temp_mean_48h  = (sum(r["temp"] for r in readings_48h) / len(readings_48h)
                      if readings_48h else temp)

    return {
        "Temperature_C":            temp,
        "Turbidity_FNU":            turb,
        "Turbidity_Delta_24h":      turb_delta_24h,
        "Turbidity_Max_48h":        turb_max_48h,
        "Temp_Rolling_Mean_48h":    temp_mean_48h,
        "Temp_Turbidity_Interaction": temp * turb,
        "Flow_CFS":                 0.0,
        "Flow_Delta_24h":           0.0,
    }

# TODO: confirm function
# ── Bare /ws — accepts device_id via query param or first message ─────────────
# Starlette 1.x does not route WebSocket upgrades at the root path "/".
# Use  ws://host:8000/ws?device_id=sink_01  or send device_id in first JSON.
@app.websocket("/ws")
async def root_websocket_endpoint(websocket: WebSocket, device_id: str = ""):
    await websocket.accept()

    pending: dict | None = None
    if not device_id:
        try:
            raw = await websocket.receive_text()
            pending = json.loads(raw)
            device_id = pending.get("device_id", "")
        except Exception:
            await websocket.close(code=1008, reason="First message must be JSON with device_id")
            return
        if not device_id:
            await websocket.close(code=1008, reason="device_id required in query param or payload")
            return

    manager.active_connections[device_id] = websocket
    manager.data_buffer.setdefault(device_id, [])
    logger.info(f"Device {device_id} connected via root WS")

    async def _process(sensor_data: dict):
        temp  = float(sensor_data.get("temp_c",        sensor_data.get("temp", 0)))
        turb  = float(sensor_data.get("turbidity_ntu", sensor_data.get("turbidity", sensor_data.get("turb", 0))))
        ts_ms = int(sensor_data.get("ts", time.time() * 1000))
        manager.data_buffer[device_id].append({"ts": ts_ms, "temp": temp, "turbidity": turb})
        historical = manager.data_buffer[device_id][-100:]
        risk = risk_engine.calculate_realtime_risk(temp, turb, historical_buffer=historical)
        await process_reading(device_id, temp, turb, ts_ms)
        await websocket.send_json({
            "device_id":   device_id,
            "received_at": datetime.now().isoformat(),
            "sensor_data": sensor_data,
            "risk":        risk,
        })

    try:
        if pending is not None:
            await _process(pending)
        while True:
            await _process(json.loads(await websocket.receive_text()))
    except WebSocketDisconnect:
        await manager.disconnect(device_id)
    except Exception as e:
        logger.error(f"Root WS error for {device_id}: {e}")
        await manager.disconnect(device_id)

# TODO: confirm function
# ── Gap 1 — Dashboard WebSocket endpoint ─────────────────────────────────────
@app.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    await dashboard_manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            # Inject command: forward to the target device if it is connected
            if msg.get("cmd") == "inject":
                device_id = msg.get("sensorId")
                if device_id in manager.active_connections:
                    await manager.active_connections[device_id].send_json({"cmd": "inject"})
                elif device_id in _sim_state:
                    _sim_state[device_id]["inject"] = INJECT_TICKS
    except WebSocketDisconnect:
        dashboard_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Dashboard WS error: {e}")
        dashboard_manager.disconnect(websocket)

# ── Device WebSocket endpoint ─────────────────────────────────────────────────
@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    await manager.connect(device_id, websocket)
    try:
        while True:
            data        = await websocket.receive_text()
            sensor_data = json.loads(data)
            logger.info(f"Device {device_id}: {sensor_data}")

            # Normalise field names — Pi/ESP may send temp_c/turbidity_ntu or temp/turbidity/turb
            temp = float(sensor_data.get("temp_c", sensor_data.get("temp", 0)))
            turb = float(sensor_data.get("turbidity_ntu", sensor_data.get("turbidity", sensor_data.get("turb", 0))))
            ts_ms = int(sensor_data.get("ts", time.time() * 1000))

            # Store normalised reading for historical window passed to risk engine
            normalised = {"ts": ts_ms, "temp": temp, "turbidity": turb}
            manager.data_buffer[device_id].append(normalised)

            # Send to ML service (port 8001); falls back to local engine if not running
            features   = compute_features(device_id, temp, turb, ts_ms)
            ml_result  = await send_to_ml_endpoint(features)
            if "band" not in ml_result:
                historical = manager.data_buffer[device_id][-100:]
                ml_result  = risk_engine.calculate_realtime_risk(temp, turb, historical_buffer=historical)
                ml_result["source"] = "AMRRiskEngine (fallback)"

            # Broadcast the three UI message types to all dashboard clients
            await process_reading(device_id, temp, turb, ts_ms)

            # Enriched acknowledgement back to the ESP32
            await websocket.send_json({
                "device_id":   device_id,
                "received_at": datetime.now().isoformat(),
                "sensor_data": sensor_data,
                "risk":        ml_result,
            })

    except WebSocketDisconnect:
        await manager.disconnect(device_id)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error from {device_id}: {e}")
        await manager.disconnect(device_id)
    except Exception as e:
        logger.error(f"Unexpected error for {device_id}: {e}")
        await manager.disconnect(device_id)

# ── HTTP endpoints ────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/panic-log")
async def get_panic_log():
    return {"entries": _panic_log}

@app.get("/api/health")
async def health_check():
    return {
        "status":            "healthy",
        "connected_devices": len(manager.active_connections),
        "dashboard_clients": len(dashboard_manager.connections),
        "devices":           manager.get_device_status(),
    }

@app.get("/api/device/{device_id}/history")
async def get_device_history(device_id: str, limit: int = 100):
    if device_id not in manager.data_buffer:
        return JSONResponse(status_code=404, content={"error": f"Device {device_id} not found"})
    data = manager.data_buffer[device_id][-limit:]
    return {"device_id": device_id, "record_count": len(data), "data": data}

@app.delete("/api/device/{device_id}/history")
async def clear_device_history(device_id: str):
    if device_id in manager.data_buffer:
        manager.data_buffer[device_id] = []
        return {"message": f"History cleared for {device_id}"}
    return JSONResponse(status_code=404, content={"error": f"Device {device_id} not found"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
