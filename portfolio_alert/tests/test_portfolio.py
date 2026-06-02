import pytest

from portfolio_alert.models import Holding
from portfolio_alert.notifier import AlertState, evaluate_alerts
from portfolio_alert.portfolio import calculate_portfolio


def test_calculate_portfolio_pnl_summary():
    holdings = [
        Holding("510300", "沪深300ETF", 100, 4.0, True, ""),
        Holding("562500", "机器人ETF", 200, 1.5, True, ""),
    ]
    prices = {"510300": 4.5, "562500": 1.0}

    result = calculate_portfolio(holdings, prices)

    assert result.total_cost == 700
    assert result.total_market_value == 650
    assert result.total_pnl == -50
    assert result.total_pnl_ratio == pytest.approx(-7.142857)
    assert result.items[0].pnl == 50
    assert result.items[1].pnl == -100


def test_calculate_portfolio_handles_missing_price_and_zero_cost():
    holdings = [
        Holding("159819", "人工智能ETF", 2600, 0, True, ""),
        Holding("510300", "沪深300ETF", 100, 4.0, True, ""),
    ]

    result = calculate_portfolio(holdings, {"159819": 1.9})

    assert result.items[0].cost_amount == 0
    assert result.items[0].pnl_ratio == 0
    assert result.items[1].latest_price is None
    assert result.items[1].market_value == 0


def test_evaluate_single_holding_loss_threshold():
    result = calculate_portfolio(
        [Holding("562500", "机器人ETF", 200, 1.5, True, "")],
        {"562500": 1.0},
    )
    state = AlertState()

    alerts = evaluate_alerts(
        result,
        total_loss_threshold=-500,
        single_loss_threshold=-80,
        cooldown_sec=300,
        notify_on_recover=True,
        state=state,
        now=1000,
    )

    assert len(alerts) == 1
    assert alerts[0].kind == "single_loss"
    assert "562500" in alerts[0].message


def test_evaluate_total_loss_threshold():
    result = calculate_portfolio(
        [Holding("510300", "沪深300ETF", 100, 4.0, True, "")],
        {"510300": 2.0},
    )
    state = AlertState()

    alerts = evaluate_alerts(
        result,
        total_loss_threshold=-150,
        single_loss_threshold=-300,
        cooldown_sec=300,
        notify_on_recover=True,
        state=state,
        now=1000,
    )

    assert len(alerts) == 1
    assert alerts[0].kind == "total_loss"
    assert "组合当前浮亏" in alerts[0].message


def test_evaluate_alert_cooldown_blocks_repeated_alert():
    result = calculate_portfolio(
        [Holding("510300", "沪深300ETF", 100, 4.0, True, "")],
        {"510300": 2.0},
    )
    state = AlertState()

    first = evaluate_alerts(result, -150, -300, 300, True, state, now=1000)
    second = evaluate_alerts(result, -150, -300, 300, True, state, now=1100)

    assert len(first) == 1
    assert second == []


def test_evaluate_total_profit_threshold():
    result = calculate_portfolio(
        [Holding("510300", "沪深300ETF", 100, 4.0, True, "")],
        {"510300": 6.0},
    )
    state = AlertState()

    alerts = evaluate_alerts(
        result,
        total_loss_threshold=-500,
        single_loss_threshold=-300,
        cooldown_sec=300,
        notify_on_recover=False,
        state=state,
        now=1000,
        total_profit_threshold=150,
        single_profit_threshold=300,
    )

    assert len(alerts) == 1
    assert alerts[0].kind == "total_profit"
    assert "组合当前浮盈" in alerts[0].message


def test_evaluate_single_profit_threshold():
    result = calculate_portfolio(
        [Holding("562500", "机器人ETF", 200, 1.0, True, "")],
        {"562500": 2.0},
    )
    state = AlertState()

    alerts = evaluate_alerts(
        result,
        total_loss_threshold=-500,
        single_loss_threshold=-300,
        cooldown_sec=300,
        notify_on_recover=False,
        state=state,
        now=1000,
        total_profit_threshold=500,
        single_profit_threshold=150,
    )

    assert len(alerts) == 1
    assert alerts[0].kind == "single_profit"
    assert "当前浮盈" in alerts[0].message
