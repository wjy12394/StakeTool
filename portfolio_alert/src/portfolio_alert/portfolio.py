from .models import Holding, PortfolioResult, PositionResult


def calculate_portfolio(holdings: list[Holding], latest_prices: dict[str, float]) -> PortfolioResult:
    items: list[PositionResult] = []

    for holding in holdings:
        latest_price = latest_prices.get(holding.code)
        cost_amount = holding.shares * holding.cost_price
        market_value = holding.shares * latest_price if latest_price is not None else 0.0
        pnl = market_value - cost_amount
        pnl_ratio = (pnl / cost_amount * 100) if cost_amount > 0 else 0.0
        items.append(
            PositionResult(
                code=holding.code,
                name=holding.name,
                shares=holding.shares,
                cost_price=holding.cost_price,
                latest_price=latest_price,
                cost_amount=cost_amount,
                market_value=market_value,
                pnl=pnl,
                pnl_ratio=pnl_ratio,
            )
        )

    total_cost = sum(item.cost_amount for item in items)
    total_market_value = sum(item.market_value for item in items)
    total_pnl = total_market_value - total_cost
    total_pnl_ratio = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0
    return PortfolioResult(
        items=items,
        total_cost=total_cost,
        total_market_value=total_market_value,
        total_pnl=total_pnl,
        total_pnl_ratio=total_pnl_ratio,
    )


def format_portfolio(result: PortfolioResult) -> str:
    lines = [
        (
            f"当前组合市值：{result.total_market_value:.2f} 元，"
            f"总盈亏：{result.total_pnl:.2f} 元，收益率：{result.total_pnl_ratio:.2f}%"
        ),
        "",
        f"{'代码':<8}{'名称':<14}{'最新价':>10}{'市值':>12}{'盈亏':>12}{'收益率':>10}",
    ]
    for item in result.items:
        price = f"{item.latest_price:.3f}" if item.latest_price is not None else "缺失"
        lines.append(
            f"{item.code:<8}{item.name:<14}{price:>10}"
            f"{item.market_value:>12.2f}{item.pnl:>12.2f}{item.pnl_ratio:>9.2f}%"
        )
    return "\n".join(lines)
