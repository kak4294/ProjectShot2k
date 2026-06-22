# ProjectShot2k

Remote couch co-op for Xbox 360 games. Play NBA 2K11 (via Xenia emulator) with friends over the internet as if you're all on the same couch, while streaming to Twitch for spectators.

## Quick Start

### Prerequisites (Host PC — Windows)

1. **ViGEmBus driver** — [Download latest release](https://github.com/nefarius/ViGEmBus/releases) → install → reboot
2. **Python 3.10+** — [python.org](https://www.python.org/downloads/)

### Install

```bash
cd ProjectShot2k/server
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Run

```bash
cd ProjectShot2k/server
venv\Scripts\activate
python main.py
```

Server starts on `http://0.0.0.0:8000`. Open that in a browser to see the controller client.

### Test It

1. Plug a controller into your PC
2. Open `http://localhost:8000` in your browser
3. Press a button on your controller so the browser detects it
4. Select a player slot (P1–P4)
5. Open `joy.cpl` (Win+R → `joy.cpl`) — you should see the virtual gamepad mirroring your inputs

### Remote Players (over Tailscale)

1. Both host and player join the same [Tailscale](https://tailscale.com/) network
2. Player opens `http://<host-tailscale-ip>:8000` in their browser
3. Player connects Moonlight to the same Tailscale IP for low-latency video

## Project Structure

```
ProjectShot2k/
├── server/
│   ├── main.py              # FastAPI server — WebSocket + HTTP
│   ├── config.py            # Central configuration
│   ├── gamepad_manager.py   # Virtual gamepad management (vgamepad/ViGEmBus)
│   └── requirements.txt
├── client/
│   └── index.html           # React controller client (single file, no build step)
└── README.md
```

## Architecture

```
Controller (USB) → Browser (Gamepad API) → WebSocket → FastAPI → vgamepad → Xenia
                                                                              ↓
                                              Sunshine → Moonlight (player video)
                                              OBS → Twitch (spectator stream)
```

## Configuration

Edit `server/config.py` or set environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CC360_HOST` | `0.0.0.0` | Server bind address |
| `CC360_PORT` | `8000` | Server port |
| `CC360_DEADZONE` | `0.10` | Default analog stick deadzone |
| `CC360_LOG_LEVEL` | `INFO` | Logging level |