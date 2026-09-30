"""
web/server.py - FastAPI & WebSocket backend for the Network Monitor Web GUI.
"""

import sys
import os
import asyncio
import webbrowser
import psutil
from typing import Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Ensure project root is accessible
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.collector import NetworkTrafficCollector, NetworkSnapshot
from core.traffic_generator import TrafficGenerator

app = FastAPI(title="Network Bandwidth Monitor", description="CN Lab Project Web GUI")

# Global state instances
_collector: Optional[NetworkTrafficCollector] = None
_traffic_gen = TrafficGenerator()
_connected_websockets: List[WebSocket] = []

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class SettingsPayload(BaseModel):
    interface: Optional[str] = None
    demo_mode: Optional[bool] = None


class TrafficInjectPayload(BaseModel):
    type: str  # "icmp", "udp", "tcp"
    param: Optional[int] = None


@app.get("/")
async def get_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/interfaces")
async def get_interfaces():
    all_ifaces = NetworkTrafficCollector.get_available_interfaces()
    current = _collector.interface if _collector else "All"
    demo = _collector.demo_mode if _collector else False
    return {
        "interfaces": ["All"] + all_ifaces,
        "current_interface": current,
        "demo_mode": demo,
    }


@app.post("/api/settings")
async def update_settings(payload: SettingsPayload):
    global _collector
    if _collector is None:
        raise HTTPException(status_code=500, detail="Collector not initialized")

    if payload.demo_mode is not None:
        _collector.demo_mode = payload.demo_mode

    if payload.interface is not None:
        target_iface = None if payload.interface in ["All", "All Interfaces"] else payload.interface
        _collector.interface = target_iface

    return {
        "status": "success",
        "demo_mode": _collector.demo_mode,
        "current_interface": _collector.interface or "All",
    }


@app.get("/api/connections")
async def get_connections():
    """Returns active network sockets for the live connections inspector."""
    results = []
    try:
        conns = psutil.net_connections(kind="inet")
        for c in conns[:40]:
            l_ip = c.laddr.ip if c.laddr else ""
            l_port = c.laddr.port if c.laddr else 0
            r_ip = c.raddr.ip if c.raddr else "-"
            r_port = c.raddr.port if c.raddr else "-"
            proto = "TCP" if c.type == psutil.SOCK_STREAM else "UDP"
            status = str(c.status if c.status and proto == "TCP" else "STATELESS")
            
            results.append({
                "proto": str(proto),
                "local": f"{l_ip}:{l_port}",
                "remote": f"{r_ip}:{r_port}" if r_ip != "-" else "-",
                "status": status,
                "pid": str(c.pid) if c.pid else "-",
            })
    except Exception:
        # Fallback to netstat on Windows
        try:
            import subprocess
            out = subprocess.check_output(["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 4 and parts[0] in ["TCP", "UDP"]:
                    proto = parts[0]
                    local = parts[1]
                    remote = parts[2]
                    if proto == "TCP":
                        state = parts[3] if len(parts) > 3 else "ESTABLISHED"
                        pid = parts[4] if len(parts) > 4 else "-"
                    else:
                        state = "STATELESS"
                        pid = parts[3] if len(parts) > 3 else "-"
                    results.append({
                        "proto": proto,
                        "local": local,
                        "remote": remote,
                        "status": state,
                        "pid": pid,
                    })
                    if len(results) >= 40:
                        break
        except Exception:
            results = []

    return {"connections": results}


@app.post("/api/traffic/inject")
async def inject_traffic(payload: TrafficInjectPayload):
    t_type = payload.type.lower()
    if t_type == "icmp":
        count = payload.param or 5
        _traffic_gen.trigger_icmp_ping(count=count)
        return {"status": "started", "message": f"Sending {count} ICMP echo requests"}
    elif t_type == "udp":
        count = payload.param or 300
        _traffic_gen.trigger_udp_burst(packets=count)
        return {"status": "started", "message": f"Sending burst of {count} UDP datagrams"}
    elif t_type == "tcp":
        sec = payload.param or 4
        _traffic_gen.trigger_tcp_download(duration_sec=sec)
        return {"status": "started", "message": f"Streaming TCP traffic for {sec}s"}
    elif t_type in ["speedtest", "benchmark", "100mbps"]:
        sec = payload.param or 6
        _traffic_gen.trigger_speed_benchmark(duration_sec=sec)
        return {"status": "started", "message": f"Running 100+ Mbps multi-stream speed benchmark for {sec}s"}
    else:
        raise HTTPException(status_code=400, detail="Invalid traffic type")


@app.post("/api/peaks/reset")
async def reset_peaks():
    if _collector:
        _collector.reset_peaks()
    return {"status": "success", "message": "Peak bandwidth counters reset."}


_latest_snapshot_dict = {}

async def broadcast_worker():
    """Central singleton sampler ensuring consistent deltas and zero race conditions."""
    global _latest_snapshot_dict
    while True:
        try:
            if _collector:
                snapshot = _collector.get_snapshot()
                _latest_snapshot_dict = snapshot.to_dict()
                
                # Broadcast to all connected WebSockets
                stale = []
                for ws in list(_connected_websockets):
                    try:
                        await ws.send_json(_latest_snapshot_dict)
                    except Exception:
                        stale.append(ws)
                for ws in stale:
                    if ws in _connected_websockets:
                        _connected_websockets.remove(ws)
        except Exception:
            pass
        await asyncio.sleep(0.5)


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(broadcast_worker())


@app.websocket("/ws/traffic")
async def websocket_traffic_endpoint(websocket: WebSocket):
    await websocket.accept()
    _connected_websockets.append(websocket)
    if _latest_snapshot_dict:
        try:
            await websocket.send_json(_latest_snapshot_dict)
        except Exception:
            pass
    try:
        while True:
            # Keep connection alive; wait for client messages or disconnect
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if websocket in _connected_websockets:
            _connected_websockets.remove(websocket)


def start_web_server(port: int = 8000, demo_mode: bool = False, interface: Optional[str] = None):
    global _collector
    _collector = NetworkTrafficCollector(
        interface=interface,
        max_bar_length=18,
        demo_mode=demo_mode,
    )
    import uvicorn
    # Auto-open browser after 1 second in a thread
    def open_browser():
        import time
        time.sleep(1.2)
        webbrowser.open(f"http://localhost:{port}")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    start_web_server()
