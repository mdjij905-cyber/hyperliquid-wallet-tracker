"""
notifier.py — Handles all outbound notifications.

Supports:
  • Rich console (always active)
  • Telegram (if TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID are set)
  • Discord  (if DISCORD_WEBHOOK_URL is set)
"""

import requests
from datetime import datetime, timezone
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box
from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    DISCORD_WEBHOOK_URL,
    NOTIFY_NEW_POSITION, NOTIFY_POSITION_CLOSED, NOTIFY_SIZE_CHANGE,
)

console = Console()


# ─── helpers ──────────────────────────────────────────────────────────────────

def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _short(address: str) -> str:
    return f"{address[:6]}…{address[-4:]}"


def _send_telegram(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            console.print(f"[yellow][Telegram] Non-200 response: {r.text[:200]}[/yellow]")
    except Exception as exc:
        console.print(f"[yellow][Telegram] Send error: {exc}[/yellow]")


def _send_discord(embed: dict) -> None:
    if not DISCORD_WEBHOOK_URL:
        return
    payload = {"embeds": [embed]}
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if r.status_code not in (200, 204):
            console.print(f"[yellow][Discord] Non-200 response: {r.text[:200]}[/yellow]")
    except Exception as exc:
        console.print(f"[yellow][Discord] Send error: {exc}[/yellow]")


# ─── public notification functions ────────────────────────────────────────────

def notify_new_position(wallet: str, alias: str, coin: str, side: str,
                        size: float, entry_price: float, leverage,
                        notional: float) -> None:
    if not NOTIFY_NEW_POSITION:
        return

    label    = alias or _short(wallet)
    emoji    = "🟢" if side == "Long" else "🔴"
    side_str = f"[bold green]LONG[/bold green]" if side == "Long" else "[bold red]SHORT[/bold red]"
    ts       = _now_str()
    lev      = f"{leverage}x" if leverage else "–"

    # ── Console ──
    content = Text.assemble(
        ("Wallet:  ", "dim"), (f"{label}\n", "bold cyan"),
        ("Coin:    ", "dim"), (f"{coin}\n", "bold white"),
        ("Side:    ", "dim"),
    )
    content.append(f"{'LONG' if side == 'Long' else 'SHORT'}\n",
                   style="bold green" if side == "Long" else "bold red")
    content.append("Size:    ", style="dim")
    content.append(f"{abs(size):,.4f}  (~${notional:,.0f})\n", style="white")
    content.append("Entry:   ", style="dim")
    content.append(f"${entry_price:,.4f}\n", style="white")
    content.append("Leverage:", style="dim")
    content.append(f" {lev}\n", style="yellow")
    content.append("Time:    ", style="dim")
    content.append(ts, style="dim")

    panel = Panel(
        content,
        title=f"[bold]{emoji}  NEW POSITION OPENED[/bold]",
        border_style="green" if side == "Long" else "red",
        box=box.DOUBLE_EDGE,
        padding=(0, 2),
    )
    console.print(panel)

    # ── Telegram ──
    tg = (
        f"{emoji} <b>NEW POSITION OPENED</b>\n\n"
        f"👤 <b>Wallet:</b> <code>{label}</code>\n"
        f"🪙 <b>Coin:</b> {coin}\n"
        f"📈 <b>Side:</b> {'LONG' if side == 'Long' else 'SHORT'}\n"
        f"📦 <b>Size:</b> {abs(size):,.4f}  (~${notional:,.0f})\n"
        f"💵 <b>Entry:</b> ${entry_price:,.4f}\n"
        f"⚡ <b>Leverage:</b> {lev}\n"
        f"🕐 <b>Time:</b> {ts}"
    )
    _send_telegram(tg)

    # ── Discord ──
    color = 0x00FF88 if side == "Long" else 0xFF4455
    _send_discord({
        "title": f"{emoji}  New Position Opened",
        "color": color,
        "fields": [
            {"name": "Wallet",   "value": f"`{label}`",              "inline": True},
            {"name": "Coin",     "value": coin,                       "inline": True},
            {"name": "Side",     "value": side,                       "inline": True},
            {"name": "Size",     "value": f"{abs(size):,.4f}  (~${notional:,.0f})", "inline": True},
            {"name": "Entry",    "value": f"${entry_price:,.4f}",    "inline": True},
            {"name": "Leverage", "value": lev,                        "inline": True},
        ],
        "footer": {"text": f"HyperLiquid Wallet Tracker  •  {ts}"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def notify_position_closed(wallet: str, alias: str, coin: str,
                            side: str, pnl: float) -> None:
    if not NOTIFY_POSITION_CLOSED:
        return

    label   = alias or _short(wallet)
    emoji   = "✅" if pnl >= 0 else "❌"
    pnl_str = f"+${pnl:,.2f}" if pnl >= 0 else f"-${abs(pnl):,.2f}"
    ts      = _now_str()

    # ── Console ──
    content = Text.assemble(
        ("Wallet:  ", "dim"), (f"{label}\n", "bold cyan"),
        ("Coin:    ", "dim"), (f"{coin}\n", "bold white"),
        ("Side:    ", "dim"), (f"{side}\n", "bold"),
        ("PnL:     ", "dim"),
    )
    content.append(f"{pnl_str}\n", style="bold green" if pnl >= 0 else "bold red")
    content.append("Time:    ", style="dim")
    content.append(ts, style="dim")

    panel = Panel(
        content,
        title=f"[bold]{emoji}  POSITION CLOSED[/bold]",
        border_style="blue",
        box=box.DOUBLE_EDGE,
        padding=(0, 2),
    )
    console.print(panel)

    # ── Telegram ──
    tg = (
        f"{emoji} <b>POSITION CLOSED</b>\n\n"
        f"👤 <b>Wallet:</b> <code>{label}</code>\n"
        f"🪙 <b>Coin:</b> {coin}\n"
        f"📈 <b>Side:</b> {side}\n"
        f"💰 <b>PnL:</b> {pnl_str}\n"
        f"🕐 <b>Time:</b> {ts}"
    )
    _send_telegram(tg)

    # ── Discord ──
    _send_discord({
        "title": f"{emoji}  Position Closed",
        "color": 0x00AAFF,
        "fields": [
            {"name": "Wallet", "value": f"`{label}`", "inline": True},
            {"name": "Coin",   "value": coin,          "inline": True},
            {"name": "Side",   "value": side,           "inline": True},
            {"name": "PnL",    "value": pnl_str,        "inline": True},
        ],
        "footer": {"text": f"HyperLiquid Wallet Tracker  •  {ts}"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def notify_size_change(wallet: str, alias: str, coin: str, side: str,
                       old_size: float, new_size: float,
                       old_notional: float, new_notional: float) -> None:
    if not NOTIFY_SIZE_CHANGE:
        return

    label   = alias or _short(wallet)
    emoji   = "📈" if abs(new_size) > abs(old_size) else "📉"
    action  = "INCREASED" if abs(new_size) > abs(old_size) else "REDUCED"
    delta   = new_notional - old_notional
    delta_s = f"+${delta:,.0f}" if delta >= 0 else f"-${abs(delta):,.0f}"
    ts      = _now_str()

    # ── Console ──
    content = Text.assemble(
        ("Wallet:  ", "dim"), (f"{label}\n", "bold cyan"),
        ("Coin:    ", "dim"), (f"{coin}  [{side}]\n", "bold white"),
        ("Change:  ", "dim"), (f"{abs(old_size):,.4f} → {abs(new_size):,.4f}  ({delta_s})\n", "yellow"),
        ("Time:    ", "dim"), (ts, "dim"),
    )
    panel = Panel(
        content,
        title=f"[bold]{emoji}  POSITION {action}[/bold]",
        border_style="yellow",
        box=box.DOUBLE_EDGE,
        padding=(0, 2),
    )
    console.print(panel)

    # ── Telegram ──
    tg = (
        f"{emoji} <b>POSITION {action}</b>\n\n"
        f"👤 <b>Wallet:</b> <code>{label}</code>\n"
        f"🪙 <b>Coin:</b> {coin}  [{side}]\n"
        f"📦 <b>Change:</b> {abs(old_size):,.4f} → {abs(new_size):,.4f}  ({delta_s})\n"
        f"🕐 <b>Time:</b> {ts}"
    )
    _send_telegram(tg)

    # ── Discord ──
    _send_discord({
        "title": f"{emoji}  Position {action.title()}",
        "color": 0xFFAA00,
        "fields": [
            {"name": "Wallet", "value": f"`{label}`",         "inline": True},
            {"name": "Coin",   "value": f"{coin}  [{side}]",  "inline": True},
            {"name": "Change", "value": f"{abs(old_size):,.4f} → {abs(new_size):,.4f}  ({delta_s})", "inline": False},
        ],
        "footer": {"text": f"HyperLiquid Wallet Tracker  •  {ts}"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def notify_error(message: str) -> None:
    console.print(f"[bold red][ERROR][/bold red] {message}")


def notify_info(message: str) -> None:
    console.print(f"[dim cyan][INFO][/dim cyan] {message}")
