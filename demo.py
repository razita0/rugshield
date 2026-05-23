#!/usr/bin/env python3
"""
RugShield Demo — Visual scan output demonstration
"""

import asyncio
import sys
from datetime import datetime

# ANSI colors
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

def print_header():
    print(f"""
{Colors.RED}{Colors.BOLD}
    ╔══════════════════════════════════════════════════════════════╗
    ║  🛡️  RUGSHIELD — Rug-Pull Early Warning System              ║
    ║  Powered by Hermes Agent + Xiaomi MiMo V2.5                 ║
    ╚══════════════════════════════════════════════════════════════╝
{Colors.RESET}""")

def print_scan_result(token, risk_score, chain, flags):
    level_color = Colors.GREEN if risk_score < 30 else Colors.YELLOW if risk_score < 60 else Colors.RED
    level_text = "LOW" if risk_score < 30 else "MEDIUM" if risk_score < 60 else "CRITICAL"
    
    print(f"""{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 SCAN RESULT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.RESET}

  {Colors.BOLD}Token:{Colors.RESET}     {token['address']}
  {Colors.BOLD}Name:{Colors.RESET}      {token['name']} ({token['symbol']})
  {Colors.BOLD}Chain:{Colors.RESET}     {chain.upper()}
  {Colors.BOLD}Deployer:{Colors.RESET}  {token['deployer']}
  
  {Colors.BOLD}Risk Score:{Colors.RESET} {level_color}{Colors.BOLD}{risk_score}/100 ({level_text}){Colors.RESET}
  
  {Colors.BOLD}Red Flags:{Colors.RESET}""")
    for flag in flags:
        print(f"    {flag}")
    
    print(f"""
  {Colors.BOLD}Recommendation:{Colors.RESET} {Colors.RED}⛔ DO NOT BUY — High rug risk detected{Colors.RESET}
""")

def print_monitoring():
    print(f"""{Colors.GREEN}
┌──────────────────────────────────────────────────────────────┐
│  📡 MONITORING ACTIVE                                        │
├──────────────────────────────────────────────────────────────┤
│  Chain: Base                         Status: ● LIVE           │
│  Watching: 1 factory contract        Pairs scanned: 847       │
│  Alerts sent: 12                     Uptime: 2h 34m           │
│                                                              │
│  Last scan: 2 seconds ago                                    │
│  New pairs/hour: ~150                                        │
└──────────────────────────────────────────────────────────────┘{Colors.RESET}
""")

def print_alert():
    print(f"""{Colors.RED}{Colors.BOLD}
🚨 ═══════════════════════════════════════════════════════════
   RUGSHIELD ALERT — CRITICAL
═══════════════════════════════════════════════════════════{Colors.RESET}

  Token: {Colors.CYAN}0x1a2b3c4d5e6f7890abcdef1234567890abcdef12{Colors.RESET}
  Name:  SafeMoonKiller (SKILL)
  Chain: BASE
  
  {Colors.RED}Risk Score: 87/100 (CRITICAL){Colors.RESET}
  
  {Colors.YELLOW}⚠️  Red Flags Detected:{Colors.RESET}
    ❌ Liquidity NOT locked
    ❌ Honeypot detected — cannot sell
    ❌ 92% supply in top 3 wallets
    ❌ Contract NOT verified
    ⚠️ Deployer wallet is 2 hours old
    ⚠️ 45% sell tax detected
  
  📊 Full Report: https://rugshield.xyz/token/0x1a2b...ef12
  🔗 Scan with RugShield: python -m src.agent --check 0x1a2b...

{Colors.RED}═══════════════════════════════════════════════════════════{Colors.RESET}
""")

def main():
    print_header()
    print_monitoring()
    print_alert()
    
    # Sample scan result
    token = {
        "address": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
        "name": "LuckyMoon",
        "symbol": "LMOON",
        "deployer": "0x9f8e7d6c5b4a3210fedcba9876543210fedcba98"
    }
    
    flags = [
        f"{Colors.RED}❌ Liquidity NOT locked{Colors.RESET}",
        f"{Colors.YELLOW}⚠️ Deployer wallet is < 24 hours old{Colors.RESET}",
        f"{Colors.RED}❌ Contract NOT verified{Colors.RESET}",
        f"{Colors.YELLOW}⚠️ High sell tax: 35%{Colors.RESET}",
        f"{Colors.YELLOW}⚠️ Top 10 holders own 87%{Colors.RESET}",
    ]
    
    print_scan_result(token, 72, "base", flags)
    
    print(f"""{Colors.GREEN}{Colors.BOLD}
✅ RugShield is monitoring 3 chains (Base, Arbitrum, Linea)
🚀 Ready to protect DeFi traders from rug-pulls
{Colors.RESET}""")

if __name__ == "__main__":
    main()
