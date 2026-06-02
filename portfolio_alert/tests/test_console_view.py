from datetime import datetime
import time

from portfolio_alert.config_loader import load_config
from portfolio_alert.console_view import format_startup_summary, print_startup_summary
from portfolio_alert.models import Holding, PortfolioResult, PositionResult


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
                pnl_ratio=1.395833,
            ),
            PositionResult(
                code="562500",
                name="机器人ETF",
                shares=5300,
                cost_price=1.126,
                latest_price=1.103,
                cost_amount=5967.8,
                market_value=5845.9,
                pnl=-121.9,
                pnl_ratio=-2.04263,
            ),
        ],
        total_cost=11727.8,
        total_market_value=11686.3,
        total_pnl=-41.5,
        total_pnl_ratio=-0.35387,
    )


def sample_holdings() -> list[Holding]:
    return [
        Holding("510300", "沪深300ETF", 1200, 4.8),
        Holding("562500", "机器人ETF", 5300, 1.126),
    ]


def test_format_startup_summary_for_trading_time_contains_portfolio_table():
    text = format_startup_summary(
        is_trading=True,
        holdings=sample_holdings(),
        refresh_interval_sec=900,
        next_refresh_time=datetime(2026, 6, 2, 10, 15),
        portfolio_result=sample_result(),
    )

    assert "Portfolio Alert 已启动" in text
    assert "当前为交易时间" in text
    assert "启用持仓：2 只" in text
    assert "刷新频率：15 分钟" in text
    assert "当前组合市值：11686.30 元" in text
    assert "总盈亏：-41.50 元" in text
    assert "510300" in text
    assert "+80.40" in text
    assert "下一次刷新时间：2026-06-02 10:15:00" in text


def test_format_startup_summary_for_non_trading_without_prices_does_not_crash():
    text = format_startup_summary(
        is_trading=False,
        holdings=sample_holdings(),
        refresh_interval_sec=900,
        next_refresh_time=datetime(2026, 6, 3, 9, 30),
        portfolio_result=None,
    )

    assert "当前为非交易时间" in text
    assert "暂未获取到有效行情" in text
    assert "下一次交易刷新时间：2026-06-03 09:30:00" in text


def test_print_startup_summary_non_trading_without_prices_does_not_crash(tmp_path, capsys, monkeypatch):
    config = load_config(tmp_path / "config.yaml")

    def fake_prices(*args, **kwargs):
        return {}

    monkeypatch.setattr("portfolio_alert.console_view.get_latest_prices", fake_prices)
    result = print_startup_summary(
        config,
        sample_holdings(),
        logger=NoopLogger(),
        now=datetime(2026, 6, 2, 16, 0),
    )

    output = capsys.readouterr().out
    assert result is None
    assert "当前为非交易时间" in output
    assert "暂未获取到有效行情" in output


def test_print_startup_summary_non_trading_uses_snapshot_when_prices_missing(tmp_path, capsys, monkeypatch):
    from portfolio_alert.snapshot import save_snapshot

    config = load_config(tmp_path / "config.yaml")
    snapshot_path = tmp_path / "data" / "latest_snapshot.json"
    save_snapshot(snapshot_path, sample_result(), datetime(2026, 6, 1, 15, 1), is_trading_time=True)

    def fake_prices(*args, **kwargs):
        return {}

    monkeypatch.setattr("portfolio_alert.console_view.get_latest_prices", fake_prices)
    result = print_startup_summary(
        config,
        sample_holdings(),
        logger=NoopLogger(),
        now=datetime(2026, 6, 2, 16, 0),
        snapshot_path=snapshot_path,
    )

    output = capsys.readouterr().out
    assert result is not None
    assert "最近一次可用组合状态" in output
    assert "当前组合市值：11686.30 元" in output


def test_print_startup_summary_non_trading_uses_snapshot_without_fetching_prices(tmp_path, capsys, monkeypatch):
    from portfolio_alert.snapshot import save_snapshot

    config = load_config(tmp_path / "config.yaml")
    snapshot_path = tmp_path / "data" / "latest_snapshot.json"
    save_snapshot(snapshot_path, sample_result(), datetime(2026, 6, 1, 15, 1), is_trading_time=True)
    called = {"prices": False}

    def fake_prices(*args, **kwargs):
        called["prices"] = True
        return {"510300": 4.86}

    monkeypatch.setattr("portfolio_alert.console_view.get_latest_prices", fake_prices)
    result = print_startup_summary(
        config,
        sample_holdings(),
        logger=NoopLogger(),
        now=datetime(2026, 6, 2, 16, 0),
        snapshot_path=snapshot_path,
    )

    output = capsys.readouterr().out
    assert result is not None
    assert called["prices"] is False
    assert "最近一次可用组合状态" in output


def test_print_startup_summary_trading_time_times_out_and_uses_snapshot(tmp_path, capsys, monkeypatch):
    from portfolio_alert.snapshot import save_snapshot

    config = load_config(tmp_path / "config.yaml")
    object.__setattr__(config.console, "startup_quote_timeout_sec", 0.05)
    snapshot_path = tmp_path / "data" / "latest_snapshot.json"
    save_snapshot(snapshot_path, sample_result(), datetime(2026, 6, 1, 15, 1), is_trading_time=True)

    def slow_prices(*args, **kwargs):
        time.sleep(1)
        return {"510300": 4.86}

    monkeypatch.setattr("portfolio_alert.console_view.get_latest_prices", slow_prices)
    start = time.perf_counter()
    result = print_startup_summary(
        config,
        sample_holdings(),
        logger=NoopLogger(),
        now=datetime(2026, 6, 2, 10, 0),
        snapshot_path=snapshot_path,
    )
    elapsed = time.perf_counter() - start

    output = capsys.readouterr().out
    assert result is not None
    assert elapsed < 0.5
    assert "缓存时间：2026-06-01 15:01:00" in output


def test_print_startup_summary_marks_stale_snapshot(tmp_path, capsys, monkeypatch):
    from portfolio_alert.snapshot import save_snapshot

    config = load_config(tmp_path / "config.yaml")
    snapshot_path = tmp_path / "data" / "latest_snapshot.json"
    save_snapshot(snapshot_path, sample_result(), datetime(2026, 5, 20, 15, 1), is_trading_time=True)

    def fake_prices(*args, **kwargs):
        return {}

    monkeypatch.setattr("portfolio_alert.console_view.get_latest_prices", fake_prices)
    print_startup_summary(
        config,
        sample_holdings(),
        logger=NoopLogger(),
        now=datetime(2026, 6, 2, 16, 0),
        snapshot_path=snapshot_path,
    )

    output = capsys.readouterr().out
    assert "缓存较旧，仅供参考" in output


class NoopLogger:
    def error(self, *args, **kwargs):
        pass
