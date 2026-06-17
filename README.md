---
title: Hyperliquid Tracker
emoji: ⚡
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 4.44.1
app_file: app.py
pinned: false
python_version: 3.11
---

# HyperLiquid Wallet Tracker 🤖

A 24/7 AI agent that monitors any HyperLiquid wallet and notifies you the moment a new position is opened, closed, or resized.

## Features

| Feature | Details |
|---|---|
| **Real-time monitoring** | Polls Hyperliquid every 7 seconds (configurable) |
| **New position alerts** | Fires when a brand-new coin appears in positions |
| **Close alerts** | Fires when a position is fully closed |
| **Size change alerts** | Fires when position size changes by ≥ $100 notional |
| **Multi-wallet** | Track unlimited wallets simultaneously |
| **Aliases** | Name your wallets (e.g. "Whale A", "My Account") |
| **Persistence** | Wallets saved to `wallets.json`, reloaded on restart |
| **Notifications** | Console (always) + Telegram + Discord |

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure notifications (optional)
```bash
copy .env.example .env
# Edit .env with your Telegram / Discord credentials
```

### 3. Run the agent
```bash
python main.py
```

---

## CLI Commands

```
add <address> [alias]    Track a new wallet address
remove <address>         Stop tracking a wallet
alias <address> <name>   Set or update alias for a wallet
list                     Show all tracked wallets
start                    Start the 24/7 monitoring agent
stop                     Pause the monitoring agent
status                   Show current agent status
help                     Show help
exit / quit              Exit
```

### Example session
```
[HL-Tracker] >> add 0xAbCd...1234 Whale Alpha
[HL-Tracker] >> add 0xDeFg...5678 My Account
[HL-Tracker] >> list
[HL-Tracker] >> start
```

---

## Setting Up Notifications

### Telegram
1. Message [@BotFather](https://t.me/BotFather) → `/newbot`
2. Copy the token into `TELEGRAM_BOT_TOKEN` in `.env`
3. Start your bot, then visit:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Copy `chat.id` into `TELEGRAM_CHAT_ID` in `.env`

### Discord
1. Go to your server → channel settings → **Integrations** → **Webhooks** → **New Webhook**
2. Copy the URL into `DISCORD_WEBHOOK_URL` in `.env`

---

## Alert Example

### Console
```
╔══════════════════════════════════════╗
║  🟢  NEW POSITION OPENED
╠══════════════════════════════════════╣
║  Wallet:   Whale Alpha
║  Coin:     BTC
║  Side:     LONG
║  Size:     0.5000  (~$33,500)
║  Entry:    $67,000.0000
║  Leverage: 10x
║  Time:     2026-06-17 07:14:00 UTC
╚══════════════════════════════════════╝
```

---

## Configuration (``.env``)

| Variable | Default | Description |
|---|---|---|
| `POLL_INTERVAL` | `7` | Seconds between polls |
| `TELEGRAM_BOT_TOKEN` | — | Your Telegram bot token |
| `TELEGRAM_CHAT_ID` | — | Your Telegram chat/user ID |
| `DISCORD_WEBHOOK_URL` | — | Discord channel webhook URL |
| `NOTIFY_NEW_POSITION` | `true` | Alert on new positions |
| `NOTIFY_POSITION_CLOSED` | `true` | Alert on closed positions |
| `NOTIFY_SIZE_CHANGE` | `true` | Alert on size changes |
| `MIN_SIZE_CHANGE_USD` | `100` | Min $ change to trigger size alert |

---

## File Structure

```
hyperliquid-wallet-tracker/
├── main.py          # CLI entrypoint
├── agent.py         # Core monitoring engine
├── notifier.py      # Alert dispatcher (console / Telegram / Discord)
├── config.py        # Config loader
├── requirements.txt
├── .env.example     # Template — copy to .env
├── wallets.json     # Auto-generated, stores your wallet list
└── README.md
```
