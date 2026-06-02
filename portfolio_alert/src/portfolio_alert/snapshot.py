from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import json

from .models import PortfolioResult, PositionResult


SNAPSHOT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
STALE_AFTER_DAYS = 7


@dataclass(frozen=True)
class PortfolioSnapshot:
    saved_at: datetime
    is_trading_time: bool
    result: PortfolioResult


def save_snapshot(
    path: Path | str,
    result: PortfolioResult,
    saved_at: datetime,
    is_trading_time: bool,
) -> None:
    snapshot_path = Path(path)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "time": saved_at.strftime(SNAPSHOT_TIME_FORMAT),
        "is_trading_time": is_trading_time,
        "total_cost": result.total_cost,
        "total_market_value": result.total_market_value,
        "total_pnl": result.total_pnl,
        "total_pnl_ratio": result.total_pnl_ratio,
        "positions": [
            {
                "code": item.code,
                "name": item.name,
                "shares": item.shares,
                "cost_price": item.cost_price,
                "latest_price": item.latest_price,
                "cost_amount": item.cost_amount,
                "market_value": item.market_value,
                "pnl": item.pnl,
                "pnl_ratio": item.pnl_ratio,
            }
            for item in result.items
        ],
    }
    snapshot_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_snapshot(path: Path | str) -> PortfolioSnapshot | None:
    snapshot_path = Path(path)
    if not snapshot_path.exists():
        return None
    try:
        data = json.loads(snapshot_path.read_text(encoding="utf-8"))
        saved_at = datetime.strptime(str(data["time"]), SNAPSHOT_TIME_FORMAT)
        positions = [
            PositionResult(
                code=str(item["code"]),
                name=str(item["name"]),
                shares=float(item["shares"]),
                cost_price=float(item["cost_price"]),
                latest_price=None if item.get("latest_price") is None else float(item["latest_price"]),
                cost_amount=float(item.get("cost_amount", float(item["shares"]) * float(item["cost_price"]))),
                market_value=float(item["market_value"]),
                pnl=float(item["pnl"]),
                pnl_ratio=float(item["pnl_ratio"]),
            )
            for item in data.get("positions", [])
        ]
        result = PortfolioResult(
            items=positions,
            total_cost=float(data["total_cost"]),
            total_market_value=float(data["total_market_value"]),
            total_pnl=float(data["total_pnl"]),
            total_pnl_ratio=float(data["total_pnl_ratio"]),
        )
        return PortfolioSnapshot(
            saved_at=saved_at,
            is_trading_time=bool(data.get("is_trading_time", False)),
            result=result,
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def snapshot_is_stale(saved_at: datetime, now: datetime) -> bool:
    return now - saved_at > timedelta(days=STALE_AFTER_DAYS)
