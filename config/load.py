import argparse
import os
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
    return resolve_env_vars(read_config(args.config_path))

def resolve_env_vars(value):
    """解析 ${VAR_NAME} 形式的环境变量"""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]  # 去掉 ${}
        return os.environ.get(env_var, "")  # 获取环境变量值，若不存在返回空字符串
    elif isinstance(value, dict):
        return {k: resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [resolve_env_vars(v) for v in value]
    return value
