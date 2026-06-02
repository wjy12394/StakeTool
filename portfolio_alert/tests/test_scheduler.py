from datetime import datetime

from portfolio_alert.models import PortfolioResult
from portfolio_alert.notifier import Alert
from portfolio_alert.scheduler import DailyReportState, build_daily_report_alert, should_send_daily_report


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
