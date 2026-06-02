from pathlib import Path

import pytest

from portfolio_alert.holdings_loader import load_holdings


def write_yaml(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_load_holdings_preserves_code_and_enabled_rows(tmp_path: Path):
    config_path = write_yaml(
        tmp_path / "holdings.yaml",
        """
holdings:
  - code: "510300"
    name: "沪深300ETF"
    shares: 1200
    cost_price: 4.8
    enabled: true
    remark: "核心"
  - code: "000001"
    name: "平安银行"
    shares: 100
    cost_price: 12.3
    enabled: false
    remark: "忽略"
""",
    )

    holdings = load_holdings(config_path)

    assert len(holdings) == 1
    assert holdings[0].code == "510300"
    assert holdings[0].name == "沪深300ETF"
    assert holdings[0].shares == 1200
    assert holdings[0].cost_price == 4.8


def test_load_holdings_requires_all_columns(tmp_path: Path):
    config_path = write_yaml(
        tmp_path / "holdings.yaml",
        """
holdings:
  - code: "510300"
    name: "沪深300ETF"
    shares: 1200
    cost_price: 4.8
    enabled: true
""",
    )

    with pytest.raises(ValueError, match="缺少字段"):
        load_holdings(config_path)


def test_load_holdings_allows_zero_cost_price(tmp_path: Path, caplog):
    config_path = write_yaml(
        tmp_path / "holdings.yaml",
        """
holdings:
  - code: "159819"
    name: "人工智能ETF"
    shares: 2600
    cost_price: 0
    enabled: true
    remark: "手动填写成本价"
""",
    )

    holdings = load_holdings(config_path)

    assert holdings[0].cost_price == 0
    assert "请补充成本价" in caplog.text


def test_load_empty_holdings_returns_empty_list(tmp_path: Path):
    config_path = write_yaml(tmp_path / "holdings.yaml", "holdings: []\n")

    assert load_holdings(config_path) == []
