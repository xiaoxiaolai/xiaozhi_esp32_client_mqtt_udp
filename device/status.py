from enum import Enum

class Status(Enum):
    Unknown = '未知'
    Starting = '启动中'
    WifiConfiguring = 'wifi配置中'
    Idle = '待命中'
    Connecting = '连接中'
    Listening = '聆听中'
    Speaking = '说话中'
    Upgrading = '升级中'
    FatalError = '出错了'
