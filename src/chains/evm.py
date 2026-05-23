"""
EVM Chain Handler — Multi-chain EVM support for Base, Linea, Arbitrum.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware

logger = logging.getLogger(__name__)


# EVM Chain configurations
EVM_CHAINS: dict[str, dict[str, Any]] = {
    "base": {
        "chain_id": 8453,
        "rpc": "https://mainnet.base.org",
        "explorer": "https://basescan.org",
        "native_token": "ETH",
        "factory_addresses": [
            "0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6",  # Uniswap V2
            "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73",  # PancakeSwap V3
        ],
        "router_addresses": [
            "0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24",  # Uniswap V2 Router
        ],
    },
    "arbitrum": {
        "chain_id": 42161,
        "rpc": "https://arb1.arbitrum.io/rpc",
        "explorer": "https://arbiscan.io",
        "native_token": "ETH",
        "factory_addresses": [
            "0xf1D7CC64Fb4452F05c498126312eBE29f30Fbcf9",  # Uniswap V3
            "0x02a4dE4dA946B0814330766D4E5D49711638e075",  # SushiSwap
        ],
        "router_addresses": [
            "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",  # SushiSwap Router
        ],
    },
    "linea": {
        "chain_id": 59144,
        "rpc": "https://rpc.linea.build",
        "explorer": "https://lineascan.build",
        "native_token": "ETH",
        "factory_addresses": [
            "0x...LineaFactory",  # Placeholder - add actual factory
        ],
        "router_addresses": [
            "0x...LineaRouter",  # Placeholder - add actual router
        ],
    },
}


@dataclass
class EVMEvent:
    """EVM event data."""
    event_name: str
    address: str
    block_number: int
    transaction_hash: str
    args: dict[str, Any]
    timestamp: Optional[int] = None


class EVMChainHandler:
    """
    Handler for EVM-compatible chains.
    Provides unified interface for chain interactions.
    """
    
    def __init__(self, chain_name: str, rpc_url: Optional[str] = None):
        self.chain_name = chain_name
        self.config = EVM_CHAINS.get(chain_name, {})
        self.rpc_url = rpc_url or self.config.get("rpc", "")
        self.w3: Optional[AsyncWeb3] = None
        self._event_callbacks: dict[str, list[Callable]] = {}
        
    async def connect(self) -> bool:
        """Connect to the EVM chain RPC."""
        try:
            self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(self.rpc_url))
            
            # Inject POA middleware for chains like Base
            if self.chain_name in ("base", "arbitrum"):
                self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            
            # Test connection
            chain_id = await self.w3.eth.chain_id()
            logger.info(f"Connected to {self.chain_name} (chain_id: {chain_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.chain_name}: {e}")
            return False
    
    async def get_latest_block(self) -> int:
        """Get latest block number."""
        if not self.w3:
            raise ConnectionError("Not connected to chain")
        return await self.w3.eth.block_number
    
    async def get_token_info(self, token_address: str) -> dict[str, Any]:
        """Fetch basic ERC20 token information."""
        if not self.w3:
            raise ConnectionError("Not connected to chain")
            
        abi = [
            {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}]},
            {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}]},
            {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}]},
            {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}]},
            {"constant": True, "inputs": [], "name": "owner", "outputs": [{"name": "", "type": "address"}]},
        ]
        
        checksum_addr = self.w3.to_checksum_address(token_address)
        contract = self.w3.eth.contract(address=checksum_addr, abi=abi)
        
        info = {
            "address": token_address,
            "chain": self.chain_name,
        }
        
        try:
            info["name"] = await contract.functions.name().call()
        except:
            info["name"] = "Unknown"
            
        try:
            info["symbol"] = await contract.functions.symbol().call()
        except:
            info["symbol"] = "???"
            
        try:
            info["decimals"] = await contract.functions.decimals().call()
        except:
            info["decimals"] = 18
            
        try:
            info["total_supply"] = await contract.functions.totalSupply().call()
        except:
            info["total_supply"] = 0
            
        try:
            info["owner"] = await contract.functions.owner().call()
        except:
            info["owner"] = None
            
        return info
    
    async def get_contract_creation_tx(self, address: str) -> Optional[dict]:
        """Get contract creation transaction (deployer, timestamp)."""
        # In production, use trace API or Etherscan API
        # This is a simplified placeholder
        return {
            "deployer": "0x0000000000000000000000000000000000000000",
            "timestamp": 0,
        }
    
    async def check_erc20_balance(self, token_address: str, wallet_address: str) -> int:
        """Check ERC20 token balance."""
        if not self.w3:
            raise ConnectionError("Not connected to chain")
            
        abi = [{"constant": True, "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}]}]
        
        contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(token_address),
            abi=abi
        )
        
        return await contract.functions.balanceOf(
            self.w3.to_checksum_address(wallet_address)
        ).call()
    
    async def estimate_gas(self, tx: dict) -> Optional[int]:
        """Estimate gas for a transaction."""
        if not self.w3:
            return None
        try:
            return await self.w3.eth.estimate_gas(tx)
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}")
            return None
    
    def get_explorer_url(self, address: str, tx_hash: Optional[str] = None) -> str:
        """Get block explorer URL for address or transaction."""
        base = self.config.get("explorer", "")
        if tx_hash:
            return f"{base}/tx/{tx_hash}"
        return f"{base}/address/{address}"
    
    def is_factory_address(self, address: str) -> bool:
        """Check if address is a known factory contract."""
        factories = self.config.get("factory_addresses", [])
        return address.lower() in [f.lower() for f in factories]
    
    def is_router_address(self, address: str) -> bool:
        """Check if address is a known router contract."""
        routers = self.config.get("router_addresses", [])
        return address.lower() in [r.lower() for r in routers]
    
    async def watch_new_pairs(
        self,
        factory_address: str,
        callback: Callable[[EVMEvent], Any],
        from_block: Optional[int] = None,
    ) -> None:
        """
        Watch for new pair creation events.
        
        Args:
            factory_address: The DEX factory contract
            callback: Function to call when new pair detected
            from_block: Starting block number (default: latest)
        """
        if not self.w3:
            raise ConnectionError("Not connected to chain")
        
        factory_abi = [
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "token0", "type": "address"},
                    {"indexed": True, "name": "token1", "type": "address"},
                    {"indexed": False, "name": "pair", "type": "address"},
                    {"indexed": False, "name": "", "type": "uint256"},
                ],
                "name": "PairCreated",
                "type": "event",
            }
        ]
        
        factory = self.w3.eth.contract(
            address=self.w3.to_checksum_address(factory_address),
            abi=factory_abi,
        )
        
        if from_block is None:
            from_block = await self.get_latest_block()
        
        logger.info(f"Watching factory {factory_address} from block {from_block}")
        
        # Poll for new events
        while True:
            try:
                latest = await self.get_latest_block()
                events = await factory.events.PairCreated.get_logs(
                    fromBlock=from_block,
                    toBlock=latest,
                )
                
                for event in events:
                    ev = EVMEvent(
                        event_name="PairCreated",
                        address=event.address,
                        block_number=event.blockNumber,
                        transaction_hash=event.transactionHash.hex(),
                        args=dict(event.args),
                    )
                    await callback(ev)
                
                from_block = latest + 1
                await asyncio.sleep(2)  # Poll interval
                
            except Exception as e:
                logger.error(f"Error watching pairs: {e}")
                await asyncio.sleep(5)


def get_supported_chains() -> list[str]:
    """Get list of supported EVM chains."""
    return list(EVM_CHAINS.keys())


def get_chain_config(chain_name: str) -> Optional[dict]:
    """Get configuration for a specific chain."""
    return EVM_CHAINS.get(chain_name)
