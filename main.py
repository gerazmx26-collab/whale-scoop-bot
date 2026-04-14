#!/usr/bin/env python3
"""
Whale Scoop Bot - Real-Time Institutional Trading System
=====================================================
Based on institutional flow analysis and whale tracking.
Paper trading mode by default.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

from data_ingestion.sec_edgar import SECEdgarClient
from data_ingestion.whale_alerts import WhaleAlertStream
from signal_processor.scoring_engine import ScoringEngine
from execution_engine.order_manager import OrderManager
from risk_manager.risk_manager import RiskManager
from utils.config import Config
from utils.logger import setup_logger


# Global state
running = False
logger: logging.Logger = None
config: Config = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    if logger:
        logger.warning("[EXECUTION] Received shutdown signal, stopping bot...")
    running = False


async def main():
    """Main entry point for the Whale Scoop Bot."""
    global running, logger, config

    # Load configuration
    config = Config()
    logger = setup_logger("whale_scoop", config.log_level)
    logger.info("[DATA] Whale Scoop Bot starting...")

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Check mode
    if config.paper_trading_mode:
        logger.info("[EXECUTION] Running in PAPER TRADING MODE")
    else:
        logger.warning("[EXECUTION] LIVE TRADING MODE - REAL MONEY AT RISK")

    # Initialize components
    scoring_engine = ScoringEngine(config)
    risk_manager = RiskManager(config)
    order_manager = OrderManager(config, risk_manager)

    # Data ingestion clients
    sec_client = SECEdgarClient(config)
    whale_stream = WhaleAlertStream(config)

    running = True

    try:
        # Main trading loop
        while running:
            try:
                # Fetch SEC filings
                logger.debug("[DATA] Checking for new SEC filings...")
                sec_filings = await sec_client.fetch_recent_filings()

                for filing in sec_filings:
                    # Process through scoring engine
                    score = scoring_engine.calculate_score(filing)

                    if score >= config.min_signal_score:
                        logger.info(f"[SIGNAL] High conviction signal detected: {filing.get('ticker')} (score: {score})")

                        # Risk check
                        risk_check = risk_manager.check_risk(filing, score)

                        if risk_check['approved']:
                            # Execute order
                            order_result = await order_manager.execute(filing, risk_check['position_size'])

                            if order_result['success']:
                                logger.info(f"[EXECUTION] Order filled: {filing.get('ticker')} - {order_result.get('details')}")
                            else:
                                logger.warning(f"[EXECUTION] Order failed: {order_result.get('reason')}")
                        else:
                            logger.info(f"[RISK] Signal rejected: {risk_check['reason']}")

                # Check whale alerts stream
                whale_alerts = await whale_stream.get_pending_alerts()

                for alert in whale_alerts:
                    logger.info(f"[DATA] Whale Alert: {alert.get('type')} - {alert.get('amount')} {alert.get('symbol')}")

                await asyncio.sleep(config.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[ERROR] Main loop error: {e}", exc_info=True)
                await asyncio.sleep(5)

    finally:
        logger.info("[EXECUTION] Whale Scoop Bot shutting down...")
        await sec_client.close()
        await whale_stream.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")