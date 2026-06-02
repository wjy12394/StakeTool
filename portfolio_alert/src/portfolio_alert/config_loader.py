from pathlib import Path
from typing import Any

import yaml

from .models import (
    AlertConfig,
    AppConfig,
    ConsoleConfig,
    DailyReportConfig,
    LogConfig,
    MarketDataConfig,
    TradingTimeConfig,
)


DEFAULT_CONFIG: dict[str, Any] = {
    "refresh_interval_sec": 900,
    "trading_time": {
        "morning_start": "09:30",
        "morning_end": "11:30",
        "afternoon_start": "13:00",
        "afternoon_end": "15:00",
        "skip_weekends": True,
    },
    "alert": {
        "total_loss_threshold": -500,
        "single_loss_threshold": -300,
        "total_profit_threshold": 500,
        "single_profit_threshold": 300,
        "cooldown_sec": 300,
        "notify_on_recover": True,
    },
    "market_data": {
        "provider": "akshare",
        "retry_count": 3,
        "retry_interval_sec": 3,
    },
    "log": {
        "level": "INFO",
        "file": "logs/portfolio_alert.log",
    },
    "console": {
        "silent": True,
        "show_startup_summary": True,
        "show_non_trading_message": True,
        "show_portfolio_each_refresh": False,
        "startup_quote_timeout_sec": 8,
    },
    "daily_report": {
        "enabled": True,
        "report_time": "15:05",
    },
}


def load_config(path: Path | str) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            yaml.safe_dump(DEFAULT_CONFIG, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    merged = _deep_merge(DEFAULT_CONFIG, data)
    return _parse_config(merged)


def _deep_merge(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(defaults)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _parse_config(data: dict[str, Any]) -> AppConfig:
    refresh_interval = _positive_int(data["refresh_interval_sec"], "refresh_interval_sec")
    alert = data["alert"]
    market_data = data["market_data"]
    trading_time = data["trading_time"]
    log = data["log"]
    console = data["console"]
    daily_report = data["daily_report"]

    cooldown = _positive_int(alert["cooldown_sec"], "alert.cooldown_sec")
    retry_count = _positive_int(market_data["retry_count"], "market_data.retry_count")
    retry_interval = _positive_int(market_data["retry_interval_sec"], "market_data.retry_interval_sec")

    provider = str(market_data["provider"]).lower()
    if provider != "akshare":
        raise ValueError("market_data.provider 当前仅支持 akshare")

    return AppConfig(
        refresh_interval_sec=refresh_interval,
        trading_time=TradingTimeConfig(
            morning_start=_time_text(trading_time["morning_start"], "trading_time.morning_start"),
            morning_end=_time_text(trading_time["morning_end"], "trading_time.morning_end"),
            afternoon_start=_time_text(trading_time["afternoon_start"], "trading_time.afternoon_start"),
            afternoon_end=_time_text(trading_time["afternoon_end"], "trading_time.afternoon_end"),
            skip_weekends=bool(trading_time["skip_weekends"]),
        ),
        alert=AlertConfig(
            total_loss_threshold=float(alert["total_loss_threshold"]),
            single_loss_threshold=float(alert["single_loss_threshold"]),
            total_profit_threshold=float(alert["total_profit_threshold"]),
            single_profit_threshold=float(alert["single_profit_threshold"]),
            cooldown_sec=cooldown,
            notify_on_recover=bool(alert["notify_on_recover"]),
        ),
        market_data=MarketDataConfig(
            provider=provider,
            retry_count=retry_count,
            retry_interval_sec=retry_interval,
        ),
        log=LogConfig(level=str(log["level"]).upper(), file=str(log["file"])),
        console=ConsoleConfig(
            silent=bool(console.get("silent", console.get("quiet", True))),
            show_startup_summary=bool(console.get("show_startup_summary", True)),
            show_non_trading_message=bool(console.get("show_non_trading_message", True)),
            show_portfolio_each_refresh=bool(console["show_portfolio_each_refresh"]),
            startup_quote_timeout_sec=float(console.get("startup_quote_timeout_sec", 8)),
        ),
        daily_report=DailyReportConfig(
            enabled=bool(daily_report["enabled"]),
            report_time=_time_text(daily_report["report_time"], "daily_report.report_time"),
        ),
    )


def _positive_int(value: Any, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须是正整数") from exc
    if parsed <= 0:
        raise ValueError(f"{name} 必须是正整数")
    return parsed


def _time_text(value: Any, name: str) -> str:
    text = str(value)
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(f"{name} 必须是 HH:MM 格式")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"{name} 必须是有效时间")
    return f"{hour:02d}:{minute:02d}"
