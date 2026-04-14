"""Risk management module for Whale Scoop Bot."""

import logging
from datetime import datetime
from typing import Any, Optional

from utils.config import Config
from utils.logger import setup_logger


logger = setup_logger("risk_manager")


class RiskManager:
    """Risk management and position sizing."""

    def __init__(self, config: Config):
        self.config = config
        self.current_exposure = 0.0
        self.total_nav = 1000000.0  #假设$1M NAV
        self.open_positions: dict[str, dict] = {}

    def check_risk(self, filing: dict, signal_score: float) -> dict[str, Any]:
        """Check if signal passes risk criteria."""
        ticker = filing.get("ticker", "")

        # 1. Max position size check
        if self.current_exposure >= self.config.max_position_size:
            return {
                "approved": False,
                "reason": f"Max position size reached ({self.config.max_position_size}%)",
            }

        # 2. Calculate position size
        position_size = self._calculate_position_size(filing, signal_score)

        # 3. Hedge fund awareness
        if self._is_hedge_fund(filing):
            position_size *= self.config.hedge_fund_reduction
            logger.info(f"[RISK] Hedge fund detected, position reduced by 50%")

        # 4. Check for existing position
        if ticker in self.open_positions:
            current = self.open_positions[ticker]["size"]
            new_size = current + position_size

            if new_size > self.config.max_position_size:
                position_size = self.config.max_position_size - current
                logger.info(f"[RISK] Increasing existing position: {ticker}")

        # 5. Per-trade risk limit
        if position_size > self.config.max_risk_per_trade:
            position_size = self.config.max_risk_per_trade

        return {
            "approved": position_size > 0,
            "position_size": position_size,
            "reason": "Approved" if position_size > 0 else "Position size too small",
        }

    def _calculate_position_size(self, filing: dict, signal_score: float) -> float:
        """Calculate position size based on signal score and risk."""
        base_size = signal_score / 100.0 * self.config.max_risk_per_trade

        # Adjust for confidence
        confidence_factor = min(signal_score / self.config.min_signal_score, 1.5)

        # Adjust for hedge fund if applicable
        if self._is_hedge_fund(filing):
            confidence_factor *= self.config.hedge_fund_reduction

        return min(base_size * confidence_factor, self.config.max_risk_per_trade)

    def _is_hedge_fund(self, filing: dict) -> bool:
        """Check if filing is from a long-short hedge fund."""
        filer_name = filing.get("filer_name", "").lower()

        # Known hedge fund patterns
        hedge_patterns = [
            "hedge fund",
            "long short",
            "ls基金管理",
            "capital",
            " ventures",
        ]

        return any(p in filer_name for p in hedge_patterns)

    def open_position(
        self,
        ticker: str,
        size: float,
        entry_price: float,
        order_id: str
    ):
        """Record opened position."""
        self.open_positions[ticker] = {
            "size": size,
            "entry_price": entry_price,
            "order_id": order_id,
            "open_time": datetime.now(),
        }

        self.current_exposure += size
        logger.info(f"[RISK] Position opened: {ticker} {size}% @ ${entry_price}")

    def close_position(self, ticker: str, exit_price: float, pnl: float):
        """Record closed position."""
        if ticker in self.open_positions:
            pos = self.open_positions.pop(ticker)
            self.current_exposure -= pos["size"]

            logger.info(
                f"[RISK] Position closed: {ticker} @ ${exit_price}, "
                f"PnL: ${pnl:.2f}"
            )

    def get_exposure(self) -> float:
        """Get current total exposure."""
        return self.current_exposure

    def get_position(self, ticker: str) -> Optional[dict]:
        """Get position for ticker."""
        return self.open_positions.get(ticker)

    def check_liquidity_trap(self, whale_alert: dict, order_flow: dict) -> bool:
        """Check for liquidity trap manipulation.

        Args:
            whale_alert: Whale alert data
            order_flow: Order flow data

        Returns:
            True if detected as liquidity trap
        """
        alert_type = whale_alert.get("type", "")
        is_cold_to_exchange = whale_alert.get("is_cold_to_exchange", False)

        # If whale moving to exchange but no sell pressure, could be trap
        if alert_type == "transfer" and is_cold_to_exchange:
            sell_volume = order_flow.get("sell_volume", 0)
            buy_volume = order_flow.get("buy_volume", 0)

            # No confirmation of selling pressure
            if sell_volume < buy_volume:
                logger.warning(
                    f"[RISK] Liquidity trap detected: Whale transfer to exchange "
                    f"without sell confirmation"
                )
                return True

        return False

    def calculate_vwap_spread_risk(self, current_price: float, vwap: float) -> float:
        """Calculate risk adjustment based on VWAP spread."""
        if vwap == 0:
            return 1.0

        spread_pct = abs(current_price - vwap) / vwap * 100

        # Higher spread = higher risk
        if spread_pct > self.config.vwap_spread_threshold:
            return 0.5  # Reduce position

        if spread_pct > self.config.vwap_spread_threshold / 2:
            return 0.75

        return 1.0