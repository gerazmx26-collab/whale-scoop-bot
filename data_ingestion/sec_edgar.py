"""SEC Edgar data client for Form 4 and 13F filings."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import aiohttp

from utils.config import Config
from utils.logger import setup_logger


logger = setup_logger("sec_edgar")


class SECEdgarClient:
    """Client for SEC Edgar API."""

    BASE_URL = "https://efts.sec.gov"

    def __init__(self, config: Config):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_check = datetime.now() - timedelta(hours=24)
        self.demo_mode = not config.sec_api_key  # Auto-enable demo if no API key

        # Demo filings for testing without API key
        self._demo_filings = [
            {
                "ticker": "NVDA",
                "form_type": "4",
                "filer_name": "Jensen Huang",
                "filing_date": datetime.now().strftime("%Y-%m-%d"),
                "transaction_code": "P",
                "shares": 50000,
                "price": 875.50,
                "officer_title": "CEO",
                "is_ceo": True,
                "is_cfo": False,
            },
            {
                "ticker": "AAPL",
                "form_type": "4",
                "filer_name": "Tim Cook",
                "filing_date": datetime.now().strftime("%Y-%m-%d"),
                "transaction_code": "P",
                "shares": 25000,
                "price": 178.25,
                "officer_title": "CEO",
                "is_ceo": True,
                "is_cfo": False,
            },
            {
                "ticker": "MSFT",
                "form_type": "4",
                "filer_name": "Amy Hood",
                "filing_date": datetime.now().strftime("%Y-%m-%d"),
                "transaction_code": "P",
                "shares": 10000,
                "price": 412.80,
                "officer_title": "CFO",
                "is_ceo": False,
                "is_cfo": True,
            },
        ]

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def fetch_recent_filings(
        self,
        forms: list = None,
        hours_lookback: int = 24
    ) -> list[dict[str, Any]]:
        """Fetch recent SEC filings."""
        # Return demo filings if no API key
        if self.demo_mode:
            logger.info("[DATA] Running in DEMO mode (no SEC API key)")
            return self._demo_filings.copy()

        if forms is None:
            forms = ["4", "13F", "13D", "13G"]

        cutoff = datetime.now() - timedelta(hours=hours_lookback)
        filings = []

        for form in forms:
            try:
                result = await self._fetch_form_filings(form, cutoff)
                filings.extend(result)
            except Exception as e:
                logger.warning(f"[DATA] Error fetching form {form}: {e}")

        return filings

    async def _fetch_form_filings(self, form: str, cutoff: datetime) -> list[dict]:
        """Fetch filings for a specific form type."""
        session = await self._get_session()

        # SEC EDGAR API endpoint
        url = f"{self.BASE_URL}/EFTS/Search/{form}"

        params = {
            "dateRange": "custom",
            "startdt": cutoff.strftime("%Y-%m-%d"),
            "enddt": datetime.now().strftime("%Y-%m-%d"),
            "forms": form,
        }

        if self.config.sec_api_key:
            headers = {"Authorization": f"Bearer {self.config.sec_api_key}"}
        else:
            headers = {}

        try:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return self._process_filings(form, data)
                else:
                    logger.warning(f"[DATA] SEC API returned {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"[DATA] Error fetching SEC filings: {e}")
            return []

    def _process_filings(self, form: str, data: dict) -> list[dict]:
        """Process and filter filings based on high conviction criteria."""
        processed = []
        raw_filings = data.get("filings", [])

        for filing in raw_filings:
            if form == "4":
                # Filter for Code P (Open Market Purchase) only
                if self._is_valid_form4(filing):
                    processed.append(self._normalize_form4(filing))
            elif form in ["13F", "13D", "13G"]:
                processed.append(self._normalize_13f(filing))

        return processed

    def _is_valid_form4(self, filing: dict) -> bool:
        """Check if Form 4 is a high-conviction purchase (Code P)."""
        transactions = filing.get("transactionForms", [])

        for tx in transactions:
            code = tx.get("transactionCode", "")
            # Only accept Code P (Open Market Purchase), ignore M ( Options)
            if code == "P":
                return True

        return False

    def _normalize_form4(self, filing: dict) -> dict:
        """Normalize Form 4 to internal format."""
        transactions = filing.get("transactionForms", [])

        # Get primary transaction (Code P)
        primary_tx = None
        for tx in transactions:
            if tx.get("transactionCode") == "P":
                primary_tx = tx
                break

        return {
            "ticker": filing.get("ticker", "").upper(),
            "form_type": "4",
            "filer_name": filing.get("filerName", ""),
            "filing_date": filing.get("filingDate", ""),
            "transaction_code": primary_tx.get("transactionCode") if primary_tx else None,
            "shares": primary_tx.get("sharesOwnedFollowingTransaction", 0) if primary_tx else 0,
            "price": primary_tx.get("pricePerShare", 0) if primary_tx else 0,
            "officer_title": filing.get("officerTitle", ""),
            "is_ceo": "CEO" in filing.get("officerTitle", ""),
            "is_cfo": "CFO" in filing.get("officerTitle", ""),
        }

    def _normalize_13f(self, filing: dict) -> dict:
        """Normalize 13F filing to internal format."""
        holdings = filing.get("holdings", [])

        return {
            "ticker": filing.get("ticker", "").upper(),
            "form_type": filing.get("formType", "13F"),
            "filer_name": filing.get("managerName", ""),
            "filing_date": filing.get("filingDate", ""),
            "holdings_count": len(holdings),
            "total_value": sum(h.get("value", 0) for h in holdings),
            "positions": [
                {
                    "ticker": h.get("ticker", ""),
                    "shares": h.get("shares", 0),
                    "value": h.get("value", 0),
                    "percentage": h.get("percentage", 0),
                }
                for h in holdings
            ],
        }

    async def close(self):
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()