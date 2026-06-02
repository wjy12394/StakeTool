import sys
import types

import pandas as pd

from portfolio_alert.market_data import AkshareMarketDataProvider


class DummyLogger:
    def __init__(self) -> None:
        self.messages: list[tuple[str, tuple[object, ...]]] = []

    def warning(self, message: str, *args: object) -> None:
        self.messages.append((message, args))

    def error(self, message: str, *args: object) -> None:
        self.messages.append((message, args))

    def debug(self, message: str, *args: object) -> None:
        self.messages.append((message, args))


def test_akshare_provider_uses_only_etf_spot_data():
    class Provider(AkshareMarketDataProvider):
        def __init__(self) -> None:
            super().__init__(DummyLogger())
            self.stock_called = False

        def _fetch_etf_spot(self) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {"代码": "510300", "最新价": 4.86},
                    {"代码": "562500", "最新价": 1.10},
                ]
            )

        def _fetch_stock_spot(self) -> pd.DataFrame:
            self.stock_called = True
            return pd.DataFrame([{"代码": "000001", "最新价": 12.3}])

    provider = Provider()

    prices = provider.get_latest_prices(["510300", "000001"])

    assert prices == {"510300": 4.86}
    assert provider.stock_called is False


def test_akshare_progress_output_is_suppressed(capsys, monkeypatch):
    fake_akshare = types.SimpleNamespace()

    def fake_fund_etf_spot_em():
        print("21%|████████████")
        print("progress on stderr", file=sys.stderr)
        return pd.DataFrame([{"代码": "510300", "最新价": 4.86}])

    fake_akshare.fund_etf_spot_em = fake_fund_etf_spot_em
    monkeypatch.setitem(sys.modules, "akshare", fake_akshare)

    provider = AkshareMarketDataProvider(DummyLogger())
    frame = provider._fetch_etf_spot()

    captured = capsys.readouterr()
    assert frame is not None
    assert captured.out == ""
    assert captured.err == ""
