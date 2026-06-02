from datetime import datetime, timedelta

from portfolio_alert.models import PortfolioResult, PositionResult
from portfolio_alert.snapshot import load_snapshot, save_snapshot, snapshot_is_stale


def sample_result() -> PortfolioResult:
    return PortfolioResult(
        items=[
            PositionResult(
                code="510300",
                name="沪深300ETF",
                shares=1200,
                cost_price=4.8,
                latest_price=4.867,
                cost_amount=5760,
                market_value=5840.4,
                pnl=80.4,
                pnl_ratio=1.4,
            )
        ],
        total_cost=5760,
        total_market_value=5840.4,
        total_pnl=80.4,
        total_pnl_ratio=1.4,
    )


def test_save_and_load_snapshot(tmp_path):
    path = tmp_path / "latest_snapshot.json"
    saved_at = datetime(2026, 6, 2, 15, 1)

    save_snapshot(path, sample_result(), saved_at, is_trading_time=True)
    snapshot = load_snapshot(path)

    assert snapshot is not None
    assert snapshot.saved_at == saved_at
    assert snapshot.is_trading_time is True
    assert snapshot.result.total_market_value == 5840.4
    assert snapshot.result.items[0].code == "510300"


def test_load_missing_snapshot_returns_none(tmp_path):
    assert load_snapshot(tmp_path / "missing.json") is None


def test_snapshot_is_stale_after_seven_days():
    snapshot_time = datetime(2026, 6, 1, 15, 0)

    assert snapshot_is_stale(snapshot_time, snapshot_time + timedelta(days=8)) is True
    assert snapshot_is_stale(snapshot_time, snapshot_time + timedelta(days=2)) is False
