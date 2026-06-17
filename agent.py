"""
agent.py — Core wallet monitoring engine.

Architecture:
  • Polls Hyperliquid REST API every POLL_INTERVAL seconds.
  • Maintains a snapshot of each wallet's open positions.
  • Diffs snapshots to detect: new positions, closed positions, size changes.
  • Dispatches alerts via notifier.py.
  • Persists wallet list to wallets.json so it survives restarts.
"""

import asyncio
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

import requests
from rich.console import Console
from rich.table import Table
from rich import box

from config import (
    HL_REST_URL, POLL_INTERVAL,
    WALLETS_FILE, MIN_SIZE_CHANGE_USD,
    TRACKED_WALLETS,
)
from notifier import (
    notify_new_position,
    notify_position_closed,
    notify_size_change,
    notify_error,
    notify_info,
)

console = Console()


# ─── data types ───────────────────────────────────────────────────────────────

class Position:
    """Represents one open perpetual position."""
    __slots__ = ("coin", "size", "side", "entry_price", "leverage",
                 "unrealized_pnl", "notional")

    def __init__(self, coin: str, size: float, entry_price: float,
                 leverage, unrealized_pnl: float):
        self.coin          = coin
        self.size          = size                                # negative = short
        self.side          = "Long" if size > 0 else "Short"
        self.entry_price   = entry_price
        self.leverage      = leverage
        self.unrealized_pnl = unrealized_pnl
        self.notional      = abs(size) * entry_price            # USD value

    def __repr__(self):
        return (f"<Position {self.coin} {self.side} "
                f"sz={self.size:.4f} entry=${self.entry_price:.4f}>")


WalletPositions = Dict[str, Position]   # coin → Position


# ─── WalletMonitor ────────────────────────────────────────────────────────────

class WalletMonitor:
    def __init__(self):
        # address (lower) → {"alias": str, "snapshot": WalletPositions | None,
        #                     "errors": int, "last_ok": float}
        self._wallets: Dict[str, dict] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._load_wallets()

    # ── persistence ───────────────────────────────────────────────────────────

    def _load_wallets(self) -> None:
        # 1. Load from wallets.json if exists
        if os.path.exists(WALLETS_FILE):
            try:
                with open(WALLETS_FILE, "r") as fh:
                    data = json.load(fh)
                for addr, info in data.items():
                    self._wallets[addr.lower()] = {
                        "alias":    info.get("alias", ""),
                        "snapshot": None,
                        "errors":   0,
                        "last_ok":  0.0,
                    }
            except Exception as exc:
                notify_error(f"Could not load {WALLETS_FILE}: {exc}")

        # 2. Load from TRACKED_WALLETS environment variable (comma-separated address:alias)
        if TRACKED_WALLETS:
            for item in TRACKED_WALLETS.split(","):
                item = item.strip()
                if not item:
                    continue
                if ":" in item:
                    addr, alias = item.split(":", 1)
                else:
                    addr, alias = item, ""
                addr = addr.strip().lower()
                if addr.startswith("0x") and len(addr) == 42:
                    if addr not in self._wallets:
                        self._wallets[addr] = {
                            "alias":    alias.strip(),
                            "snapshot": None,
                            "errors":   0,
                            "last_ok":  0.0,
                        }

        if self._wallets:
            notify_info(f"Loaded {len(self._wallets)} wallet(s) to monitor")

    def _save_wallets(self) -> None:
        data = {addr: {"alias": info["alias"]} for addr, info in self._wallets.items()}
        try:
            with open(WALLETS_FILE, "w") as fh:
                json.dump(data, fh, indent=2)
        except Exception as exc:
            notify_error(f"Could not save {WALLETS_FILE}: {exc}")

    # ── public management API ─────────────────────────────────────────────────

    def add_wallet(self, address: str, alias: str = "") -> bool:
        address = address.strip().lower()
        if not address.startswith("0x") or len(address) != 42:
            console.print("[red]Invalid address — must be a 42-char hex string starting with 0x.[/red]")
            return False
        if address in self._wallets:
            console.print(f"[yellow]Wallet already tracked: {address}[/yellow]")
            return False
        self._wallets[address] = {
            "alias":    alias.strip(),
            "snapshot": None,
            "errors":   0,
            "last_ok":  0.0,
        }
        self._save_wallets()
        notify_info(f"Added wallet  {'(' + alias + ')' if alias else ''}  {address}")
        return True

    def remove_wallet(self, address: str) -> bool:
        address = address.strip().lower()
        if address not in self._wallets:
            console.print(f"[yellow]Wallet not found: {address}[/yellow]")
            return False
        del self._wallets[address]
        self._save_wallets()
        notify_info(f"Removed wallet: {address}")
        return True

    def set_alias(self, address: str, alias: str) -> bool:
        address = address.strip().lower()
        if address not in self._wallets:
            console.print(f"[yellow]Wallet not found: {address}[/yellow]")
            return False
        self._wallets[address]["alias"] = alias.strip()
        self._save_wallets()
        notify_info(f"Alias set → '{alias}' for {address}")
        return True

    def list_wallets(self) -> None:
        if not self._wallets:
            console.print("[dim]No wallets tracked. Use  add <address> [alias]  to add one.[/dim]")
            return

        tbl = Table(
            title="Tracked Wallets",
            box=box.SIMPLE_HEAVY,
            header_style="bold cyan",
            show_lines=True,
        )
        tbl.add_column("#",        style="dim",        width=3)
        tbl.add_column("Alias",    style="bold",       width=18)
        tbl.add_column("Address",  style="cyan",       width=44)
        tbl.add_column("Positions", style="white",     width=10)
        tbl.add_column("Status",   style="green",      width=10)

        for i, (addr, info) in enumerate(self._wallets.items(), 1):
            snap     = info["snapshot"] or {}
            pos_str  = str(len(snap)) if snap else "–"
            status   = "🟢 OK" if info["errors"] == 0 else f"⚠️  {info['errors']} err"
            tbl.add_row(
                str(i),
                info["alias"] or "–",
                addr,
                pos_str,
                status,
            )
        console.print(tbl)

    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    # ── monitoring engine ─────────────────────────────────────────────────────

    # Shared thread-pool for blocking requests calls
    _executor = ThreadPoolExecutor(max_workers=8)

    async def start(self) -> None:
        if self.is_running:
            console.print("[yellow]Monitor is already running.[/yellow]")
            return
        if not self._wallets:
            console.print("[yellow]No wallets added yet. Use  add <address>  first.[/yellow]")
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        notify_info(f"Monitor started — polling every {POLL_INTERVAL}s")

    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        notify_info("Monitor stopped.")

    @staticmethod
    def _blocking_fetch(address: str) -> Optional[List[dict]]:
        """Synchronous fetch — runs in a thread so Windows DNS works fine."""
        try:
            payload = {"type": "clearinghouseState", "user": address}
            resp = requests.post(
                HL_REST_URL,
                json=payload,
                timeout=12,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                return resp.json().get("assetPositions", [])
            else:
                notify_error(f"HTTP {resp.status_code} for {address[:10]}…: {resp.text[:120]}")
        except requests.exceptions.ConnectionError as exc:
            notify_error(f"Connection error for {address[:10]}…: {exc}")
        except requests.exceptions.Timeout:
            notify_error(f"Timeout fetching {address[:10]}…")
        except Exception as exc:
            notify_error(f"Unexpected error for {address[:10]}…: {exc}")
        return None

    async def _fetch_positions(self, address: str) -> Optional[List[dict]]:
        """Runs the blocking fetch in a thread — keeps the event loop free."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self._blocking_fetch, address
        )

    @staticmethod
    def _parse_positions(raw: List[dict]) -> WalletPositions:
        """Convert raw API response → dict of coin → Position."""
        result: WalletPositions = {}
        for ap in raw:
            pos = ap.get("position", {})
            try:
                szi = float(pos.get("szi", 0) or 0)
                if szi == 0.0:
                    continue                     # skip empty slots
                coin        = pos["coin"]
                entry_price = float(pos.get("entryPx", 0) or 0)
                pnl         = float(pos.get("unrealizedPnl", 0) or 0)
                lev_info    = pos.get("leverage", {}) or {}
                leverage    = lev_info.get("value") or lev_info.get("type", "cross")
                result[coin] = Position(coin, szi, entry_price, leverage, pnl)
            except (KeyError, TypeError, ValueError):
                continue
        return result

    def _diff_positions(
        self,
        wallet: str,
        alias: str,
        prev: WalletPositions,
        curr: WalletPositions,
    ) -> None:
        """Detect and fire notifications for all changes."""

        # 1️⃣  New positions (coin in curr but not in prev)
        for coin, pos in curr.items():
            if coin not in prev:
                notify_new_position(
                    wallet, alias,
                    coin, pos.side, pos.size,
                    pos.entry_price, pos.leverage,
                    pos.notional,
                )

        # 2️⃣  Closed positions (coin in prev but not in curr)
        for coin, pos in prev.items():
            if coin not in curr:
                notify_position_closed(
                    wallet, alias,
                    coin, pos.side, pos.unrealized_pnl,
                )

        # 3️⃣  Size changes (coin in both, but size differs meaningfully)
        for coin, curr_pos in curr.items():
            if coin not in prev:
                continue
            prev_pos    = prev[coin]
            delta_notional = abs(curr_pos.notional - prev_pos.notional)
            same_side      = curr_pos.side == prev_pos.side
            size_changed   = abs(curr_pos.size - prev_pos.size) > 1e-8

            if size_changed and same_side and delta_notional >= MIN_SIZE_CHANGE_USD:
                notify_size_change(
                    wallet, alias,
                    coin, curr_pos.side,
                    prev_pos.size, curr_pos.size,
                    prev_pos.notional, curr_pos.notional,
                )
            elif size_changed and not same_side:
                # Side flipped → treat as close + open
                notify_position_closed(
                    wallet, alias, coin, prev_pos.side, prev_pos.unrealized_pnl
                )
                notify_new_position(
                    wallet, alias,
                    coin, curr_pos.side, curr_pos.size,
                    curr_pos.entry_price, curr_pos.leverage,
                    curr_pos.notional,
                )

    async def _monitor_loop(self) -> None:
        while self._running:
            tick_start = time.monotonic()

            for address, info in list(self._wallets.items()):
                if not self._running:
                    break

                raw = await self._fetch_positions(address)
                if raw is None:
                    info["errors"] += 1
                    continue

                info["errors"] = 0
                info["last_ok"] = time.time()
                curr = self._parse_positions(raw)

                if info["snapshot"] is None:
                    # First poll — show current state but don't fire alerts
                    coins = list(curr.keys())
                    label = info["alias"] or f"{address[:6]}…{address[-4:]}"
                    if coins:
                        notify_info(
                            f"[bold]{label}[/bold] — initial snapshot: "
                            + ", ".join(f"[cyan]{c}[/cyan]" for c in coins)
                        )
                    else:
                        notify_info(f"[bold]{label}[/bold] — initial snapshot: no open positions")
                else:
                    self._diff_positions(address, info["alias"], info["snapshot"], curr)

                info["snapshot"] = curr

            # Sleep for remaining interval
            elapsed = time.monotonic() - tick_start
            sleep_for = max(0.1, POLL_INTERVAL - elapsed)
            await asyncio.sleep(sleep_for)
