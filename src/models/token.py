"""
RugShield Data Models — Token and alert data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AlertPriority(Enum):
    """Alert priority levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ChainType(Enum):
    """Supported blockchain types."""
    EVM = "evm"
    SOLANA = "solana"


@dataclass
class ChainConfig:
    """Chain configuration."""
    name: str
    chain_type: ChainType
    chain_id: int
    rpc_url: str
    explorer_url: str
    native_token: str = "ETH"
    factory_addresses: list[str] = field(default_factory=list)
    router_addresses: list[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class ContractMethod:
    """Contract method signature."""
    name: str
    signature: str
    risk_weight: int = 0
    description: str = ""


@dataclass
class TokenContract:
    """Token contract analysis."""
    address: str
    chain: str
    is_open_source: bool = False
    is_proxy: bool = False
    has_selfdestruct: bool = False
    has_mint: bool = False
    has_pause: bool = False
    has_blacklist: bool = False
    has_whitelist: bool = False
    max_tx_amount: Optional[float] = None
    max_sell_tax: float = 0.0
    max_buy_tax: float = 0.0
    owner_address: Optional[str] = None
    owner_can_change_tax: bool = False
    
    @property
    def suspicious_methods(self) -> list[str]:
        """List suspicious contract methods."""
        suspicious = []
        if self.has_blacklist:
            suspicious.append("blacklist")
        if self.has_whitelist:
            suspicious.append("whitelist")
        if self.has_pause:
            suspicious.append("pause")
        if self.has_mint:
            suspicious.append("mint")
        if self.has_selfdestruct:
            suspicious.append("selfdestruct")
        return suspicious


@dataclass
class DeployerProfile:
    """Deployer wallet profile."""
    address: str
    chain: str
    wallet_age_days: int = 0
    total_contracts_deployed: int = 0
    rugs_detected: int = 0
    is_contract: bool = False
    first_seen: Optional[datetime] = None
    
    @property
    def risk_score(self) -> int:
        """Calculate deployer risk score (0-100)."""
        score = 0
        if self.wallet_age_days < 1:
            score += 40
        elif self.wallet_age_days < 7:
            score += 20
        elif self.wallet_age_days < 30:
            score += 10
        
        if self.rugs_detected > 0:
            score += min(self.rugs_detected * 25, 50)
        
        if self.total_contracts_deployed > 20:
            score += 10
        
        return min(score, 100)


@dataclass
class PairInfo:
    """DEX pair information."""
    pair_address: str
    token0: str
    token1: str
    reserve0: float
    reserve1: float
    liquidity_usd: float
    pair_created_at: Optional[datetime] = None
    router_address: Optional[str] = None


@dataclass 
class LockInfo:
    """Liquidity lock information."""
    is_locked: bool
    lock_percentage: float
    locker_type: Optional[str] = None  # e.g., "Team.Finance", "Unicrypt"
    lock_contract: Optional[str] = None
    unlock_time: Optional[datetime] = None
    locked_amount_usd: float = 0.0
    
    @property
    def is_expired(self) -> bool:
        """Check if lock has expired."""
        if self.unlock_time is None:
            return False
        return datetime.utcnow() > self.unlock_time


@dataclass
class HolderStats:
    """Token holder statistics."""
    total_holders: int = 0
    top_10_percentage: float = 0.0
    top_25_percentage: float = 0.0
    top_50_percentage: float = 0.0
    deployer_percentage: float = 0.0
    pair_percentage: float = 0.0
    contract_percentage: float = 0.0
    is_reflected: bool = False  # Reflection tokens
    
    @property
    def concentration_risk(self) -> str:
        """Assess concentration risk level."""
        if self.top_10_percentage > 80:
            return "critical"
        elif self.top_10_percentage > 60:
            return "high"
        elif self.top_10_percentage > 40:
            return "medium"
        return "low"


@dataclass
class TaxAnalysis:
    """Buy/sell tax analysis."""
    buy_tax: float = 0.0
    sell_tax: float = 0.0
    transfer_tax: float = 0.0
    max_buy_tax: float = 0.0
    max_sell_tax: float = 0.0
    can_change_tax: bool = False
    
    @property
    def is_suspicious(self) -> bool:
        """Check if taxes are suspicious."""
        return (
            self.sell_tax > 20 or
            self.max_sell_tax > 50 or
            (self.buy_tax > 10 and self.sell_tax > 10)
        )


@dataclass
class Alert:
    """Rug-pull alert."""
    alert_id: str
    chain: str
    token_address: str
    token_name: str
    token_symbol: str
    risk_score: int
    risk_level: str
    priority: AlertPriority
    red_flags: list[str]
    deployer: str
    pair_address: Optional[str] = None
    liquidity_usd: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def format_telegram(self) -> str:
        """Format alert for Telegram."""
        priority_emoji = {
            AlertPriority.INFO: "ℹ️",
            AlertPriority.WARNING: "⚠️",
            AlertPriority.CRITICAL: "🚨",
            AlertPriority.EMERGENCY: "🔴",
        }
        
        flags_text = "\n".join(self.red_flags[:6])  # Max 6 flags
        
        return (
            f"{priority_emoji.get(self.priority, '📊')} **RUGSHIELD ALERT**\n\n"
            f"**Token:** `{self.token_address[:6]}...{self.token_address[-4:]}`\n"
            f"**Name:** {self.token_name} ({self.token_symbol})\n"
            f"**Chain:** {self.chain.upper()}\n"
            f"**Risk Score:** {self.risk_score}/100 ({self.risk_level.upper()})\n"
            f"**Liquidity:** ${self.liquidity_usd:,.2f}\n"
            f"**Deployer:** `{self.deployer[:6]}...{self.deployer[-4:]}`\n\n"
            f"**Red Flags:**\n{flags_text}\n\n"
            f"🕐 {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
    
    def format_discord(self) -> str:
        """Format alert for Discord (with embed-friendly markdown)."""
        flags_text = "\n".join(self.red_flags[:8])
        
        return (
            f"## 🚨 RUGSHIELD ALERT — {self.risk_level.upper()}\n\n"
            f"**Token:** `{self.token_address}`\n"
            f"**Name:** {self.token_name} ({self.token_symbol})\n"
            f"**Chain:** {self.chain.upper()}\n"
            f"**Risk Score:** `{self.risk_score}/100`\n"
            f"**Liquidity:** `${self.liquidity_usd:,.2f}`\n\n"
            f"### Red Flags:\n{flags_text}"
        )
