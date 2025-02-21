import argparse

import yaml

def read_config(config_path):
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config
  
def load_config():
    """加载配置文件"""
    parser = argparse.ArgumentParser(description="Server configuration")
    parser.add_argument("--config_path", type=str, default="./config/default.yml")
    args = parser.parse_args()
    return read_config(args.config_path)
