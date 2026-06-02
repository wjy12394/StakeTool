from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import logging
import time
from typing import Protocol

import pandas as pd

from .holdings_loader import normalize_code
from .models import MarketDataConfig


class MarketDataProvider(Protocol):
    def get_latest_prices(self, codes: list[str]) -> dict[str, float]:
        ...


class AkshareMarketDataProvider:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger(__name__)

    def get_latest_prices(self, codes: list[str]) -> dict[str, float]:
        normalized = [normalize_code(code) for code in codes]
        prices: dict[str, float] = {}
        frames = [self._fetch_etf_spot()]

        for frame in frames:
            if frame is None or frame.empty:
                continue
            code_column = _find_column(frame, ["代码", "证券代码", "symbol"])
            price_column = _find_column(frame, ["最新价", "最新价格", "现价", "price"])
            if not code_column or not price_column:
                self.logger.warning("行情字段未识别，可用字段: %s", list(frame.columns))
                continue
            frame = frame.copy()
            frame[code_column] = frame[code_column].astype(str).map(normalize_code)
            matched = frame[frame[code_column].isin(normalized)]
            for _, row in matched.iterrows():
                try:
                    prices[str(row[code_column])] = float(row[price_column])
                except (TypeError, ValueError):
                    self.logger.warning("价格解析失败: %s", row.to_dict())

        missing = sorted(set(normalized) - set(prices))
        if missing:
            self.logger.warning("以下证券未获取到价格: %s", ", ".join(missing))
        return prices

    def _fetch_etf_spot(self) -> pd.DataFrame | None:
        try:
            import akshare as ak

            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                return ak.fund_etf_spot_em()
        except Exception as exc:
            self.logger.error("AKShare ETF 行情获取失败: %s", exc)
            return None


def get_latest_prices(
    codes: list[str],
    config: MarketDataConfig | None = None,
    logger: logging.Logger | None = None,
) -> dict[str, float]:
    log = logger or logging.getLogger(__name__)
    provider = AkshareMarketDataProvider(log)
    retry_count = config.retry_count if config else 1
    retry_interval = config.retry_interval_sec if config else 0

    for attempt in range(1, retry_count + 1):
        try:
            prices = provider.get_latest_prices(codes)
            if prices:
                return prices
        except Exception as exc:
            log.error("行情接口异常，第 %s 次尝试失败: %s", attempt, exc)
        if attempt < retry_count:
            time.sleep(retry_interval)
    return {}


def _find_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    return None
