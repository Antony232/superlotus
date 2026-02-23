# logger_config.py - 统一日志配置（彩色输出版）
import logging
import sys
import os


class Colors:
    """ANSI 颜色代码"""
    RESET = "\033[0m"
    DIM = "\033[2m"
    
    # 日志级别颜色
    DEBUG = "\033[36m"      # 青色
    INFO = "\033[32m"       # 绿色
    WARNING = "\033[33m"    # 黄色
    ERROR = "\033[31m"      # 红色
    CRITICAL = "\033[35m"   # 紫色


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    LEVEL_WIDTH = 8  # 级别字段宽度
    
    def format(self, record):
        # 获取级别颜色
        level_color = getattr(Colors, record.levelname, Colors.RESET)
        
        # 格式化时间
        time_str = self.formatTime(record, "%H:%M:%S")
        
        # 格式化级别（带颜色，固定宽度）
        level_name = record.levelname
        level_str = f"{level_color}{level_name:<{self.LEVEL_WIDTH}}{Colors.RESET}"
        
        # 格式化消息
        message = record.getMessage()
        
        # 组装日志行
        return f"{Colors.DIM}{time_str}{Colors.RESET} │ {level_str} │ {message}"


def setup_logger(level=None):
    """配置全局日志"""
    # 从环境变量获取日志级别
    if level is None:
        level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
    
    # 创建彩色格式化器
    formatter = ColoredFormatter()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    
    # 激进抑制第三方库日志
    third_party_loggers = [
        # nonebot 相关
        "nonebot", "nonebot.adapters", "nonebot.internal", "nonebot.matcher",
        "nonebot.log", "nonebot.plugin", "nonebot.rule",
        # uvicorn
        "uvicorn", "uvicorn.error", "uvicorn.access",
        # 其他
        "websockets", "aiohttp", "asyncio", "multipart",
        "urllib3", "requests", "charset_normalizer", "httpx",
        "httpcore", "anyio", "h11", "ssl", "PIL"
    ]
    
    for name in third_party_loggers:
        logging.getLogger(name).setLevel(logging.CRITICAL)
    
    # 禁用 nonebot 内置日志处理器
    try:
        import nonebot.log
        nonebot.log.logger.handlers.clear()
        nonebot.log.logger.setLevel(logging.CRITICAL)
    except Exception:
        pass
    
    return root_logger


def print_banner(name: str = "超级小莲", version: str = "v8.0"):
    """打印启动横幅"""
    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║     🐱 {name} - Warframe 智能助手                        ║
║     版本: 猫娘@回应版 {version}                               ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)
