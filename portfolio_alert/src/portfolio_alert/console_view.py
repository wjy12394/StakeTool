from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import logging
from pathlib import Path

from .models import Holding, PortfolioResult
from .market_data import get_latest_prices
from .portfolio import calculate_portfolio
from .scheduler import get_next_refresh_time, is_trading_time
from .snapshot import load_snapshot, snapshot_is_stale


def format_startup_summary(
    is_trading: bool,
    holdings: list[Holding],
    refresh_interval_sec: int,
    next_refresh_time: datetime,
    portfolio_result: PortfolioResult | None,
    show_non_trading_message: bool = True,
    snapshot_saved_at: datetime | None = None,
    snapshot_stale: bool = False,
) -> str:
    lines = [
        "Portfolio Alert 已启动",
        "当前为交易时间" if is_trading else "当前为非交易时间",
        f"启用持仓：{len(holdings)} 只",
        f"刷新频率：{_format_interval(refresh_interval_sec)}",
        "",
    ]

    if is_trading:
        if portfolio_result is None:
            lines.extend(["当前暂未获取到有效行情。", ""])
        else:
            lines.extend(_format_portfolio_block(portfolio_result))
            if snapshot_saved_at is not None:
                lines.append(f"缓存时间：{snapshot_saved_at:%Y-%m-%d %H:%M:%S}")
            if snapshot_stale:
                lines.append("缓存较旧，仅供参考。")
            lines.append("")
        lines.append(f"下一次刷新时间：{next_refresh_time:%Y-%m-%d %H:%M:%S}")
        return "\n".join(lines)

    if portfolio_result is None:
        lines.extend(
            [
                "当前为非交易时间，且暂未获取到有效行情。",
                "程序将在下一个交易时段自动刷新。",
                f"下一次交易刷新时间：{next_refresh_time:%Y-%m-%d %H:%M:%S}",
            ]
        )
        return "\n".join(lines)

    if show_non_trading_message:
        lines.extend(
            [
                "非交易时间说明：",
                "当前不再高频请求实时行情。",
                "程序将在下一个交易时段自动刷新。",
                "",
                "最近一次可用组合状态：",
            ]
        )
    lines.extend(_format_summary_lines(portfolio_result))
    if snapshot_saved_at is not None:
        lines.append(f"缓存时间：{snapshot_saved_at:%Y-%m-%d %H:%M:%S}")
    if snapshot_stale:
        lines.append("缓存较旧，仅供参考。")
    lines.append("")
    lines.append(f"下一次交易刷新时间：{next_refresh_time:%Y-%m-%d %H:%M:%S}")
    return "\n".join(lines)


def print_startup_summary(
    config,
    holdings: list[Holding],
    logger: logging.Logger,
    now: datetime | None = None,
    snapshot_path: Path | str | None = None,
) -> PortfolioResult | None:
    if not config.console.show_startup_summary:
        return None

    current_time = now or datetime.now()
    trading = is_trading_time(current_time, config.trading_time)
    snapshot = load_snapshot(snapshot_path) if snapshot_path is not None else None
    result = None
    snapshot_saved_at = None
    snapshot_stale = False

    if not trading and snapshot is not None:
        result = snapshot.result
        snapshot_saved_at = snapshot.saved_at
        snapshot_stale = snapshot_is_stale(snapshot.saved_at, current_time)
    else:
        result = _try_get_startup_portfolio(
            config,
            holdings,
            logger,
            timeout_sec=config.console.startup_quote_timeout_sec,
        )
        if result is None and snapshot is not None:
            result = snapshot.result
            snapshot_saved_at = snapshot.saved_at
            snapshot_stale = snapshot_is_stale(snapshot.saved_at, current_time)
    next_refresh = get_next_refresh_time(
        current_time,
        trading_time=config.trading_time,
        refresh_interval_sec=config.refresh_interval_sec,
    )
    print(
        format_startup_summary(
            is_trading=trading,
            holdings=holdings,
            refresh_interval_sec=config.refresh_interval_sec,
            next_refresh_time=next_refresh,
            portfolio_result=result,
            show_non_trading_message=config.console.show_non_trading_message,
            snapshot_saved_at=snapshot_saved_at,
            snapshot_stale=snapshot_stale,
        )
    )
    return result


def _try_get_startup_portfolio(
    config,
    holdings: list[Holding],
    logger: logging.Logger,
    timeout_sec: float,
) -> PortfolioResult | None:
    if not holdings:
        return None

    def fetch_prices():
        return get_latest_prices([holding.code for holding in holdings], config.market_data, logger)

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fetch_prices)
    try:
        prices = future.result(timeout=timeout_sec)
    except TimeoutError:
        future.cancel()
        logger.error("启动摘要行情获取超过 %.1f 秒，改用缓存或稍后刷新", timeout_sec)
        executor.shutdown(wait=False, cancel_futures=True)
        return None
    except Exception as exc:
        logger.error("启动摘要行情获取失败: %s", exc)
        executor.shutdown(wait=False, cancel_futures=True)
        return None
    finally:
        if future.done():
            executor.shutdown(wait=False, cancel_futures=True)
    if not prices:
        return None
    return calculate_portfolio(holdings, prices)


def _format_portfolio_block(result: PortfolioResult) -> list[str]:
    lines = _format_summary_lines(result)
    lines.extend(
        [
            "",
            f"{'代码':<10}{'名称':<12}{'最新价':>10}{'市值':>12}{'盈亏':>12}{'收益率':>10}",
        ]
    )
    for item in result.items:
        latest_price = f"{item.latest_price:.3f}" if item.latest_price is not None else "缺失"
        lines.append(
            f"{item.code:<10}{item.name:<12}{latest_price:>10}"
            f"{item.market_value:>12.2f}{_format_signed_money(item.pnl):>12}"
            f"{_format_signed_ratio(item.pnl_ratio):>10}"
        )
    return lines


def _format_summary_lines(result: PortfolioResult) -> list[str]:
    return [
        f"当前组合市值：{result.total_market_value:.2f} 元",
        f"总成本：{result.total_cost:.2f} 元",
        f"总盈亏：{_format_signed_money(result.total_pnl)}",
        f"总收益率：{_format_signed_ratio(result.total_pnl_ratio)}",
    ]


def _format_signed_money(value: float) -> str:
    return f"{value:+.2f} 元"


def _format_signed_ratio(value: float) -> str:
    return f"{value:+.2f}%"


def _format_interval(seconds: int) -> str:
    if seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes} 分钟"
    return f"{seconds} 秒"
