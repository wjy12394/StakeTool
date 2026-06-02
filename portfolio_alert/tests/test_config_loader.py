from pathlib import Path

from portfolio_alert.config_loader import load_config


def test_default_config_is_long_term_quiet_monitor(tmp_path: Path):
    config = load_config(tmp_path / "config.yaml")

    assert config.refresh_interval_sec == 900
    assert config.console.silent is True
    assert config.console.show_startup_summary is True
    assert config.console.show_non_trading_message is True
    assert config.console.show_portfolio_each_refresh is False
    assert config.console.startup_quote_timeout_sec == 8
    assert config.alert.total_profit_threshold == 500
    assert config.alert.single_profit_threshold == 300
    assert config.daily_report.enabled is True
    assert config.daily_report.report_time == "15:05"
