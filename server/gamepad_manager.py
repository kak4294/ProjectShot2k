"""
ProjectShot2k — Virtual Gamepad Manager

Creates and manages virtual Xbox 360 controllers via ViGEmBus/vgamepad.
Each player slot (1-4) gets a dedicated virtual gamepad.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

try:
    import vgamepad as vg

    VGAMEPAD_AVAILABLE = True
except ImportError:
    VGAMEPAD_AVAILABLE = False

from config import MAX_PLAYERS, VALID_SLOTS

logger = logging.getLogger("projectshot2k.gamepad")

# ---------------------------------------------------------------------------
# Button mapping: JSON key → vgamepad constant
# ---------------------------------------------------------------------------
if VGAMEPAD_AVAILABLE:
    BUTTON_MAP: dict[str, Any] = {
        "A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
        "B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
        "X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
        "Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
        "LB": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
        "RB": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
        "BACK": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
        "START": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
        "LS": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
        "RS": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
        "DPAD_UP": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
        "DPAD_DOWN": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
        "DPAD_LEFT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
        "DPAD_RIGHT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
        "GUIDE": vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
    }
else:
    BUTTON_MAP = {}


# ---------------------------------------------------------------------------
# Per-slot stats
# ---------------------------------------------------------------------------
@dataclass
class SlotStats:
    connected: bool = False
    frames_received: int = 0
    last_frame_time: float = 0.0
    last_latency_ms: float = 0.0
    client_ip: str = ""


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------
class GamepadManager:
    """Manages virtual Xbox 360 gamepads for all player slots."""

    def __init__(self) -> None:
        self._pads: dict[int, Any] = {}
        self._stats: dict[int, SlotStats] = {
            slot: SlotStats() for slot in VALID_SLOTS
        }

        if not VGAMEPAD_AVAILABLE:
            logger.warning(
                "vgamepad not available — running in STUB MODE. "
                "Install vgamepad + ViGEmBus on Windows to create real virtual gamepads."
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def create_all(self) -> None:
        """Create virtual gamepads for every slot on server startup."""
        if not VGAMEPAD_AVAILABLE:
            logger.info("Stub mode: skipping gamepad creation.")
            return

        for slot in VALID_SLOTS:
            try:
                pad = vg.VX360Gamepad()
                self._pads[slot] = pad
                logger.info(f"Created virtual gamepad for slot {slot}")
            except Exception as e:
                logger.error(f"Failed to create gamepad for slot {slot}: {e}")

    def destroy_all(self) -> None:
        """Release all virtual gamepads on server shutdown."""
        for slot, pad in self._pads.items():
            try:
                pad.reset()
                pad.update()
                del pad
                logger.info(f"Released virtual gamepad for slot {slot}")
            except Exception as e:
                logger.error(f"Error releasing gamepad for slot {slot}: {e}")
        self._pads.clear()

    # ------------------------------------------------------------------
    # Connection tracking
    # ------------------------------------------------------------------

    def connect_slot(self, slot: int, client_ip: str = "") -> bool:
        """Mark a slot as connected. Returns False if already taken."""
        if slot not in VALID_SLOTS:
            return False
        if self._stats[slot].connected:
            return False
        self._stats[slot] = SlotStats(connected=True, client_ip=client_ip)
        logger.info(f"Player connected to slot {slot} from {client_ip}")
        return True

    def disconnect_slot(self, slot: int) -> None:
        """Mark a slot as disconnected and reset its gamepad."""
        if slot in VALID_SLOTS:
            self._stats[slot] = SlotStats()
            if slot in self._pads:
                try:
                    self._pads[slot].reset()
                    self._pads[slot].update()
                except Exception:
                    pass
            logger.info(f"Player disconnected from slot {slot}")

    def is_slot_available(self, slot: int) -> bool:
        return slot in VALID_SLOTS and not self._stats[slot].connected

    def get_status(self) -> dict:
        """Return status dict for all slots."""
        return {
            "max_players": MAX_PLAYERS,
            "slots": {
                slot: {
                    "connected": s.connected,
                    "frames_received": s.frames_received,
                    "last_latency_ms": round(s.last_latency_ms, 1),
                    "client_ip": s.client_ip,
                }
                for slot, s in self._stats.items()
            },
        }

    # ------------------------------------------------------------------
    # Input application
    # ------------------------------------------------------------------

    def apply_input(self, slot: int, frame: dict) -> None:
        """Apply an input frame to the virtual gamepad for a slot.

        Args:
            slot: Player slot (1-4).
            frame: Input frame dict matching the project schema.
        """
        now = time.time()
        stats = self._stats.get(slot)
        if stats:
            stats.frames_received += 1
            stats.last_frame_time = now
            # Compute latency from client timestamp
            client_ts = frame.get("timestamp", 0)
            if client_ts:
                stats.last_latency_ms = now * 1000 - client_ts

        pad = self._pads.get(slot)
        if pad is None:
            return  # Stub mode or slot not created

        try:
            pad.reset()

            # Buttons
            buttons = frame.get("buttons", {})
            for btn_name, pressed in buttons.items():
                if pressed and btn_name in BUTTON_MAP:
                    pad.press_button(button=BUTTON_MAP[btn_name])

            # Triggers
            triggers = frame.get("triggers", {})
            pad.left_trigger_float(value_float=max(0.0, min(1.0, triggers.get("LT", 0.0))))
            pad.right_trigger_float(value_float=max(0.0, min(1.0, triggers.get("RT", 0.0))))

            # Sticks
            sticks = frame.get("sticks", {})
            pad.left_joystick_float(
                x_value_float=max(-1.0, min(1.0, sticks.get("LS_X", 0.0))),
                y_value_float=max(-1.0, min(1.0, sticks.get("LS_Y", 0.0))),
            )
            pad.right_joystick_float(
                x_value_float=max(-1.0, min(1.0, sticks.get("RS_X", 0.0))),
                y_value_float=max(-1.0, min(1.0, sticks.get("RS_Y", 0.0))),
            )

            pad.update()

        except Exception as e:
            logger.error(f"Error applying input for slot {slot}: {e}")