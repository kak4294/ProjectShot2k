"""
ProjectShot2k — Central Configuration

All tunable parameters in one place. Override via environment variables.
"""

import os


# --- Server ---
HOST: str = os.getenv("CC360_HOST", "0.0.0.0")
PORT: int = int(os.getenv("CC360_PORT", "8000"))

# --- Players ---
MAX_PLAYERS: int = 4
VALID_SLOTS: list[int] = [1, 2, 3, 4]

# --- Input ---
INPUT_POLL_RATE_HZ: int = 60  # Expected client send rate
DEADZONE: float = float(os.getenv("CC360_DEADZONE", "0.10"))
ACK_INTERVAL_FRAMES: int = 30  # Send an ack back to client every N frames

# --- WebSocket ---
WS_PING_INTERVAL: float = 20.0  # Seconds between pings
WS_PING_TIMEOUT: float = 10.0   # Seconds to wait for pong
WS_MAX_MESSAGE_SIZE: int = 4096  # Bytes — input frames are ~500B

# --- Logging ---
LOG_LEVEL: str = os.getenv("CC360_LOG_LEVEL", "INFO")