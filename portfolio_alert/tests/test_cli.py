from datetime import datetime

from portfolio_alert.cli import parse_args, run_once
from portfolio_alert.config_loader import load_config
from portfolio_alert.models import Holding, PortfolioResult, PositionResult
from portfolio_alert.snapshot import load_snapshot, save_snapshot


def sample_result() -> PortfolioResult:
    return PortfolioResult(
        items=[
            PositionResult(
                code="510300",
                name="沪深300ETF",
                shares=100,
                cost_price=4.0,
                latest_price=4.5,
                cost_amount=400,
                market_value=450,
                pnl=50,
                pnl_ratio=12.5,
            )
        ],
        total_cost=400,
        total_market_value=450,
        total_pnl=50,
        total_pnl_ratio=12.5,
    )


def test_parse_once_and_no_cache_args():
    options = parse_args(["--once", "--no-cache"])

    assert options.once is True
    assert options.no_cache is True


def test_parse_debug_arg():
    options = parse_args(["--debug"])

    assert options.debug is True


def test_run_once_fetches_prices_prints_summary_and_saves_snapshot(tmp_path, capsys, monkeypatch):
    config = load_config(tmp_path / "config.yaml")
    snapshot_path = tmp_path / "data" / "latest_snapshot.json"
    holdings = [Holding("510300", "沪深300ETF", 100, 4.0, True, "")]

    def fake_prices(*args, **kwargs):
        return {"510300": 4.5}

    monkeypatch.setattr("portfolio_alert.cli.get_latest_prices", fake_prices)

    result = run_once(
        config,
        holdings,
        NoopLogger(),
        snapshot_path=snapshot_path,
        no_cache=False,
        now=datetime(2026, 6, 2, 10, 0),
    )

    output = capsys.readouterr().out
    snapshot = load_snapshot(snapshot_path)
    assert result is not None
    assert snapshot is not None
    assert snapshot.result.total_market_value == 450
    assert "Portfolio Alert 已启动" in output
    assert "当前组合市值：450.00 元" in output


def test_run_once_no_cache_does_not_read_snapshot_when_prices_fail(tmp_path, capsys, monkeypatch):
    config = load_config(tmp_path / "config.yaml")
    snapshot_path = tmp_path / "data" / "latest_snapshot.json"
    save_snapshot(snapshot_path, sample_result(), datetime(2026, 6, 1, 15, 1), is_trading_time=True)
    holdings = [Holding("510300", "沪深300ETF", 100, 4.0, True, "")]

    def no_prices(*args, **kwargs):
        return {}

    monkeypatch.setattr("portfolio_alert.cli.get_latest_prices", no_prices)

    result = run_once(
        config,
        holdings,
        NoopLogger(),
        snapshot_path=snapshot_path,
        no_cache=True,
        now=datetime(2026, 6, 2, 10, 0),
    )

    output = capsys.readouterr().out
    assert result is None
    assert "未获取到有效实时行情，且已禁用缓存" in output
    assert "当前组合市值：450.00 元" not in output


class NoopLogger:
    def info(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass
