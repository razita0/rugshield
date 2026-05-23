# 🛡️ RugShield — Rug-Pull Early Warning System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat)
![Chain](https://img.shields.io/badge/Chains-EVM%20%7C%20Solana-purple?style=flat)

**Real-time rug-pull detection & token safety scoring for DeFi traders.**

</div>

---

## 📋 Overview

RugShield is an AI-powered early warning system that analyzes newly deployed tokens across EVM chains (Base, Linea, Arbitrum) and Solana to detect potential rug-pulls before they happen.

### 🎯 Key Features

| Feature | Description |
|---------|-------------|
| **Liquidity Lock Detection** | Checks if LP tokens are locked via major locker contracts (Team.Finance, Unicrypt, etc.) |
| **Deployer Wallet Age** | Flags fresh wallets deploying contracts (high risk pattern) |
| **Honeypot Detection** | Simulates buy/sell to detect if selling is blocked or heavily taxed |
| **Holder Distribution** | Analyzes concentration risk — whale dominance = red flag |
| **Contract Verification** | Checks source code verification status & suspicious patterns |
| **Real-time Alerts** | Instant notification via Telegram/Discord when risk threshold breached |

### 🧠 How It Works

```
Token Deployed → Contract Analysis → On-Chain Simulation → Risk Scoring → Alert
     ↓                  ↓                   ↓                  ↓           ↓
  Event Listener    Bytecode Check    Buy/Sell Sim       ML Model     Telegram/Discord
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- RPC endpoint (Alchemy, QuickNode, or public RPC)
- Optional: Telegram/Discord webhook for alerts

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/rugshield.git
cd rugshield

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy example config
cp configs/default.yaml.example configs/default.yaml

# Edit your settings
vim configs/default.yaml
```

### Run

```bash
# Monitor Base chain
python -m src.agent --chain base

# Monitor multiple chains
python -m src.agent --chain base,arb,linea

# One-shot token check
python -m src.agent --check 0x1234...abcd
```

---

## 📊 Risk Score Breakdown

| Score | Risk Level | Meaning |
|-------|------------|---------|
| 0-20 | 🟢 **LOW** | Multiple safety signals present |
| 21-40 | 🟡 **MEDIUM** | Some concerns, proceed with caution |
| 41-60 | 🟠 **HIGH** | Multiple red flags detected |
| 61-80 | 🔴 **CRITICAL** | Strong rug-pull indicators |
| 81-100 | ⚫ **SCAM** | Near-certain rug or honeypot |

### Scoring Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| `liquidity_locked` | 25% | LP locked via recognized locker |
| `deployer_age` | 15% | Wallet age before deploy |
| `honeypot_check` | 25% | Can sell successfully? |
| `holder_distribution` | 15% | Top 10 holder concentration |
| `contract_verified` | 10% | Source code verified on explorer |
| `tax_analysis` | 10% | Buy/sell tax reasonable? |

---

## 🏗️ Architecture

```
rugshield/
├── src/
│   ├── agent.py           # Main orchestrator
│   ├── core/
│   │   ├── scanner.py     # Token scanner engine
│   │   ├── scorer.py      # Risk scoring logic
│   │   └── contracts.py   # Known contract ABIs & addresses
│   ├── chains/
│   │   ├── evm.py         # EVM chain handler (Base, Arb, Linea)
│   │   └── solana.py      # Solana chain handler
│   ├── alerts/
│   │   ├── telegram.py    # Telegram bot integration
│   │   └── discord.py     # Discord webhook integration
│   └── models/
│       └── token.py       # Token data models
├── configs/
│   └── default.yaml       # Configuration template
├── scripts/
│   └── backfill.py        # Historical analysis script
└── tests/
    └── test_scanner.py    # Unit tests
```

---

## 🔧 Configuration Reference

```yaml
# configs/default.yaml
chains:
  base:
    rpc: "https://mainnet.base.org"
    enabled: true
    factory: "0x...UniswapV2Factory"
  arbitrum:
    rpc: "https://arb1.arbitrum.io/rpc"
    enabled: true
  linea:
    rpc: "https://rpc.linea.build"
    enabled: true

scoring:
  thresholds:
    low: 20
    medium: 40
    high: 60
    critical: 80

alerts:
  telegram:
    enabled: true
    bot_token: "${TELEGRAM_BOT_TOKEN}"
    chat_id: "${TELEGRAM_CHAT_ID}"
  discord:
    enabled: false
    webhook_url: "${DISCORD_WEBHOOK}"

honeypot:
  simulation_amount: "0.01"  # ETH for simulation
  max_gas_limit: 3000000
```

---

## 🧪 Example Alert

```
🚨 RUGSHIELD ALERT — CRITICAL (Score: 87)

Token: 0x1a2b...3c4d
Name: SafeMoonKiller (SKILL)
Chain: Base
Deployer: 0x9f8e...7d6c (Age: 2 hours)

⚠️ Red Flags:
• ❌ Liquidity NOT locked
• ❌ Honeypot detected — cannot sell
• ❌ 92% supply in top 3 wallets
• ❌ Contract NOT verified
• ⚠️ Deployer wallet is 2 hours old
• ⚠️ 45% sell tax detected

📊 Full Report: https://rugshield.xyz/token/0x1a2b...3c4d
```

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## ⚠️ Disclaimer

RugShield provides automated risk analysis for informational purposes only. No system can guarantee 100% accuracy. Always DYOR (Do Your Own Research) before investing.

---

## 🔗 Links

- [Xiaomi MiMo API](https://platform.xiaomimimo.com)
- [Documentation](https://rugshield.xyz/docs)
- [Discord Community](https://discord.gg/rugshield)

---

<div align="center">

**Built with ❤️ using Hermes Agent + Xiaomi MiMo**

</div>
