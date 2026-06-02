from datetime import datetime

from portfolio_alert.models import PortfolioResult
from portfolio_alert.notifier import Alert
from portfolio_alert.models import TradingTimeConfig
from portfolio_alert.scheduler import (
    DailyReportState,
    build_daily_report_alert,
    get_next_refresh_time,
    should_send_daily_report,
)


def empty_result() -> PortfolioResult:
    return PortfolioResult(items=[], total_cost=0, total_market_value=0, total_pnl=0, total_pnl_ratio=0)


def test_daily_report_sends_once_after_close_time_on_trading_day():
    state = DailyReportState()

    first = should_send_daily_report(
        datetime(2026, 6, 2, 15, 6),
        report_time="15:05",
        skip_weekends=True,
        state=state,
    )
    second = should_send_daily_report(
        datetime(2026, 6, 2, 15, 30),
        report_time="15:05",
        skip_weekends=True,
        state=state,
    )

    assert first is True
    assert second is False


def test_daily_report_skips_weekends():
    state = DailyReportState()

    assert (
        should_send_daily_report(
            datetime(2026, 6, 6, 15, 6),
            report_time="15:05",
            skip_weekends=True,
            state=state,
        )
        is False
    )


def test_build_daily_report_alert_contains_summary():
    alert = build_daily_report_alert(empty_result())

    assert isinstance(alert, Alert)
    assert alert.kind == "daily_report"
    assert "收盘日报" in alert.title
    assert "组合市值" in alert.message


def trading_config() -> TradingTimeConfig:
    return TradingTimeConfig(
        morning_start="09:30",
        morning_end="11:30",
        afternoon_start="13:00",
        afternoon_end="15:00",
        skip_weekends=True,
    )


def test_get_next_refresh_time_during_trading_time():
    result = get_next_refresh_time(
        datetime(2026, 6, 2, 10, 7),
        trading_time=trading_config(),
        refresh_interval_sec=900,
    )

    assert result == datetime(2026, 6, 2, 10, 15)


def test_get_next_refresh_time_during_lunch_break():
    result = get_next_refresh_time(
        datetime(2026, 6, 2, 12, 5),
        trading_time=trading_config(),
        refresh_interval_sec=900,
    )

    assert result == datetime(2026, 6, 2, 13, 0)


def test_get_next_refresh_time_after_close():
    result = get_next_refresh_time(
        datetime(2026, 6, 2, 15, 30),
        trading_time=trading_config(),
        refresh_interval_sec=900,
    )

    assert result == datetime(2026, 6, 3, 9, 30)


def test_get_next_refresh_time_on_weekend():
    result = get_next_refresh_time(
        datetime(2026, 6, 6, 10, 0),
        trading_time=trading_config(),
        refresh_interval_sec=900,
    )

    assert result == datetime(2026, 6, 8, 9, 30)
