"""
config.py — Centralised configuration loader.
All settings come from environment variables (loaded from .env).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Hyperliquid endpoints ──────────────────────────────────────────────────────
HL_REST_URL   = "https://api.hyperliquid.xyz/info"
HL_WS_URL     = "wss://api.hyperliquid.xyz/ws"

# ── Polling ────────────────────────────────────────────────────────────────────
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "7"))          # seconds between checks

# ── Telegram ───────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TRACKED_WALLETS     = os.getenv("TRACKED_WALLETS", "").strip()


# ── Discord ────────────────────────────────────────────────────────────────────
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

# ── Alert filters ──────────────────────────────────────────────────────────────
NOTIFY_NEW_POSITION  = os.getenv("NOTIFY_NEW_POSITION",  "true").lower() == "true"
NOTIFY_POSITION_CLOSED = os.getenv("NOTIFY_POSITION_CLOSED", "true").lower() == "true"
NOTIFY_SIZE_CHANGE   = os.getenv("NOTIFY_SIZE_CHANGE",   "true").lower() == "true"
MIN_SIZE_CHANGE_USD  = float(os.getenv("MIN_SIZE_CHANGE_USD", "100"))

# ── Persistence ────────────────────────────────────────────────────────────────
WALLETS_FILE = "wallets.json"
