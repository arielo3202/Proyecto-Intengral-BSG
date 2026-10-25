from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from app.services.audit_service import immutable_audit_service
from app.services.financial_quant import FinancialDataError, quant_market_service


class TestQuantAndAudit(unittest.TestCase):
    def test_quant_indicators_and_verified_series(self) -> None:
        series = quant_market_service.fetch_and_validate_series("MELI", expected_currency="USD")
        metrics = quant_market_service.compute_indicators(series)
        self.assertEqual(metrics["ticker"], "MELI")
        self.assertEqual(metrics["currency"], "USD")
        self.assertGreater(metrics["sma_20"], 0)
        self.assertGreater(metrics["ema_12"], 0)
        self.assertTrue(0.0 <= metrics["rsi_14"] <= 100.0)
        self.assertGreater(metrics["annualized_volatility_pct"], 0)

    def test_quant_rejects_currency_mismatch_and_unlicensed_ticker(self) -> None:
        with self.assertRaises(FinancialDataError) as ctx_curr:
            quant_market_service.fetch_and_validate_series("WALMEX.MX", expected_currency="USD")
        self.assertEqual(ctx_curr.exception.code, "CURRENCY_MISMATCH")

        with self.assertRaises(FinancialDataError) as ctx_cov:
            quant_market_service.fetch_and_validate_series("UNKNOWN_TICKER_XYZ", expected_currency="USD")
        self.assertEqual(ctx_cov.exception.code, "TICKER_NOT_COVERED")

    def test_quant_rejects_stale_and_anomalous_prices(self) -> None:
        stale_ts = datetime.now(timezone.utc) - timedelta(days=5)
        with self.assertRaises(FinancialDataError) as ctx_stale:
            quant_market_service.fetch_and_validate_series(
                "AAPL", expected_currency="USD", injected_timestamp_utc=stale_ts
            )
        self.assertEqual(ctx_stale.exception.code, "STALE_MARKET_DATA")

        anomalous_closes = [220.0] * 19 + [500.0]
        with self.assertRaises(FinancialDataError) as ctx_anom:
            quant_market_service.fetch_and_validate_series(
                "AAPL", expected_currency="USD", injected_closes=anomalous_closes
            )
        self.assertEqual(ctx_anom.exception.code, "ANOMALOUS_PRICE")

    def test_immutable_audit_sha256_hash_chain(self) -> None:
        rec1 = immutable_audit_service.record_event(
            event_type="UNIT_TEST_EVENT_1",
            user_id="usr-test",
            user_role="admin",
            session_id="sess-test-01",
            provider_used="vertex_ai",
            model_used="gemini-2.5-flash",
            total_tokens=150,
            cost_usd=0.000045,
            latency_ms=112.4,
            circuit_breaker_state="CLOSED",
        )
        rec2 = immutable_audit_service.record_event(
            event_type="UNIT_TEST_EVENT_2",
            user_id="usr-test",
            user_role="admin",
            session_id="sess-test-01",
            provider_used="ollama_fallback",
            model_used="llama3.2:3b",
            total_tokens=210,
            cost_usd=0.0,
            latency_ms=95.0,
            circuit_breaker_state="OPEN",
        )
        self.assertEqual(rec2["prev_hash"], rec1["record_hash"])
        verification = immutable_audit_service.verify_chain_integrity()
        self.assertTrue(verification["is_valid"])
        self.assertEqual(verification["status"], "CHAIN_INTACT_SHA256_VERIFIED")


if __name__ == "__main__":
    unittest.main()
