"""
ProjectShot2k — FastAPI WebSocket Input Server

Receives controller input from remote players over WebSocket,
injects it into Windows as virtual Xbox 360 gamepads via vgamepad.
Also serves the browser-based controller client.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

import config
from gamepad_manager import GamepadManager

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s  %(name)-30s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("projectshot2k.server")

# ---------------------------------------------------------------------------
# Gamepad manager (singleton)
# ---------------------------------------------------------------------------
gpm = GamepadManager()

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ProjectShot2k server …")
    gpm.create_all()
    logger.info(f"Listening on {config.HOST}:{config.PORT}")
    yield
    logger.info("Shutting down — releasing virtual gamepads …")
    gpm.destroy_all()


app = FastAPI(title="ProjectShot2k", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Resolve client path
# ---------------------------------------------------------------------------
CLIENT_HTML = Path(__file__).resolve().parent.parent / "client" / "index.html"

# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def serve_client():
    """Serve the controller client app."""
    if CLIENT_HTML.exists():
        return FileResponse(CLIENT_HTML, media_type="text/html")
    return HTMLResponse("<h1>ProjectShot2k</h1><p>Client not found. Place index.html in ../client/</p>")


@app.get("/status")
async def status():
    """Return server status and connected players."""
    return JSONResponse(gpm.get_status())


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


# ---------------------------------------------------------------------------
# WebSocket controller endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/controller/{player_slot}")
async def controller_ws(websocket: WebSocket, player_slot: int):
    # Validate slot
    if player_slot not in config.VALID_SLOTS:
        await websocket.close(code=4001, reason=f"Invalid slot {player_slot}. Use 1-{config.MAX_PLAYERS}.")
        return

    # Check availability
    if not gpm.is_slot_available(player_slot):
        await websocket.close(code=4002, reason=f"Slot {player_slot} is already taken.")
        return

    await websocket.accept()
    client_ip = websocket.client.host if websocket.client else "unknown"
    gpm.connect_slot(player_slot, client_ip)

    # Send welcome message
    await websocket.send_json({
        "type": "welcome",
        "slot": player_slot,
        "message": f"Connected to slot {player_slot}",
    })

    frame_count = 0

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                frame = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(f"Slot {player_slot}: bad JSON, skipping frame")
                continue

            # Apply input to virtual gamepad
            gpm.apply_input(player_slot, frame)
            frame_count += 1

            # Periodic ack with latency info
            if frame_count % config.ACK_INTERVAL_FRAMES == 0:
                await websocket.send_json({
                    "type": "ack",
                    "seq": frame.get("seq", 0),
                    "server_time": time.time() * 1000,
                    "frames_received": frame_count,
                })

    except WebSocketDisconnect:
        logger.info(f"Slot {player_slot}: client disconnected")
    except Exception as e:
        logger.error(f"Slot {player_slot}: error — {e}")
    finally:
        gpm.disconnect_slot(player_slot)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
    )