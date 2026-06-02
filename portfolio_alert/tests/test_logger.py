import logging

from portfolio_alert.logger import setup_logger


def test_setup_logger_uses_debug_level_for_visible_console(tmp_path):
    logger = setup_logger("DEBUG", tmp_path / "app.log", quiet_console=False)
    console_handler = logger.handlers[0]

    assert console_handler.level == logging.DEBUG


def test_setup_logger_suppresses_console_when_quiet(tmp_path):
    logger = setup_logger("DEBUG", tmp_path / "app.log", quiet_console=True)
    console_handler = logger.handlers[0]

    assert console_handler.level == logging.CRITICAL
