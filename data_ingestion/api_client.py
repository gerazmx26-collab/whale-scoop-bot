"""API Client for WhaleTracker Backend."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

import aiohttp

from utils.config import Config
from utils.logger import setup_logger


logger = setup_logger("api_client")


class WhaleTrackerAPI:
    """Client for WhaleTracker Backend API."""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.api_base_url or "http://localhost:8000"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def get_form4_transactions(self) -> list[dict]:
        """Fetch Form 4 transactions from the API."""
        session = await self._get_session()

        try:
            async with session.get(f"{self.base_url}/form4") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return self._normalize_form4(data)
                else:
                    logger.warning(f"[DATA] API returned status {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"[DATA] Error fetching Form 4: {e}")
            return []

    async def get_signals(self, min_strength: int = 2) -> list[dict]:
        """Fetch market signals from the API."""
        session = await self._get_session()

        try:
            async with session.get(
                f"{self.base_url}/signals",
                params={"min_strength": min_strength, "limit": 50}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data
                else:
                    return []
        except Exception as e:
            logger.error(f"[DATA] Error fetching signals: {e}")
            return []

    async def get_clusters(self, min_participants: int = 3) -> list[dict]:
        """Fetch cluster buys from the API."""
        session = await self._get_session()

        try:
            async with session.get(
                f"{self.base_url}/clusters",
                params={"min_participants": min_participants}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data
                else:
                    return []
        except Exception as e:
            logger.error(f"[DATA] Error fetching clusters: {e}")
            return []

    async def get_dashboard(self) -> dict:
        """Fetch dashboard data."""
        session = await self._get_session()

        try:
            async with session.get(f"{self.base_url}/dashboard") as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return {}
        except Exception as e:
            logger.error(f"[DATA] Error fetching dashboard: {e}")
            return {}

    async def get_health(self) -> dict:
        """Check API health."""
        session = await self._get_session()

        try:
            async with session.get(f"{self.base_url}/health") as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return {"status": "unhealthy"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _normalize_form4(self, filings: list) -> list[dict]:
        """Normalize Form 4 data from API to internal format."""
        normalized = []

        for f in filings:
            # Skip non-P (Open Market Purchase) transactions
            if f.get("transaction_code", "") != "P":
                continue

            normalized.append({
                "ticker": f.get("ticker", "").upper(),
                "form_type": "4",
                "filer_name": f.get("filer_name", ""),
                "filing_date": f.get("filing_date", ""),
                "transaction_code": f.get("transaction_code", ""),
                "shares": f.get("shares", 0),
                "price": f.get("price", 0),
                "officer_title": f.get("officer_title", ""),
                "is_ceo": "CEO" in f.get("officer_title", ""),
                "is_cfo": "CFO" in f.get("officer_title", ""),
            })

        return normalized

    async def close(self):
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()