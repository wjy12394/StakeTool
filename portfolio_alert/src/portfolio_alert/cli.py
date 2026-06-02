from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import logging

from .console_view import format_startup_summary
from .market_data import get_latest_prices
from .models import AppConfig, Holding, PortfolioResult
from .portfolio import calculate_portfolio
from .scheduler import get_next_refresh_time, is_trading_time
from .snapshot import load_snapshot, save_snapshot, snapshot_is_stale


@dataclass(frozen=True)
class CliOptions:
    once: bool
    no_cache: bool
    debug: bool


def parse_args(argv: list[str] | None = None) -> CliOptions:
    parser = ArgumentParser(description="Portfolio Alert 长期持仓监控器")
    parser.add_argument("--once", action="store_true", help="只刷新并打印一次组合状态，然后退出")
    parser.add_argument("--no-cache", action="store_true", help="不读取缓存，强制请求实时行情")
    parser.add_argument("--debug", action="store_true", help="在控制台显示更详细日志")
    args = parser.parse_args(argv)
    return CliOptions(once=args.once, no_cache=args.no_cache, debug=args.debug)


def run_once(
    config: AppConfig,
    holdings: list[Holding],
    logger: logging.Logger,
    snapshot_path: Path | str,
    no_cache: bool = False,
    now: datetime | None = None,
) -> PortfolioResult | None:
    current_time = now or datetime.now()
    trading = is_trading_time(current_time, config.trading_time)
    snapshot = None if no_cache else load_snapshot(snapshot_path)

    if not trading and snapshot is not None:
        return _print_snapshot_summary(config, holdings, current_time, snapshot)

    result = _fetch_once(config, holdings, logger)
    if result is not None:
        save_snapshot(snapshot_path, result, current_time, is_trading_time=trading)
        _print_summary(config, holdings, current_time, trading, result)
        return result

    if snapshot is not None:
        return _print_snapshot_summary(config, holdings, current_time, snapshot)

    _print_summary(config, holdings, current_time, trading, None)
    if no_cache:
        print("未获取到有效实时行情，且已禁用缓存。")
    else:
        print("未获取到有效实时行情，也没有可用缓存。")
    return None


def _fetch_once(config: AppConfig, holdings: list[Holding], logger: logging.Logger) -> PortfolioResult | None:
    try:
        prices = get_latest_prices([holding.code for holding in holdings], config.market_data, logger)
    except Exception as exc:
        logger.error("单次刷新行情获取失败: %s", exc)
        return None
    if not prices:
        return None
    return calculate_portfolio(holdings, prices)


def _print_summary(
    config: AppConfig,
    holdings: list[Holding],
    now: datetime,
    trading: bool,
    result: PortfolioResult | None,
) -> None:
    print(
        format_startup_summary(
            is_trading=trading,
            holdings=holdings,
            refresh_interval_sec=config.refresh_interval_sec,
            next_refresh_time=get_next_refresh_time(now, config.trading_time, config.refresh_interval_sec),
            portfolio_result=result,
            show_non_trading_message=config.console.show_non_trading_message,
        )
    )


def _print_snapshot_summary(config: AppConfig, holdings: list[Holding], now: datetime, snapshot) -> PortfolioResult:
    stale = snapshot_is_stale(snapshot.saved_at, now)
    print(
        format_startup_summary(
            is_trading=is_trading_time(now, config.trading_time),
            holdings=holdings,
            refresh_interval_sec=config.refresh_interval_sec,
            next_refresh_time=get_next_refresh_time(now, config.trading_time, config.refresh_interval_sec),
            portfolio_result=snapshot.result,
            show_non_trading_message=config.console.show_non_trading_message,
            snapshot_saved_at=snapshot.saved_at,
            snapshot_stale=stale,
        )
    )
    return snapshot.result
