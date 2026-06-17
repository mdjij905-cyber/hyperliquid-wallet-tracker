import gradio as gr
import asyncio
import threading
import time
from agent import WalletMonitor
import notifier

# Initialize the wallet monitor
monitor = WalletMonitor()

# Background monitor thread runner
def run_monitor():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Start monitor
    loop.run_until_complete(monitor.start())
    # Keep running
    loop.run_forever()

# Start background thread
thread = threading.Thread(target=run_monitor, daemon=True)
thread.start()

# Functions for Gradio UI
def get_logs():
    if not notifier.LOG_MESSAGES:
        return "System initializing... Waiting for logs."
    return "\n".join(notifier.LOG_MESSAGES)

def get_status():
    status = "🟢 RUNNING" if monitor.is_running else "🔴 INACTIVE"
    wallets_count = len(monitor._wallets)
    return f"Status: {status}\nTracked Wallets: {wallets_count} active"

def get_wallets_list():
    if not monitor._wallets:
        return "No wallets configured. Add wallets via the TRACKED_WALLETS environment variable."
    lines = []
    for addr, info in monitor._wallets.items():
        alias = info.get("alias", "No Alias")
        lines.append(f"• {alias} ({addr})")
    return "\n".join(lines)

# Create Gradio blocks interface with a dark modern tech theme
with gr.Blocks(title="Hyperliquid Wallet Tracker Dashboard", theme=gr.themes.Default()) as demo:
    gr.Markdown("# ⚡ Hyperliquid Wallet Tracker Dashboard")
    gr.Markdown("This AI agent runs 24/7 in the cloud to monitor trades and send instant Telegram notifications.")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📊 Agent Status")
            status_box = gr.Textbox(label="Agent State", value=get_status, every=2)
            
            gr.Markdown("### 👤 Tracked Wallets")
            wallets_box = gr.Textbox(label="Configured Wallets", value=get_wallets_list, every=5)
            
        with gr.Column(scale=2):
            gr.Markdown("### 📜 Live Logs")
            logs_box = gr.TextArea(label="Bot Activity Logs (Refreshes Live)", value=get_logs, every=2, lines=15)

# Launch (Hugging Face Spaces automatically exposes port 7860)
demo.launch(server_name="0.0.0.0", server_port=7860)
