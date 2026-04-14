"""Order execution manager for Whale Scoop Bot."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from risk_manager.risk_manager import RiskManager
from utils.config import Config
from utils.logger import setup_logger


logger = setup_logger("order_manager")


class OrderManager:
    """Manages order execution and logging."""

    def __init__(self, config: Config, risk_manager: RiskManager):
        self.config = config
        self.risk_manager = risk_manager
        self.order_log: list[dict] = []
        self.pending_orders: dict[str, dict] = {}

    async def execute(self, signal: dict, position_size: float) -> dict[str, Any]:
        """Execute order based on signal."""
        ticker = signal.get("ticker", "")

        if not ticker:
            return {"success": False, "reason": "Missing ticker"}

        if self.config.paper_trading_mode:
            return await self._execute_paper(signal, position_size)
        else:
            return await self._execute_live(signal, position_size)

    async def _execute_paper(self, signal: dict, position_size: float) -> dict:
        """Execute in paper trading mode."""
        ticker = signal.get("ticker", "")
        order_id = self._generate_order_id(ticker)

        # Simulate execution
        entry_price = await self._get_market_price(ticker)

        # Log the order
        order_record = {
            "order_id": order_id,
            "ticker": ticker,
            "side": "BUY",
            "size": position_size,
            "entry_price": entry_price,
            "timestamp": datetime.now().isoformat(),
            "mode": "PAPER",
            "signal_score": signal.get("score", 0),
        }

        self.order_log.append(order_record)

        # Record position in risk manager
        self.risk_manager.open_position(ticker, position_size, entry_price, order_id)

        logger.info(
            f"[EXECUTION] PAPER BUY: {ticker} {position_size}% @ ${entry_price} "
            f"(Order ID: {order_id})"
        )

        return {
            "success": True,
            "order_id": order_id,
            "details": f"Bought {position_size}% of {ticker} at ${entry_price}",
        }

    async def _execute_live(self, signal: dict, position_size: float) -> dict:
        """Execute in live trading mode."""
        # In production, integrate with broker API
        logger.warning(
            f"[EXECUTION] LIVE TRADING not fully implemented - "
            f"would execute: {signal.get('ticker')}"
        )
        return {"success": False, "reason": "Live trading not configured"}

    async def _get_market_price(self, ticker: str) -> float:
        """Get current market price (placeholder).

        In production, this would fetch from price feed.
        """
        # Placeholder
        return 100.0

    def _generate_order_id(self, ticker: str) -> str:
        """Generate unique order ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"WS-{ticker}-{timestamp}"

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel pending order."""
        if order_id in self.pending_orders:
            order = self.pending_orders.pop(order_id)
            order["status"] = "CANCELLED"
            self.order_log.append(order)

            logger.info(f"[EXECUTION] Order cancelled: {order_id}")
            return {"success": True, "order_id": order_id}

        return {"success": False, "reason": "Order not found"}

    def get_order(self, order_id: str) -> Optional[dict]:
        """Get order by ID."""
        for order in self.order_log:
            if order.get("order_id") == order_id:
                return order

        return self.pending_orders.get(order_id)

    def get_open_orders(self) -> list[dict]:
        """Get all open orders."""
        return [
            o for o in self.order_log
            if o.get("status") == "OPEN"
        ]

    def get_order_history(self, days: int = 30) -> list[dict]:
        """Get order history."""
        cutoff = datetime.now() - timedelta(days=days)

        return [
            o for o in self.order_log
            if datetime.fromisoformat(o["timestamp"]) >= cutoff
        ]

    def log_vwap_spread(self, ticker: str, current_price: float, vwap: float):
        """Log VWAP spread for analysis."""
        if vwap > 0:
            spread = (current_price - vwap) / vwap * 100

            logger.info(
                f"[DATA] {ticker}: Current=${current_price}, "
                f"VWAP=${vwap}, Spread={spread:.2f}%"
            )

            return {
                "ticker": ticker,
                "current_price": current_price,
                "vwap": vwap,
                "spread_pct": spread,
            }

        return None


# Import timedelta for get_order_history
from datetime import timedelta