"""Configuration management for Whale Scoop Bot."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Main configuration class."""

    # Mode
    paper_trading_mode: bool = True
    log_level: str = "INFO"

    # Risk parameters
    max_risk_per_trade: float = 1.5  # percentage of NAV
    max_position_size: float = 10.0  # max % of NAV per position
    hedge_fund_reduction: float = 0.5  # reduction factor for long-short funds

    # Signal parameters
    min_signal_score: float = 75.0
    min_cluster_window_days: int = 7
    vwap_spread_threshold: float = 1.5  # percentage

    # Data sources
    sec_api_key: Optional[str] = None
    whale_alert_ws_url: str = "wss://api.whale-alert.io/v1/ws"
    api_base_url: str = "http://localhost:8000"  # WhaleTracker backend

    # Execution
    poll_interval: int = 60  # seconds
    order_timeout: int = 30  # seconds

    # I-Ratio (insider buy/sell ratio)
    seasonal_blackout_months: list = None

    # VWAP settings
    vwap_window_minutes: int = 5
    price_feeds: list = None

    def __post_init__(self):
        """Initialize default values."""
        if self.seasonal_blackout_months is None:
            self.seasonal_blackout_months = [3, 5, 8, 11]  # March, May, August, November
        if self.price_feeds is None:
            self.price_feeds = ["binance", "coinbase"]

        # Load from environment
        self.sec_api_key = os.getenv("SEC_API_KEY", self.sec_api_key)

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables."""
        config = cls()
        config.paper_trading_mode = os.getenv("PAPER_TRADING_MODE", "true").lower() == "true"
        config.log_level = os.getenv("LOG_LEVEL", "INFO")
        config.max_risk_per_trade = float(os.getenv("MAX_RISK_PER_TRADE", "1.5"))
        config.min_signal_score = float(os.getenv("MIN_SIGNAL_SCORE", "75.0"))
        return config