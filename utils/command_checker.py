# utils/command_checker.py - 命令检查器
import re
from typing import List
from nonebot.adapters.onebot.v11 import Event


def is_wm_command(event: Event) -> bool:
    """判断是否为/wm命令"""
    msg = event.get_plaintext().strip()
    prefixes = ['/wm', '！wm', '!wm']

    for prefix in prefixes:
        if msg.startswith(prefix + ' ') or msg == prefix:
            return True
    return False


def is_help_command(event: Event) -> bool:
    """判断是否为/help或/帮助命令"""
    msg = event.get_plaintext().strip().lower()

    # 支持的帮助命令格式
    help_commands = [
        '/help', '！help', '!help',
        '/帮助', '！帮助', '!帮助',
        '/hlep', '！hlep', '!hlep'  # 兼容拼写错误
    ]

    # 检查是否是完全匹配的帮助命令
    for cmd in help_commands:
        if msg == cmd:
            return True

    # 检查是否以help开头（如/help等）
    help_patterns = [r'^[/！!]help', r'^[/！!]帮助', r'^[/！!]hlep']
    for pattern in help_patterns:
        if re.match(pattern, msg):
            return True

    return False


def extract_wm_query(message: str) -> str:
    """从/wm命令中提取查询内容"""
    msg = message.strip()

    # 提取命令和查询内容
    if msg.startswith('/wm'):
        return msg[3:].strip()
    elif msg.startswith('！wm') or msg.startswith('!wm'):
        return msg[3:].strip()

    return msg[2:].strip() if len(msg) > 2 else ""