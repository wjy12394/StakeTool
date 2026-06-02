from dataclasses import dataclass, field
import logging
import time

from .models import PortfolioResult


@dataclass(frozen=True)
class Alert:
    kind: str
    title: str
    message: str


@dataclass
class AlertState:
    last_sent_at: dict[str, float] = field(default_factory=dict)
    active_keys: set[str] = field(default_factory=set)


def evaluate_alerts(
    result: PortfolioResult,
    total_loss_threshold: float,
    single_loss_threshold: float,
    cooldown_sec: int,
    notify_on_recover: bool,
    state: AlertState,
    now: float | None = None,
    total_profit_threshold: float | None = None,
    single_profit_threshold: float | None = None,
) -> list[Alert]:
    current_time = time.time() if now is None else now
    alerts: list[Alert] = []

    total_key = "total_loss"
    if result.total_pnl <= total_loss_threshold:
        message = (
            f"组合当前浮亏：{result.total_pnl:.2f} 元\n"
            f"组合收益率：{result.total_pnl_ratio:.2f}%"
        )
        alerts.extend(_maybe_alert(state, total_key, current_time, cooldown_sec, "ETF持仓亏损提醒", message))
    elif total_key in state.active_keys:
        state.active_keys.remove(total_key)
        if notify_on_recover:
            alerts.extend(
                _maybe_alert(
                    state,
                    f"{total_key}:recover",
                    current_time,
                    cooldown_sec,
                    "ETF持仓恢复提醒",
                    f"组合浮亏已恢复到阈值以上：{result.total_pnl:.2f} 元",
                    mark_active=False,
                )
            )

    if total_profit_threshold is not None:
        total_profit_key = "total_profit"
        if result.total_pnl >= total_profit_threshold:
            message = (
                f"组合当前浮盈：{result.total_pnl:.2f} 元\n"
                f"组合收益率：{result.total_pnl_ratio:.2f}%"
            )
            alerts.extend(
                _maybe_alert(state, total_profit_key, current_time, cooldown_sec, "ETF持仓盈利提醒", message)
            )
        elif total_profit_key in state.active_keys:
            state.active_keys.remove(total_profit_key)

    for item in result.items:
        key = f"single_loss:{item.code}"
        if item.pnl <= single_loss_threshold:
            message = (
                f"{item.code} {item.name} 当前浮亏：{item.pnl:.2f} 元\n"
                f"当前收益率：{item.pnl_ratio:.2f}%"
            )
            alerts.extend(_maybe_alert(state, key, current_time, cooldown_sec, "单只ETF亏损提醒", message))
        elif key in state.active_keys:
            state.active_keys.remove(key)
            if notify_on_recover:
                alerts.extend(
                    _maybe_alert(
                        state,
                        f"{key}:recover",
                        current_time,
                        cooldown_sec,
                        "单只ETF恢复提醒",
                        f"{item.code} {item.name} 浮亏已恢复到阈值以上：{item.pnl:.2f} 元",
                        mark_active=False,
                    )
                )

        if single_profit_threshold is not None:
            profit_key = f"single_profit:{item.code}"
            if item.pnl >= single_profit_threshold:
                message = (
                    f"{item.code} {item.name} 当前浮盈：{item.pnl:.2f} 元\n"
                    f"当前收益率：{item.pnl_ratio:.2f}%"
                )
                alerts.extend(_maybe_alert(state, profit_key, current_time, cooldown_sec, "单只ETF盈利提醒", message))
            elif profit_key in state.active_keys:
                state.active_keys.remove(profit_key)

    return alerts


def send_alert(alert: Alert, logger: logging.Logger | None = None) -> None:
    log = logger or logging.getLogger(__name__)
    try:
        from win11toast import toast

        toast(alert.title, alert.message)
    except Exception as exc:
        log.warning("Windows 通知失败，改为命令行输出: %s", exc)
        print(f"\n{alert.title}\n{alert.message}\n")


def _maybe_alert(
    state: AlertState,
    key: str,
    now: float,
    cooldown_sec: int,
    title: str,
    message: str,
    mark_active: bool = True,
) -> list[Alert]:
    last_sent = state.last_sent_at.get(key, 0)
    if now - last_sent < cooldown_sec:
        if mark_active:
            state.active_keys.add(key.removesuffix(":recover"))
        return []

    state.last_sent_at[key] = now
    if mark_active:
        state.active_keys.add(key.removesuffix(":recover"))
    return [Alert(kind=key.split(":")[0], title=title, message=message)]
