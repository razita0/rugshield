"""
RugShield Agent — Main orchestrator for rug-pull detection.
Monitors chains, scans tokens, and sends alerts.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from datetime import datetime
from typing import Any, Optional

from src.alerts import (
    AlertProvider,
    MultiAlertManager,
    create_discord_alerter,
    create_telegram_alerter,
)
from src.chains.evm import EVMChainHandler, EVMEvent, get_chain_config
from src.core.scanner import RiskLevel, TokenScanner
from src.models.token import Alert, AlertPriority, ChainConfig, ChainType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rugshield")


class RugShieldAgent:
    """
    Main agent for rug-pull detection.
    
    Orchestrates chain monitoring, token scanning, and alerting.
    """
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.chains: dict[str, EVMChainHandler] = {}
        self.alert_manager = MultiAlertManager()
        self.scanners: dict[str, TokenScanner] = {}
        self.is_running = False
        self._scan_cache: dict[str, datetime] = {}  # Prevent duplicate scans
        
    async def initialize(self) -> None:
        """Initialize all components."""
        logger.info("🛡️ RugShield Agent initializing...")
        
        # Setup chains
        await self._setup_chains()
        
        # Setup alert providers
        await self._setup_alerts()
        
        logger.info(f"✅ RugShield initialized with {len(self.chains)} chains")
    
    async def _setup_chains(self) -> None:
        """Setup chain handlers from config."""
        chains_config = self.config.get("chains", {})
        
        for chain_name, chain_conf in chains_config.items():
            if not chain_conf.get("enabled", False):
                continue
                
            handler = EVMChainHandler(
                chain_name=chain_name,
                rpc_url=chain_conf.get("rpc", ""),
            )
            
            if await handler.connect():
                self.chains[chain_name] = handler
                self.scanners[chain_name] = TokenScanner(
                    rpc_url=chain_conf.get("rpc", ""),
                    chain=chain_name,
                )
                logger.info(f"  ✓ {chain_name} connected")
            else:
                logger.warning(f"  ✗ {chain_name} connection failed")
    
    async def _setup_alerts(self) -> None:
        """Setup alert providers from config."""
        alerts_config = self.config.get("alerts", {})
        
        # Telegram
        telegram_conf = alerts_config.get("telegram", {})
        if telegram_conf.get("enabled", False):
            alerter = create_telegram_alerter(telegram_conf)
            if alerter:
                self.alert_manager.add_provider("telegram", alerter)
        
        # Discord
        discord_conf = alerts_config.get("discord", {})
        if discord_conf.get("enabled", False):
            alerter = create_discord_alerter(discord_conf)
            if alerter:
                self.alert_manager.add_provider("discord", alerter)
        
        # Test connections
        if self.alert_manager.providers:
            results = await self.alert_manager.test_all_connections()
            for name, ok in results.items():
                status = "✓" if ok else "✗"
                logger.info(f"  {status} Alert provider: {name}")
    
    async def start_monitoring(self) -> None:
        """Start monitoring all enabled chains."""
        if not self.chains:
            logger.error("No chains configured!")
            return
        
        self.is_running = True
        logger.info("🚀 Starting chain monitoring...")
        
        tasks = []
        for chain_name, handler in self.chains.items():
            chain_conf = self.config.get("chains", {}).get(chain_name, {})
            factory_addresses = chain_conf.get("factory_addresses", [])
            
            for factory in factory_addresses:
                task = asyncio.create_task(
                    self._monitor_factory(chain_name, handler, factory),
                    name=f"monitor-{chain_name}-{factory[:8]}",
                )
                tasks.append(task)
        
        logger.info(f"Monitoring {len(tasks)} factory contracts across {len(self.chains)} chains")
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Monitoring cancelled")
        finally:
            self.is_running = False
    
    async def _monitor_factory(
        self,
        chain_name: str,
        handler: EVMChainHandler,
        factory_address: str,
    ) -> None:
        """Monitor a DEX factory for new pair creations."""
        logger.info(f"  Watching {chain_name} factory: {factory_address}")
        
        async def on_new_pair(event: EVMEvent) -> None:
            """Handle new pair created event."""
            token0 = event.args.get("token0", "")
            token1 = event.args.get("token1", "")
            pair_address = event.args.get("pair", "")
            
            # Determine which token is likely the new token (not WETH/stablecoin)
            new_token = self._identify_new_token(chain_name, token0, token1)
            
            if new_token:
                logger.info(f"🔍 New pair detected on {chain_name}: {pair_address}")
                logger.info(f"   Token: {new_token}")
                
                # Prevent duplicate scans within 5 minutes
                cache_key = f"{chain_name}:{new_token}"
                if cache_key in self._scan_cache:
                    age = (datetime.utcnow() - self._scan_cache[cache_key]).seconds
                    if age < 300:
                        logger.info(f"   Skipping (scanned {age}s ago)")
                        return
                
                self._scan_cache[cache_key] = datetime.utcnow()
                
                # Scan the token
                await self._scan_and_alert(chain_name, new_token, pair_address)
        
        await handler.watch_new_pairs(
            factory_address=factory_address,
            callback=on_new_pair,
        )
    
    def _identify_new_token(
        self,
        chain_name: str,
        token0: str,
        token1: str,
    ) -> Optional[str]:
        """Identify which token in a pair is the new/interesting one."""
        # Known stablecoin/WETH addresses per chain
        known_tokens = {
            "base": [
                "0x4200000000000000000000000000000000000006",  # WETH
                "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC
            ],
            "arbitrum": [
                "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",  # WETH
                "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",  # USDC
            ],
            "linea": [
                "0xe5D7C2a44FfDf6b19c41F70b5693FD5393b96075",  # WETH
            ],
        }
        
        known = [t.lower() for t in known_tokens.get(chain_name, [])]
        
        if token0.lower() in known:
            return token1
        if token1.lower() in known:
            return token0
        
        # Return token0 as default
        return token0
    
    async def _scan_and_alert(
        self,
        chain_name: str,
        token_address: str,
        pair_address: str,
    ) -> None:
        """Scan a token and send alert if risky."""
        try:
            scanner = self.scanners.get(chain_name)
            if not scanner:
                return
            
            result = await scanner.scan_token(token_address)
            
            # Check if risk exceeds threshold
            thresholds = self.config.get("scoring", {}).get("thresholds", {})
            alert_threshold = thresholds.get("medium", 40)
            
            if result.risk_score >= alert_threshold:
                # Create and send alert
                alert = Alert(
                    alert_id=str(uuid.uuid4())[:8],
                    chain=chain_name,
                    token_address=token_address,
                    token_name=result.token.name,
                    token_symbol=result.token.symbol,
                    risk_score=result.risk_score,
                    risk_level=result.risk_level.value,
                    priority=self._score_to_priority(result.risk_score),
                    red_flags=result.red_flags,
                    deployer=result.token.deployer,
                    pair_address=pair_address,
                    liquidity_usd=result.liquidity.liquidity_usd if result.liquidity else 0,
                )
                
                results = await self.alert_manager.send_alert(alert)
                logger.warning(
                    f"🚨 Alert sent for {result.token.symbol} "
                    f"(score: {result.risk_score}) - {results}"
                )
            else:
                logger.info(
                    f"✅ Token {result.token.symbol} passed "
                    f"(score: {result.risk_score})"
                )
                
        except Exception as e:
            logger.error(f"Scan failed for {token_address}: {e}", exc_info=True)
    
    @staticmethod
    def _score_to_priority(score: int) -> AlertPriority:
        """Convert risk score to alert priority."""
        if score >= 80:
            return AlertPriority.EMERGENCY
        elif score >= 60:
            return AlertPriority.CRITICAL
        elif score >= 40:
            return AlertPriority.WARNING
        return AlertPriority.INFO
    
    async def scan_token(self, chain: str, token_address: str) -> dict[str, Any]:
        """
        One-shot token scan.
        
        Returns:
            Dictionary with scan results
        """
        scanner = self.scanners.get(chain)
        if not scanner:
            return {"error": f"Chain {chain} not configured"}
        
        result = await scanner.scan_token(token_address)
        
        return {
            "token": result.token.address,
            "name": result.token.name,
            "symbol": result.token.symbol,
            "chain": result.token.chain,
            "risk_score": result.risk_score,
            "risk_level": result.risk_level.value,
            "red_flags": result.red_flags,
            "is_safe": result.is_safe,
            "is_dangerous": result.is_dangerous,
        }
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the agent."""
        logger.info("Shutting down RugShield...")
        self.is_running = False
        await self.alert_manager.close_all()
        logger.info("RugShield shutdown complete")


def load_config(config_path: str = "configs/default.yaml") -> dict[str, Any]:
    """Load configuration from YAML file."""
    import yaml
    
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded config from {config_path}")
        return config or {}
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}, using defaults")
        return get_default_config()


def get_default_config() -> dict[str, Any]:
    """Get default configuration."""
    return {
        "chains": {
            "base": {
                "rpc": "https://mainnet.base.org",
                "enabled": True,
                "factory_addresses": [
                    "0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6",
                ],
            },
        },
        "scoring": {
            "thresholds": {
                "low": 20,
                "medium": 40,
                "high": 60,
                "critical": 80,
            }
        },
        "alerts": {
            "telegram": {"enabled": False},
            "discord": {"enabled": False},
        },
    }


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="RugShield - Rug-Pull Detection")
    parser.add_argument("--chain", default="base", help="Chain to monitor")
    parser.add_argument("--check", help="Token address to scan (one-shot)")
    parser.add_argument("--config", default="configs/default.yaml", help="Config file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    config = load_config(args.config)
    agent = RugShieldAgent(config)
    
    try:
        await agent.initialize()
        
        if args.check:
            # One-shot scan mode
            result = await agent.scan_token(args.chain, args.check)
            print("\n📊 Scan Result:")
            for key, value in result.items():
                print(f"  {key}: {value}")
        else:
            # Monitor mode
            await agent.start_monitoring()
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
