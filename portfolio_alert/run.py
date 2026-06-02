from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from portfolio_alert.config_loader import load_config
from portfolio_alert.console_view import print_startup_summary
from portfolio_alert.holdings_loader import load_holdings
from portfolio_alert.logger import setup_logger
from portfolio_alert.scheduler import run_loop


def main() -> None:
    config_path = ROOT / "config.yaml"
    holdings_path = ROOT / "holdings.yaml"
    snapshot_path = ROOT / "data" / "latest_snapshot.json"
    logger = None

    try:
        config = load_config(config_path)
        logger = setup_logger(config.log.level, ROOT / config.log.file, quiet_console=config.console.silent)
        logger.info("程序启动")
        holdings = load_holdings(holdings_path)
        logger.info("读取持仓成功，共 %s 条启用持仓", len(holdings))
        print_startup_summary(config, holdings, logger, snapshot_path=snapshot_path)
        run_loop(config, holdings, logger, snapshot_path=snapshot_path)
    except KeyboardInterrupt:
        if logger:
            logger.info("收到退出信号")
    except Exception as exc:
        if logger:
            logger.error("程序异常退出: %s", exc)
        else:
            print(f"程序启动失败：{exc}", file=sys.stderr)
    finally:
        if logger:
            logger.info("程序退出")


if __name__ == "__main__":
    main()
