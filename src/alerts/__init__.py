"""
RugShield Alert Modules — Telegram and Discord notifications.
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import aiohttp

from src.models.token import Alert, AlertPriority

logger = logging.getLogger(__name__)


class AlertProvider(ABC):
    """Base class for alert providers."""
    
    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """Send an alert. Returns True if successful."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the provider is properly configured."""
        pass


class TelegramAlert(AlertProvider):
    """
    Telegram alert provider using Bot API.
    
    Setup:
        1. Create bot via @BotFather
        2. Get bot token
        3. Add bot to your group/channel
        4. Get chat_id using getUpdates or @userinfobot
    """
    
    BASE_URL = "https://api.telegram.org/bot"
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"{self.BASE_URL}{bot_token}"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def send(self, alert: Alert) -> bool:
        """Send alert to Telegram."""
        try:
            session = await self._get_session()
            message = alert.format_telegram()
            
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }
            
            url = f"{self.api_url}/sendMessage"
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    logger.info(f"Telegram alert sent: {alert.alert_id}")
                    return True
                else:
                    text = await resp.text()
                    logger.error(f"Telegram send failed: {resp.status} - {text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Telegram alert error: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test Telegram bot connection."""
        try:
            session = await self._get_session()
            url = f"{self.api_url}/getMe"
            async with session.get(url) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()


class DiscordAlert(AlertProvider):
    """
    Discord alert provider using Webhooks.
    
    Setup:
        1. Go to Server Settings > Integrations > Webhooks
        2. Create new webhook
        3. Copy webhook URL
    """
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def _get_embed_color(self, priority: AlertPriority) -> int:
        """Get embed color based on priority."""
        colors = {
            AlertPriority.INFO: 0x3498DB,      # Blue
            AlertPriority.WARNING: 0xF39C12,   # Orange
            AlertPriority.CRITICAL: 0xE74C3C,  # Red
            AlertPriority.EMERGENCY: 0x8E44AD, # Purple
        }
        return colors.get(priority, 0x95A5A6)
    
    async def send(self, alert: Alert) -> bool:
        """Send alert as Discord embed."""
        try:
            session = await self._get_session()
            
            flags_text = "\n".join(alert.red_flags[:8])
            
            embed = {
                "title": f"🚨 RUGSHIELD ALERT — {alert.risk_level.upper()}",
                "color": self._get_embed_color(alert.priority),
                "fields": [
                    {"name": "Token", "value": f"`{alert.token_address}`", "inline": False},
                    {"name": "Name", "value": f"{alert.token_name} ({alert.token_symbol})", "inline": True},
                    {"name": "Chain", "value": alert.chain.upper(), "inline": True},
                    {"name": "Risk Score", "value": f"`{alert.risk_score}/100`", "inline": True},
                    {"name": "Liquidity", "value": f"${alert.liquidity_usd:,.2f}", "inline": True},
                    {"name": "Deployer", "value": f"`{alert.deployer}`", "inline": False},
                    {"name": "Red Flags", "value": flags_text or "None detected", "inline": False},
                ],
                "timestamp": alert.timestamp.isoformat(),
                "footer": {"text": "RugShield • AI-Powered Rug Detection"},
            }
            
            payload = {"embeds": [embed]}
            
            async with session.post(self.webhook_url, json=payload) as resp:
                if resp.status in (200, 204):
                    logger.info(f"Discord alert sent: {alert.alert_id}")
                    return True
                else:
                    text = await resp.text()
                    logger.error(f"Discord send failed: {resp.status} - {text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Discord alert error: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test Discord webhook connection."""
        try:
            session = await self._get_session()
            test_payload = {
                "content": "🛡️ RugShield webhook test — connection successful!",
                "flags": 64,  # Ephemeral
            }
            async with session.post(self.webhook_url, json=test_payload) as resp:
                return resp.status in (200, 204)
        except Exception as e:
            logger.error(f"Discord connection test failed: {e}")
            return False
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()


class MultiAlertManager:
    """
    Manager for multiple alert providers.
    Sends alerts to all configured providers.
    """
    
    def __init__(self):
        self.providers: dict[str, AlertProvider] = {}
    
    def add_provider(self, name: str, provider: AlertProvider) -> None:
        """Add an alert provider."""
        self.providers[name] = provider
        logger.info(f"Added alert provider: {name}")
    
    def remove_provider(self, name: str) -> None:
        """Remove an alert provider."""
        if name in self.providers:
            del self.providers[name]
    
    async def send_alert(self, alert: Alert) -> dict[str, bool]:
        """Send alert to all providers."""
        results = {}
        
        tasks = []
        for name, provider in self.providers.items():
            tasks.append(self._send_to_provider(name, provider, alert))
        
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for name, result in zip(self.providers.keys(), task_results):
            if isinstance(result, Exception):
                results[name] = False
                logger.error(f"Alert to {name} failed: {result}")
            else:
                results[name] = result
        
        return results
    
    async def _send_to_provider(
        self,
        name: str,
        provider: AlertProvider,
        alert: Alert,
    ) -> bool:
        """Send alert to a single provider with retry."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                success = await provider.send(alert)
                if success:
                    return True
                logger.warning(f"Alert to {name} failed (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Alert to {name} error (attempt {attempt + 1}): {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(1 * (attempt + 1))
        
        return False
    
    async def test_all_connections(self) -> dict[str, bool]:
        """Test all provider connections."""
        results = {}
        
        for name, provider in self.providers.items():
            try:
                results[name] = await provider.test_connection()
            except Exception as e:
                results[name] = False
                logger.error(f"Connection test for {name} failed: {e}")
        
        return results
    
    async def close_all(self) -> None:
        """Close all provider sessions."""
        for provider in self.providers.values():
            if hasattr(provider, "close"):
                await provider.close()


def create_telegram_alerter(config: dict) -> Optional[TelegramAlert]:
    """Factory function to create Telegram alerter from config."""
    bot_token = config.get("bot_token", "")
    chat_id = config.get("chat_id", "")
    
    if not bot_token or not chat_id:
        logger.warning("Telegram config incomplete")
        return None
    
    return TelegramAlert(bot_token, chat_id)


def create_discord_alerter(config: dict) -> Optional[DiscordAlert]:
    """Factory function to create Discord alerter from config."""
    webhook_url = config.get("webhook_url", "")
    
    if not webhook_url:
        logger.warning("Discord webhook URL not configured")
        return None
    
    return DiscordAlert(webhook_url)
