"""
RugShield Scanner — On-chain token analysis engine.
Analyzes new token contracts for rug-pull indicators.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk classification levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    SCAM = "scam"


@dataclass
class TokenInfo:
    """Token contract information."""
    address: str
    name: str
    symbol: str
    decimals: int
    total_supply: float
    deployer: str
    deploy_time: datetime
    chain: str
    is_verified: bool = False
    has_mint_function: bool = False
    has_pause_function: bool = False


@dataclass
class LiquidityInfo:
    """Liquidity pool information."""
    pair_address: str
    liquidity_usd: float
    is_locked: bool
    locker_contract: Optional[str] = None
    lock_expiry: Optional[datetime] = None
    lock_percentage: float = 0.0


@dataclass
class HolderInfo:
    """Token holder distribution analysis."""
    total_holders: int
    top_10_concentration: float  # % held by top 10 wallets
    deployer_holdings: float  # % held by deployer
    is_suspicious: bool = False
    max_holder_percentage: float = 0.0


@dataclass
class HoneypotResult:
    """Honeypot detection result."""
    is_honeypot: bool
    can_buy: bool
    can_sell: bool
    buy_tax: float  # percentage
    sell_tax: float  # percentage
    gas_estimation: Optional[int] = None
    simulation_tx: Optional[str] = None


@dataclass
class ScanResult:
    """Complete token scan result."""
    token: TokenInfo
    liquidity: Optional[LiquidityInfo]
    holders: Optional[HolderInfo]
    honeypot: Optional[HoneypotResult]
    risk_score: int = 0
    risk_level: RiskLevel = RiskLevel.LOW
    red_flags: list[str] = field(default_factory=list)
    scan_time: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_safe(self) -> bool:
        return self.risk_score < 30
    
    @property
    def is_dangerous(self) -> bool:
        return self.risk_score >= 60


# Known locker contracts across chains
LOCKER_CONTRACTS: dict[str, list[str]] = {
    "base": [
        "0x...",  # Team.Finance
        "0x...",  # Unicrypt
    ],
    "arbitrum": [
        "0x...",
        "0x...",
    ],
    "linea": [
        "0x...",
    ],
}

# Minimum deployer wallet age (in seconds) before considered safe
MIN_DEPLOYER_AGE = 86400  # 24 hours

# Honeypot simulation parameters
HONEYPOT_SIM_AMOUNT_ETH = 0.01
HONEYPOT_MAX_GAS = 3_000_000


class TokenScanner:
    """Main token scanner for on-chain analysis."""
    
    def __init__(self, rpc_url: str, chain: str = "base"):
        self.rpc_url = rpc_url
        self.chain = chain
        self.w3: Optional[AsyncWeb3] = None
        
    async def connect(self) -> None:
        """Establish connection to RPC endpoint."""
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(self.rpc_url))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        logger.info(f"Connected to {self.chain} via {self.rpc_url}")
        
    async def scan_token(self, token_address: str) -> ScanResult:
        """
        Perform comprehensive token scan.
        
        Args:
            token_address: Contract address to analyze
            
        Returns:
            ScanResult with risk assessment
        """
        if not self.w3:
            await self.connect()
            
        logger.info(f"Scanning token: {token_address} on {self.chain}")
        
        # Gather all analysis data concurrently
        token_info, liquidity, holders, honeypot = await asyncio.gather(
            self._get_token_info(token_address),
            self._analyze_liquidity(token_address),
            self._analyze_holders(token_address),
            self._detect_honeypot(token_address),
        )
        
        # Build scan result
        result = ScanResult(
            token=token_info,
            liquidity=liquidity,
            holders=holders,
            honeypot=honeypot,
        )
        
        # Calculate risk score
        result.risk_score, result.red_flags = self._calculate_risk(result)
        result.risk_level = self._score_to_level(result.risk_score)
        
        return result
    
    async def _get_token_info(self, address: str) -> TokenInfo:
        """Fetch basic token information."""
        # ERC20 minimal ABI
        abi = [
            {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
        ]
        
        contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(address),
            abi=abi
        )
        
        # Fetch token details
        name = await contract.functions.name().call()
        symbol = await contract.functions.symbol().call()
        decimals = await contract.functions.decimals().call()
        total_supply = await contract.functions.totalSupply().call()
        
        # Get deployer from contract creation
        deployer = await self._get_contract_deployer(address)
        deploy_time = await self._get_deploy_time(address)
        
        # Check contract verification (simplified)
        is_verified = await self._check_verification(address)
        
        return TokenInfo(
            address=address,
            name=name,
            symbol=symbol,
            decimals=decimals,
            total_supply=total_supply / (10 ** decimals),
            deployer=deployer,
            deploy_time=deploy_time,
            chain=self.chain,
            is_verified=is_verified,
        )
    
    async def _get_contract_deployer(self, address: str) -> str:
        """Get the deployer address of a contract."""
        try:
            # Get first transaction (deployment)
            tx_hash = await self.w3.eth.get_code(
                self.w3.to_checksum_address(address)
            )
            # In real implementation, trace or use explorer API
            return "0x0000000000000000000000000000000000000000"
        except Exception as e:
            logger.warning(f"Failed to get deployer: {e}")
            return "0x0000000000000000000000000000000000000000"
    
    async def _get_deploy_time(self, address: str) -> datetime:
        """Get contract deployment timestamp."""
        # In real implementation, fetch from explorer API or trace
        return datetime.utcnow()
    
    async def _check_verification(self, address: str) -> bool:
        """Check if contract source is verified on block explorer."""
        # Would query blockscout/API in production
        return False
    
    async def _analyze_liquidity(self, token_address: str) -> LiquidityInfo:
        """Analyze liquidity pool status."""
        # Check LP lock status via known locker contracts
        lockers = LOCKER_CONTRACTS.get(self.chain, [])
        
        return LiquidityInfo(
            pair_address="0x0000000000000000000000000000000000000000",
            liquidity_usd=0.0,
            is_locked=False,
            lock_percentage=0.0,
        )
    
    async def _analyze_holders(self, token_address: str) -> HolderInfo:
        """Analyze token holder distribution."""
        # Would query token holders via explorer API
        return HolderInfo(
            total_holders=0,
            top_10_concentration=0.0,
            deployer_holdings=0.0,
        )
    
    async def _detect_honeypot(self, token_address: str) -> HoneypotResult:
        """
        Detect if token is a honeypot by simulating buy/sell.
        
        A honeypot allows buying but prevents or heavily taxes selling.
        """
        # Would perform actual buy/sell simulation in production
        return HoneypotResult(
            is_honeypot=False,
            can_buy=True,
            can_sell=True,
            buy_tax=0.0,
            sell_tax=0.0,
        )
    
    def _calculate_risk(self, result: ScanResult) -> tuple[int, list[str]]:
        """
        Calculate overall risk score based on all factors.
        
        Returns:
            Tuple of (score, list_of_red_flags)
        """
        score = 0
        flags = []
        
        # 1. Liquidity lock check (25 points max)
        if result.liquidity:
            if not result.liquidity.is_locked:
                score += 25
                flags.append("❌ Liquidity NOT locked")
            elif result.liquidity.lock_percentage < 100:
                score += 10
                flags.append(f"⚠️ Only {result.liquidity.lock_percentage}% of LP locked")
        
        # 2. Deployer wallet age (15 points max)
        deployer_age = (datetime.utcnow() - result.token.deploy_time).total_seconds()
        if deployer_age < 3600:  # Less than 1 hour
            score += 15
            flags.append("⚠️ Deployer wallet is < 1 hour old")
        elif deployer_age < MIN_DEPLOYER_AGE:
            score += 8
            flags.append("⚠️ Deployer wallet is < 24 hours old")
        
        # 3. Honeypot detection (25 points max)
        if result.honeypot:
            if result.honeypot.is_honeypot:
                score += 25
                flags.append("❌ Honeypot detected — cannot sell")
            elif result.honeypot.sell_tax > 20:
                score += 15
                flags.append(f"⚠️ High sell tax: {result.honeypot.sell_tax}%")
            elif result.honeypot.sell_tax > 10:
                score += 8
                flags.append(f"⚠️ Moderate sell tax: {result.honeypot.sell_tax}%")
        
        # 4. Holder distribution (15 points max)
        if result.holders:
            if result.holders.top_10_concentration > 80:
                score += 15
                flags.append(f"⚠️ Top 10 holders own {result.holders.top_10_concentration}%")
            elif result.holders.deployer_holdings > 50:
                score += 10
                flags.append(f"⚠️ Deployer holds {result.holders.deployer_holdings}%")
        
        # 5. Contract verification (10 points max)
        if not result.token.is_verified:
            score += 10
            flags.append("❌ Contract NOT verified")
        
        # 6. Suspicious functions (5 points max)
        if result.token.has_mint_function:
            score += 3
            flags.append("⚠️ Contract has mint function")
        if result.token.has_pause_function:
            score += 2
            flags.append("⚠️ Contract has pause function")
        
        return min(score, 100), flags
    
    @staticmethod
    def _score_to_level(score: int) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score <= 20:
            return RiskLevel.LOW
        elif score <= 40:
            return RiskLevel.MEDIUM
        elif score <= 60:
            return RiskLevel.HIGH
        elif score <= 80:
            return RiskLevel.CRITICAL
        else:
            return RiskLevel.SCAM


class MultiChainScanner:
    """Scanner that monitors multiple chains simultaneously."""
    
    def __init__(self, chains_config: dict[str, dict[str, Any]]):
        self.scanners: dict[str, TokenScanner] = {}
        self.config = chains_config
        
    async def initialize(self) -> None:
        """Initialize scanners for all enabled chains."""
        for chain_name, config in self.config.items():
            if config.get("enabled", False):
                scanner = TokenScanner(
                    rpc_url=config["rpc"],
                    chain=chain_name,
                )
                await scanner.connect()
                self.scanners[chain_name] = scanner
                logger.info(f"Initialized scanner for {chain_name}")
    
    async def scan_all_chains(self, token_address: str) -> dict[str, ScanResult]:
        """Scan a token address across all enabled chains."""
        tasks = []
        chain_names = []
        
        for chain_name, scanner in self.scanners.items():
            tasks.append(scanner.scan_token(token_address))
            chain_names.append(chain_name)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            chain: result for chain, result in zip(chain_names, results)
            if not isinstance(result, Exception)
        }
