from pathlib import Path
import logging


def setup_logger(level: str, log_file: Path | str, quiet_console: bool = False) -> logging.Logger:
    logger = logging.getLogger("portfolio_alert")
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.CRITICAL if quiet_console else log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_path = Path(log_file)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
