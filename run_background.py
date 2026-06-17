"""
run_background.py — Runs the HyperLiquid Wallet Tracker in the background.

Use this script to run the bot 24/7 without needing to keep a terminal window open.
To run:
    pythonw run_background.py

To stop:
    Stop the 'pythonw.exe' process in Task Manager.
"""

import asyncio
import sys

# Force SelectorEventLoop on Windows to avoid DNS resolution issues with asyncio/requests
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from agent import WalletMonitor
from notifier import notify_info

async def main():
    monitor = WalletMonitor()
    if not monitor._wallets:
        notify_info("No wallets to track. Please run 'python main.py' and add wallets first.")
        return

    # Start the monitor loop
    await monitor.start()
    
    # Keep the script running forever
    while monitor.is_running:
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
