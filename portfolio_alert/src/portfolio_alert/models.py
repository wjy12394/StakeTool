from dataclasses import dataclass


@dataclass(frozen=True)
class Holding:
    code: str
    name: str
    shares: float
    cost_price: float
    enabled: bool = True
    remark: str = ""


@dataclass(frozen=True)
class PositionResult:
    code: str
    name: str
    shares: float
    cost_price: float
    latest_price: float | None
    cost_amount: float
    market_value: float
    pnl: float
    pnl_ratio: float


@dataclass(frozen=True)
class PortfolioResult:
    items: list[PositionResult]
    total_cost: float
    total_market_value: float
    total_pnl: float
    total_pnl_ratio: float


@dataclass(frozen=True)
class TradingTimeConfig:
    morning_start: str
    morning_end: str
    afternoon_start: str
    afternoon_end: str
    skip_weekends: bool


@dataclass(frozen=True)
class AlertConfig:
    total_loss_threshold: float
    single_loss_threshold: float
    total_profit_threshold: float
    single_profit_threshold: float
    cooldown_sec: int
    notify_on_recover: bool


@dataclass(frozen=True)
class MarketDataConfig:
    provider: str
    retry_count: int
    retry_interval_sec: int


@dataclass(frozen=True)
class LogConfig:
    level: str
    file: str


@dataclass(frozen=True)
class ConsoleConfig:
    silent: bool
    show_startup_summary: bool
    show_non_trading_message: bool
    show_portfolio_each_refresh: bool


@dataclass(frozen=True)
class DailyReportConfig:
    enabled: bool
    report_time: str


@dataclass(frozen=True)
class AppConfig:
    refresh_interval_sec: int
    trading_time: TradingTimeConfig
    alert: AlertConfig
    market_data: MarketDataConfig
    log: LogConfig
    console: ConsoleConfig
    daily_report: DailyReportConfig
