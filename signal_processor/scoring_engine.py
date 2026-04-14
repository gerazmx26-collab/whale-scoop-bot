"""Signal scoring engine for high-conviction institutional signals."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from utils.config import Config
from utils.logger import setup_logger


logger = setup_logger("scoring_engine")


class ScoringEngine:
    """Engine to score and filter trading signals."""

    # Weight factors for scoring
    WEIGHTS = {
        "code_p": 30,          # Open Market Purchase
        "cluster_buy": 25,      # Multiple execs buying
        "ceo_cfo": 20,          # CEO/CFO purchases
        "high_conviction": 15,    # Outside blacko months
        "dix_spike": 10,         # DIX Index elevated
    }

    def __init__(self, config: Config):
        self.config = config
        self.recent_filings: dict[str, list[dict]] = defaultdict(list)
        self.cluster_cache: dict[str, list[datetime]] = defaultdict(list)

    def calculate_score(self, filing: dict) -> float:
        """Calculate conviction score for a filing."""
        score = 0.0
        ticker = filing.get("ticker", "")

        if not ticker:
            return 0.0

        # 1. Code P filter (mandatory)
        if filing.get("transaction_code") == "P":
            score += self.WEIGHTS["code_p"]
            logger.debug(f"[SIGNAL] {ticker}: +{self.WEIGHTS['code_p']} for Code P")

        # 2. CEO/CFO filter
        if filing.get("is_ceo") or filing.get("is_cfo"):
            score += self.WEIGHTS["ceo_cfo"]
            logger.debug(f"[SIGNAL] {ticker}: +{self.WEIGHTS['ceo_cfo']} for CEO/CFO")

        # 3. Cluster buy detection
        if self._check_cluster_buy(filing):
            score += self.WEIGHTS["cluster_buy"]
            logger.debug(f"[SIGNAL] {ticker}: +{self.WEIGHTS['cluster_buy']} for Cluster Buy")

        # 4. I-Ratio / Seasonal check
        if self._is_high_conviction_seasonal(filing):
            score += self.WEIGHTS["high_conviction"]
            logger.debug(f"[SIGNAL] {ticker}: +{self.WEIGHTS['high_conviction']} for High Conviction")

        # 5. VWAP reference (placeholder for live data)
        if self._check_vwap_confirmation(filing):
            score += self.WEIGHTS["dix_spike"]
            logger.debug(f"[SIGNAL] {ticker}: +{self.WEIGHTS['dix_spike']} for VWAP confirmation")

        # Store for cluster tracking
        self._update_cluster_cache(filing)

        logger.info(f"[SIGNAL] {ticker}: Final score = {score}/{sum(self.WEIGHTS.values())}")
        return score

    def _check_cluster_buy(self, filing: dict) -> bool:
        """Check if multiple executives buying in window."""
        ticker = filing.get("ticker", "")
        filing_date = self._parse_date(filing.get("filing_date"))

        if not filing_date:
            return False

        window = timedelta(days=self.config.min_cluster_window_days)
        cutoff = filing_date - window

        # Check recent filings for same ticker
        recent = [
            f for f in self.recent_filings[ticker]
            if self._parse_date(f.get("filing_date")) >= cutoff
        ]

        return len(recent) >= 2

    def _is_high_conviction_seasonal(self, filing: dict) -> bool:
        """Check if purchase is outside standard blackout months."""
        filing_date = self._parse_date(filing.get("filing_date"))

        if not filing_date:
            return False

        month = filing_date.month

        # Outside blackout months means HIGH conviction
        return month not in self.config.seasonal_blackout_months

    def _check_vwap_confirmation(self, filing: dict) -> bool:
        """Check if price is above VWAP (placeholder logic)."""
        # In production, this would fetch real-time price data
        # For now, assume true if signal is strong
        return True

    def _update_cluster_cache(self, filing: dict):
        """Update cluster tracking for ticker."""
        ticker = filing.get("ticker", "")
        filing_date = self._parse_date(filing.get("filing_date"))

        if ticker and filing_date:
            self.recent_filings[ticker].append(filing)
            self.cluster_cache[ticker].append(filing_date)

            # Cleanup old entries
            cutoff = datetime.now() - timedelta(days=30)
            self.recent_filings[ticker] = [
                f for f in self.recent_filings[ticker]
                if self._parse_date(f.get("filing_date")) >= cutoff
            ]

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string."""
        if not date_str:
            return None

        formats = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    def check_window_dressing(self, ticker: str, fundamentals: dict) -> bool:
        """Check for window dressing manipulation.

        Args:
            ticker: Stock ticker
            fundamentals: Dict with sales_growth, inventory_growth_rate, margin_growth

        Returns:
            True if detected as window dressing/manipulation
        """
        sales_growth = fundamentals.get("sales_growth", 0)
        inventory_growth = fundamentals.get("inventory_growth_rate", 0)
        margin_growth = fundamentals.get("margin_growth", 0)

        # Window dressing pattern:
        # - Sales growth > 0 (to cross 50% threshold)
        # - Inventory growth < 0 (clearing inventory)
        # - Margins decreasing (price cutting)
        is_manipulation = (
            sales_growth > 0 and
            inventory_growth < 0 and
            margin_growth < 0
        )

        if is_manipulation:
            logger.warning(f"[SIGNAL] {ticker}: Window dressing detected, signal rejected")

        return is_manipulation

    def get_top_signals(self, min_score: float = None) -> list[dict]:
        """Get top scoring signals."""
        if min_score is None:
            min_score = self.config.min_signal_score

        all_signals = []

        for ticker, filings in self.recent_filings.items():
            for filing in filings:
                score = self._cached_scores.get(ticker, 0)
                if score >= min_score:
                    all_signals.append({
                        "ticker": ticker,
                        "score": score,
                        "filing": filing,
                    })

        return sorted(all_signals, key=lambda x: x["score"], reverse=True)

    # Cache for scores (would be in Redis in production)
    _cached_scores = {}