"""
main.py — Interactive CLI for the HyperLiquid Wallet Tracker agent.

Run with:
    python main.py

Commands:
    add <address> [alias]   — track a wallet
    remove <address>        — stop tracking
    alias <address> <name>  — set / change alias
    list                    — show tracked wallets
    start                   — begin 24/7 monitoring
    stop                    — pause monitoring
    status                  — show monitor status
    help                    — show this help
    exit / quit             — exit the program
"""

import asyncio
import sys

# ── Windows fix: ProactorEventLoop (default on Win) breaks aiohttp DNS ────────
# Force SelectorEventLoop so aiohttp can resolve hostnames correctly.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich import box

from agent import WalletMonitor

console = Console()
monitor = WalletMonitor()


# ─── banner ───────────────────────────────────────────────────────────────────

BANNER = """
[bold cyan]
 ██╗  ██╗██╗     ████████╗██████╗  █████╗  ██████╗██╗  ██╗███████╗██████╗
 ██║  ██║██║     ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗
 ███████║██║        ██║   ██████╔╝███████║██║     █████╔╝ █████╗  ██████╔╝
 ██╔══██║██║        ██║   ██╔══██╗██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗
 ██║  ██║███████╗   ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██║  ██║
 ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
[/bold cyan]
[dim]  HyperLiquid Wallet Tracker  |  AI Agent  |  24/7 Monitoring[/dim]
"""

HELP_TEXT = """[bold]Commands[/bold]

  [cyan]add[/cyan] [white]<address> [alias][/white]    Track a new wallet address (alias is optional)
  [cyan]remove[/cyan] [white]<address>[/white]          Stop tracking a wallet
  [cyan]alias[/cyan] [white]<address> <name>[/white]    Set or update the alias for a wallet
  [cyan]list[/cyan]                      Show all tracked wallets and their status
  [cyan]start[/cyan]                     Start the 24/7 monitoring agent
  [cyan]stop[/cyan]                      Pause the monitoring agent
  [cyan]status[/cyan]                    Show current agent status
  [cyan]help[/cyan]                      Show this help message
  [cyan]exit[/cyan] / [cyan]quit[/cyan]              Exit the program

[dim]Configuration:  Copy .env.example → .env and fill in Telegram / Discord credentials
Wallets are auto-saved to wallets.json and reloaded on next startup.[/dim]
"""


# ─── command handlers ─────────────────────────────────────────────────────────

def cmd_add(parts):
    if len(parts) < 2:
        console.print("[yellow]Usage: add <address> [alias][/yellow]")
        return
    address = parts[1]
    alias   = " ".join(parts[2:]) if len(parts) > 2 else ""
    added   = monitor.add_wallet(address, alias)
    if added and monitor.is_running:
        console.print("[dim]Wallet added — will be included in the next poll cycle.[/dim]")


def cmd_remove(parts):
    if len(parts) < 2:
        console.print("[yellow]Usage: remove <address>[/yellow]")
        return
    monitor.remove_wallet(parts[1])


def cmd_alias(parts):
    if len(parts) < 3:
        console.print("[yellow]Usage: alias <address> <name>[/yellow]")
        return
    monitor.set_alias(parts[1], " ".join(parts[2:]))


def cmd_start():
    asyncio.get_event_loop().create_task(monitor.start())


def cmd_stop():
    monitor.stop()


def cmd_status():
    state = "[bold green]● RUNNING[/bold green]" if monitor.is_running else "[bold red]○ STOPPED[/bold red]"
    console.print(Panel(state, title="Monitor Status", box=box.ROUNDED, width=30))


# ─── main REPL ────────────────────────────────────────────────────────────────

DISPATCH = {
    "add":    cmd_add,
    "remove": cmd_remove,
    "alias":  cmd_alias,
    "list":   lambda _: monitor.list_wallets(),
    "start":  lambda _: cmd_start(),
    "stop":   lambda _: cmd_stop(),
    "status": lambda _: cmd_status(),
    "help":   lambda _: console.print(Panel(HELP_TEXT, title="Help", box=box.ROUNDED)),
}


async def repl():
    console.print(BANNER)
    console.print(Panel(HELP_TEXT, title="Quick Help", box=box.ROUNDED))

    loop = asyncio.get_event_loop()

    # Auto-start if wallets were loaded from disk
    if monitor._wallets:
        console.print("[dim]Wallets loaded from disk — type [bold]start[/bold] to begin monitoring.[/dim]\n")

    while True:
        try:
            raw = await loop.run_in_executor(None, lambda: input("\n[HL-Tracker] >> "))
        except (EOFError, KeyboardInterrupt):
            break

        raw   = raw.strip()
        parts = raw.split()
        if not parts:
            continue

        action = parts[0].lower()

        if action in ("exit", "quit"):
            break
        elif action in DISPATCH:
            try:
                DISPATCH[action](parts)
            except Exception as exc:
                console.print(f"[red]Error: {exc}[/red]")
        else:
            console.print(f"[yellow]Unknown command: '{action}'. Type 'help' for a list of commands.[/yellow]")

        # Small yield so async tasks (monitor loop) can run
        await asyncio.sleep(0.05)

    monitor.stop()
    console.print("\n[dim]Goodbye! 👋[/dim]")


def main():
    try:
        asyncio.run(repl())
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted. Goodbye![/dim]")
        sys.exit(0)


if __name__ == "__main__":
    main()
