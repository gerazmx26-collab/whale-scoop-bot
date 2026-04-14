"""Whale Alert stream client for on-chain data."""

import asyncio
import json
import logging
from typing import Any, Optional

import websockets

from utils.config import Config
from utils.logger import setup_logger


logger = setup_logger("whale_alerts")


class WhaleAlertStream:
    """WebSocket client for Whale Alert API."""

    def __init__(self, config: Config):
        self.config = config
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.pending_alerts: list[dict] = []
        self._running = False

    async def connect(self):
        """Establish WebSocket connection."""
        try:
            self.ws = await websockets.connect(
                self.config.whale_alert_ws_url,
                ping_interval=30,
                ping_timeout=10
            )
            self._running = True
            logger.info("[DATA] Whale Alert WebSocket connected")
        except Exception as e:
            logger.error(f"[DATA] Failed to connect to Whale Alert: {e}")
            self._running = False

    async def listen(self):
        """Listen for incoming alerts."""
        if not self.ws:
            await self.connect()

        try:
            async for message in self.ws:
                if not self._running:
                    break

                alert = json.loads(message)
                processed = self._process_alert(alert)

                if processed:
                    self.pending_alerts.append(processed)
                    logger.info(f"[DATA] Whale Alert: {processed.get('type')} - ${processed.get('amount')}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("[DATA] Whale Alert connection closed, reconnecting...")
            await asyncio.sleep(5)
            await self.connect()
            if self._running:
                await self.listen()
        except Exception as e:
            logger.error(f"[DATA] Error in Whale Alert stream: {e}")

    def _process_alert(self, raw: dict) -> Optional[dict]:
        """Process raw whale alert."""
        alert_type = raw.get("type", "")

        # Only track exchanges and large transfers
        if alert_type not in ["transfer", "exchange"]:
            return None

        amount = raw.get("amount", 0)
        if amount < 1000000:  # Skip under $1M
            return None

        return {
            "id": raw.get("id", ""),
            "type": alert_type,
            "blockchain": raw.get("blockchain", ""),
            "from": raw.get("from", ""),
            "to": raw.get("to", ""),
            "amount": amount,
            "symbol": raw.get("symbol", ""),
            "timestamp": raw.get("timestamp", ""),
            "is_exchange_to_cold": self._is_exchange_to_cold_wallet(raw),
            "is_cold_to_exchange": self._is_cold_wallet_to_exchange(raw),
        }

    def _is_exchange_to_cold_wallet(self, alert: dict) -> bool:
        """Detect if transfer is from exchange to cold wallet (accumulation signal)."""
        alert_type = alert.get("type", "")
        to = alert.get("to", "").lower()

        # Known cold wallet prefixes
        cold_prefixes = ["0x", "0x", "bc1"]

        return alert_type == "transfer" and any(to.startswith(p) for p in cold_prefixes)

    def _is_cold_wallet_to_exchange(self, alert: dict) -> bool:
        """Detect if transfer is from cold wallet to exchange (distribution signal)."""
        alert_type = alert.get("type", "")
        from_addr = alert.get("from", "").lower()

        cold_prefixes = ["0x", "0x", "bc1"]

        return alert_type == "transfer" and any(from_addr.startswith(p) for p in cold_prefixes)

    async def get_pending_alerts(self) -> list[dict]:
        """Get and clear pending alerts."""
        alerts = self.pending_alerts.copy()
        self.pending_alerts.clear()
        return alerts

    async def close(self):
        """Close WebSocket connection."""
        self._running = False
        if self.ws:
            await self.ws.close()
        logger.info("[DATA] Whale Alert WebSocket closed")