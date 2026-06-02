from dataclasses import dataclass
from datetime import date, datetime, time as dt_time
import logging
import time

from .market_data import get_latest_prices
from .models import AppConfig, Holding, PortfolioResult, TradingTimeConfig
from .notifier import Alert, AlertState, evaluate_alerts, send_alert
from .portfolio import calculate_portfolio, format_portfolio


@dataclass
class DailyReportState:
    last_report_date: date | None = None


def is_trading_time(now: datetime, config: TradingTimeConfig) -> bool:
    if config.skip_weekends and now.weekday() >= 5:
        return False
    current = now.time()
    morning_start = _parse_time(config.morning_start)
    morning_end = _parse_time(config.morning_end)
    afternoon_start = _parse_time(config.afternoon_start)
    afternoon_end = _parse_time(config.afternoon_end)
    return morning_start <= current <= morning_end or afternoon_start <= current <= afternoon_end


def run_loop(config: AppConfig, holdings: list[Holding], logger: logging.Logger) -> None:
    state = AlertState()
    daily_report_state = DailyReportState()
    last_result: PortfolioResult | None = None
    if not holdings:
        logger.warning("没有启用持仓，程序将等待配置更新")

    while True:
        now = datetime.now()
        try:
            if not is_trading_time(now, config.trading_time):
                if (
                    config.daily_report.enabled
                    and last_result is not None
                    and should_send_daily_report(
                        now,
                        config.daily_report.report_time,
                        config.trading_time.skip_weekends,
                        daily_report_state,
                    )
                ):
                    alert = build_daily_report_alert(last_result)
                    logger.info("发送收盘日报: %s", alert.message.replace("\n", " "))
                    send_alert(alert, logger)
                time.sleep(60)
                continue

            codes = [holding.code for holding in holdings]
            prices = get_latest_prices(codes, config.market_data, logger)
            result = calculate_portfolio(holdings, prices)
            last_result = result
            logger.info(
                "组合汇总: 市值 %.2f 元，总盈亏 %.2f 元，收益率 %.2f%%",
                result.total_market_value,
                result.total_pnl,
                result.total_pnl_ratio,
            )
            if config.console.show_portfolio_each_refresh:
                print(f"[{now:%H:%M:%S}] {format_portfolio(result)}")

            alerts = evaluate_alerts(
                result=result,
                total_loss_threshold=config.alert.total_loss_threshold,
                single_loss_threshold=config.alert.single_loss_threshold,
                cooldown_sec=config.alert.cooldown_sec,
                notify_on_recover=config.alert.notify_on_recover,
                state=state,
                total_profit_threshold=config.alert.total_profit_threshold,
                single_profit_threshold=config.alert.single_profit_threshold,
            )
            if config.daily_report.enabled and should_send_daily_report(
                now,
                config.daily_report.report_time,
                config.trading_time.skip_weekends,
                daily_report_state,
            ):
                alerts.append(build_daily_report_alert(result))

            for alert in alerts:
                logger.warning("触发提醒: %s %s", alert.title, alert.message.replace("\n", " "))
                send_alert(alert, logger)

            time.sleep(config.refresh_interval_sec)
        except Exception as exc:
            logger.error("监控循环异常，下一轮继续: %s", exc)
            time.sleep(60)
            continue


def _parse_time(value: str) -> dt_time:
    hour, minute = value.split(":")
    return dt_time(hour=int(hour), minute=int(minute))


def should_send_daily_report(
    now: datetime,
    report_time: str,
    skip_weekends: bool,
    state: DailyReportState,
) -> bool:
    if skip_weekends and now.weekday() >= 5:
        return False
    if now.time() < _parse_time(report_time):
        return False
    if state.last_report_date == now.date():
        return False
    state.last_report_date = now.date()
    return True


def build_daily_report_alert(result: PortfolioResult) -> Alert:
    message = (
        f"组合市值：{result.total_market_value:.2f} 元\n"
        f"当日收盘浮动盈亏：{result.total_pnl:.2f} 元\n"
        f"组合收益率：{result.total_pnl_ratio:.2f}%"
    )
    return Alert(kind="daily_report", title="ETF持仓收盘日报", message=message)
