#!/usr/bin/env python3
"""
Quick token analysis script.
Usage: python scripts/analyze.py <chain> <token_address>
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import RugShieldAgent, load_config


async def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/analyze.py <chain> <token_address>")
        print("Example: python scripts/analyze.py base 0x1234...abcd")
        sys.exit(1)
    
    chain = sys.argv[1]
    token_address = sys.argv[2]
    
    print(f"\n🔍 Analyzing token: {token_address}")
    print(f"📡 Chain: {chain}\n")
    
    config = load_config()
    agent = RugShieldAgent(config)
    
    try:
        await agent.initialize()
        result = await agent.scan_token(chain, token_address)
        
        print("=" * 50)
        print(f"Token: {result.get('name', 'Unknown')} ({result.get('symbol', '???')})")
        print(f"Chain: {result.get('chain', chain).upper()}")
        print("-" * 50)
        print(f"Risk Score: {result.get('risk_score', 0)}/100")
        print(f"Risk Level: {result.get('risk_level', 'unknown').upper()}")
        print(f"Safe: {'✅ Yes' if result.get('is_safe') else '❌ No'}")
        print(f"Dangerous: {'⚠️ Yes' if result.get('is_dangerous') else '✅ No'}")
        print("-" * 50)
        
        flags = result.get('red_flags', [])
        if flags:
            print("Red Flags:")
            for flag in flags:
                print(f"  {flag}")
        else:
            print("No red flags detected! 🎉")
        
        print("=" * 50)
        
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
