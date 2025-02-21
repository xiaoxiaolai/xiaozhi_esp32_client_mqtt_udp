import logging
import sys
import os


def setup_logging(logger: dict):
    """配置全局日志"""
    os.makedirs(logger['log_dir'], exist_ok=True)

    logging.basicConfig(
        level=logger['level'],
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(logger['log_dir'], "server.log"), encoding='utf-8')
        ],
        force=True
    )
    return logging.getLogger(__name__)
