from pathlib import Path
import logging

import yaml

from .models import Holding


REQUIRED_COLUMNS = ["code", "name", "shares", "cost_price", "enabled", "remark"]


def load_holdings(path: Path | str) -> list[Holding]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"持仓文件不存在: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    raw_holdings = data.get("holdings")
    if raw_holdings is None:
        raise ValueError("holdings.yaml 缺少字段: holdings")
    if not isinstance(raw_holdings, list):
        raise ValueError("holdings.yaml 中 holdings 必须是列表")

    holdings: list[Holding] = []
    for index, row in enumerate(raw_holdings, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"holdings 第 {index} 项必须是对象")
        missing = [column for column in REQUIRED_COLUMNS if column not in row]
        if missing:
            raise ValueError(f"holdings 第 {index} 项缺少字段: {', '.join(missing)}")

        enabled = _parse_bool(row["enabled"])
        if not enabled:
            continue

        code = normalize_code(row["code"])
        shares = _parse_float(row["shares"], f"holdings 第 {index} 项 shares")
        cost_price = _parse_float(row["cost_price"], f"holdings 第 {index} 项 cost_price")
        if cost_price <= 0:
            logging.warning("%s %s cost_price <= 0，请补充成本价", code, row["name"])

        holdings.append(
            Holding(
                code=code,
                name=str(row["name"]),
                shares=shares,
                cost_price=cost_price,
                enabled=enabled,
                remark="" if row["remark"] is None else str(row["remark"]),
            )
        )
    return holdings


def normalize_code(value: object) -> str:
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if not text.isdigit():
        raise ValueError(f"证券代码必须是数字: {text}")
    return text.zfill(6)


def _parse_float(value: object, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须是数字") from exc
    if parsed < 0:
        raise ValueError(f"{name} 不能为负数")
    return parsed


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"enabled 必须是 true 或 false: {value}")
