# trading-bot-primetrade
# 🤖 Binance Futures Testnet Trading Bot

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Testnet Only](https://img.shields.io/badge/binance-testnet%20only-orange.svg)](https://testnet.binancefuture.com)

A production-grade Python trading bot for **Binance Futures Testnet (USDT-M)**, featuring a clean layered architecture, structured JSON logging, rich CLI output, and a TWAP execution engine.

> ⚠️ **This bot is configured for Binance Futures Testnet only. It uses no real funds.**

---

## ✨ Features

| Feature | Details |
|---|---|
| **MARKET orders** | Instant execution at best available price |
| **LIMIT orders** | Resting orders with configurable time-in-force |
| **STOP-LIMIT orders** | Trigger-based orders for risk management |
| **TWAP execution** | Splits large orders into time-spaced slices to minimise market impact |
| **Balance checker** | View your testnet account balances |
| **Connectivity check** | Ping the testnet before trading |
| **Structured logging** | JSON log file + coloured console output |
| **Full validation** | Symbol, side, quantity, price — all validated before hitting the API |
| **Custom exceptions** | Typed exception hierarchy for clean error handling |
| **Rich CLI** | Beautiful tables and panels via the `rich` library |

---

## 🏗️ Architecture

```
trading_bot/
├── bot/
│   ├── cli.py            # CLI layer (Typer + Rich) — user input & output
│   ├── orders.py         # Business layer — order logic & TWAP engine
│   ├── client.py         # HTTP layer — signs & sends requests to Binance
│   ├── validators.py     # Input validation — parse, don't validate
│   ├── models.py         # Typed dataclasses — OrderResponse, TWAPResult
│   ├── exceptions.py     # Custom exception hierarchy
│   └── logging_config.py # Structured JSON + coloured console logging
├── logs/                 # Runtime log files (gitignored)
├── sample_logs/          # Pre-committed proof-of-work logs
├── .env.example          # Environment variable template
├── requirements.txt
└── README.md
```

**Data flow:**
```
User → cli.py → validators.py → orders.py → client.py → Binance API
                                                              ↓
User ← cli.py ← models.py (OrderResponse) ← client.py ←────┘
```

Each layer has a **single responsibility** and can be tested independently.

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11 or higher
- A Binance Futures Testnet account (see [Setup](#-binance-testnet-setup) below)

### 2. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/trading-bot-primetrade.git
cd trading-bot-primetrade
```

### 3. Create a virtual environment

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure credentials

```bash
# Copy the template
cp .env.example .env

# Open .env and paste your testnet API key and secret
# (See Binance Testnet Setup section below)
```

Your `.env` file should look like:
```
BINANCE_API_KEY=abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
BINANCE_API_SECRET=abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
LOG_LEVEL=INFO
```

---

## 🔧 Binance Testnet Setup

### Step 1 — Create a testnet account
1. Go to **https://testnet.binancefuture.com**
2. Click **"Sign Up"** (or log in with your GitHub account — fastest option)
3. Complete registration

### Step 2 — Generate API keys
1. Log in to **https://testnet.binancefuture.com**
2. Click your profile icon (top right) → **"API Key"**
3. Click **"Generate Key"**
4. Copy and save both the **API Key** and **Secret Key** immediately (the secret is shown only once)

### Step 3 — Get testnet funds
Testnet USDT is free. On the testnet dashboard:
1. Click **"Assets"**
2. Find **USDT** → click **"Claim"** or use the faucet button
3. You'll receive 10,000 USDT testnet balance

### Step 4 — Verify connectivity
```bash
python -m bot.cli ping
```
You should see:
```
✅  Testnet reachable
   Server time: 1736932801000
```

---

## 📖 Usage

### Check connectivity
```bash
python -m bot.cli ping
```

### Check balance
```bash
python -m bot.cli balance
```

### Place a MARKET order
```bash
# BUY 0.001 BTC at market price
python -m bot.cli order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Short-form flags
python -m bot.cli order -s BTCUSDT -d BUY -t MARKET -q 0.001
```

### Place a LIMIT order
```bash
# SELL 0.001 BTC when price reaches 44000 USDT
python -m bot.cli order -s BTCUSDT -d SELL -t LIMIT -q 0.001 --price 44000

# With custom time-in-force (IOC = immediate or cancel)
python -m bot.cli order -s BTCUSDT -d BUY -t LIMIT -q 0.001 --price 42000 --tif IOC
```

### Place a STOP-LIMIT order
```bash
# Stop-loss: SELL 0.001 BTC if price drops to 40000, limit at 39900
python -m bot.cli order -s BTCUSDT -d SELL -t STOP_LIMIT -q 0.001 --price 39900 --stop-price 40000
```

### Execute TWAP strategy *(bonus feature)*
```bash
# Split 0.05 BTC BUY into 5 slices, one every 30 seconds
python -m bot.cli twap -s BTCUSDT -d BUY -q 0.05 --slices 5 --interval 30

# Dry run (simulate without placing real orders)
python -m bot.cli twap -s BTCUSDT -d BUY -q 0.05 --slices 5 --interval 5 --dry-run
```

### Get help on any command
```bash
python -m bot.cli --help
python -m bot.cli order --help
python -m bot.cli twap --help
```

---

## 📸 Screenshots

### MARKET order — success
```
╭──────────────────────────────────────────────────────╮
│      🤖  Binance Futures Testnet — Order Placement   │
╰──────────────────────────────────────────────────────╯
╭─── 📋  Order Request ───╮
│ Field       │ Value     │
│─────────────│───────────│
│ Symbol      │ BTCUSDT   │
│ Side        │ BUY       │
│ Order Type  │ MARKET    │
│ Quantity    │ 0.001     │
╰─────────────────────────╯
╭─── ✅  Order Response ──╮
│ Field           │ Value │
│─────────────────│───────│
│ Order ID        │ 32578 │
│ Status          │ FILLED│
│ Executed Qty    │ 0.001 │
│ Fill Price      │ 43251 │
╰─────────────────────────╯
╭────────────────────────────────────────────────────╮
│  ✅  Order FILLED — 0.001 BTCUSDT @ 43251.30       │
╰────────────────────────────────────────────────────╯
```

---

## 📁 Log Files

Logs are written to `logs/app.log` in newline-delimited JSON format (one object per line). This format is compatible with log aggregation tools like Datadog, CloudWatch, and Splunk.

**Sample log entry:**
```json
{
  "timestamp": "2025-01-15T09:00:01.589Z",
  "level": "INFO",
  "logger": "bot.client",
  "message": "Order placed",
  "orderId": 3257813947,
  "status": "FILLED",
  "executedQty": "0.001",
  "avgPrice": "43251.30"
}
```

Pre-recorded sample logs are in `sample_logs/`:
- `market_order_success.log` — successful MARKET order
- `limit_order_success.log` — successful LIMIT order (status: NEW, on order book)
- `failed_order.log` — validation error + API error examples

---

## 🧪 Running Tests

```bash
pytest tests/ -v
pytest tests/ --cov=bot --cov-report=term-missing
```

---

## 🛠️ Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `AuthenticationError: API_KEY … must be set` | `.env` not created or empty | `cp .env.example .env` and fill in keys |
| `APIError: -1121 Invalid symbol` | Symbol doesn't exist on testnet | Check symbol on testnet. Try `BTCUSDT` |
| `APIError: -2019 Margin is insufficient` | Not enough testnet USDT | Claim free funds on testnet dashboard |
| `NetworkError: timed out` | Firewall or VPN blocking testnet | Disable VPN or check firewall rules |
| `MissingPriceError` | LIMIT order without `--price` | Add `--price <value>` to the command |

---

## 🔮 Future Improvements

- [ ] WebSocket price feed for real-time limit order monitoring
- [ ] Database persistence (SQLite) for order history
- [ ] Grid trading strategy
- [ ] Telegram / Slack notifications on order fills
- [ ] Backtesting mode with historical data
- [ ] Docker containerisation

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `httpx` | 0.27.0 | Modern async-ready HTTP client |
| `typer` | 0.12.3 | Type-hint-driven CLI framework |
| `rich` | 13.7.1 | Beautiful terminal output |
| `python-dotenv` | 1.0.1 | Environment variable loading |

---

## 📄 Assumptions

1. All orders target **Binance Futures Testnet (USDT-M)** only — no real funds involved.
2. Quantity precision follows Binance's default LOT_SIZE filters. For BTCUSDT, minimum is 0.001.
3. TWAP slices use MARKET orders to guarantee execution.
4. The `--dry-run` flag for TWAP simulates timing but places no real orders.
5. Testnet API keys have no IP restrictions by default.

---

## 👤 Author

GORENTLA VARSHIKA  
Python Developer Intern Candidate — Primetrade.ai  

---

*Built with ❤️ for the Primetrade.ai Python Developer Internship Assignment*
