"""
RugShield Tests — Basic unit tests for scanner components.
"""

import pytest
from src.core.scanner import RiskLevel, TokenScanner, ScanResult
from src.models.token import Alert, AlertPriority, DeployerProfile


class TestTokenScanner:
    """Test scanner scoring logic."""
    
    @pytest.fixture
    def scanner(self):
        return TokenScanner(rpc_url="https://test.rpc", chain="base")
    
    def test_score_to_level_low(self):
        assert TokenScanner._score_to_level(10) == RiskLevel.LOW
        assert TokenScanner._score_to_level(20) == RiskLevel.LOW
    
    def test_score_to_level_medium(self):
        assert TokenScanner._score_to_level(21) == RiskLevel.MEDIUM
        assert TokenScanner._score_to_level(40) == RiskLevel.MEDIUM
    
    def test_score_to_level_high(self):
        assert TokenScanner._score_to_level(41) == RiskLevel.HIGH
        assert TokenScanner._score_to_level(60) == RiskLevel.HIGH
    
    def test_score_to_level_critical(self):
        assert TokenScanner._score_to_level(61) == RiskLevel.CRITICAL
        assert TokenScanner._score_to_level(80) == RiskLevel.CRITICAL
    
    def test_score_to_level_scam(self):
        assert TokenScanner._score_to_level(81) == RiskLevel.SCAM
        assert TokenScanner._score_to_level(100) == RiskLevel.SCAM


class TestDeployerProfile:
    """Test deployer risk scoring."""
    
    def test_new_wallet_is_risky(self):
        profile = DeployerProfile(
            address="0x1234",
            chain="base",
            wallet_age_days=0,
            rugs_detected=0,
        )
        assert profile.risk_score >= 30  # Fresh wallet = high risk
    
    def test_old_wallet_is_safer(self):
        profile = DeployerProfile(
            address="0x1234",
            chain="base",
            wallet_age_days=365,
            rugs_detected=0,
        )
        assert profile.risk_score == 0
    
    def test_rug_deployer_is_risky(self):
        profile = DeployerProfile(
            address="0x1234",
            chain="base",
            wallet_age_days=365,
            rugs_detected=2,
        )
        assert profile.risk_score >= 50


class TestAlertFormatting:
    """Test alert message formatting."""
    
    @pytest.fixture
    def sample_alert(self):
        return Alert(
            alert_id="test123",
            chain="base",
            token_address="0x1a2b3c4d5e6f7890",
            token_name="TestToken",
            token_symbol="TEST",
            risk_score=75,
            risk_level="critical",
            priority=AlertPriority.CRITICAL,
            red_flags=[
                "❌ Liquidity NOT locked",
                "⚠️ Deployer wallet is < 1 hour old",
                "❌ Contract NOT verified",
            ],
            deployer="0xabcdef1234567890",
            liquidity_usd=5000.0,
        )
    
    def test_telegram_format(self, alert=sample_alert):
        formatted = alert.format_telegram()
        assert "RUGSHIELD ALERT" in formatted
        assert "TEST" in formatted
        assert "75/100" in formatted
        assert "Liquidity NOT locked" in formatted
    
    def test_discord_format(self, alert=sample_alert):
        formatted = alert.format_discord()
        assert "RUGSHIELD ALERT" in formatted
        assert "CRITICAL" in formatted


# Run with: pytest tests/test_basic.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
