from pathlib import Path
import logging


def setup_logger(level: str, log_file: Path | str, quiet_console: bool = False) -> logging.Logger:
    logger = logging.getLogger("portfolio_alert")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING if not quiet_console else logging.CRITICAL)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_path = Path(log_file)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
