"""
时间工具模块 - 存放时间格式化函数
避免在多个管理器中重复定义
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


def format_timestamp(timestamp_ms: int, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    格式化毫秒时间戳为可读字符串

    Args:
        timestamp_ms: 毫秒时间戳
        fmt: 输出格式，默认 '%Y-%m-%d %H:%M:%S'

    Returns:
        格式化后的时间字符串
    """
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        return dt.strftime(fmt)
    except Exception:
        return '时间解析失败'


def format_timestamp_to_date(timestamp_ms: int) -> str:
    """
    格式化毫秒时间戳为日期字符串（中文格式）

    Args:
        timestamp_ms: 毫秒时间戳

    Returns:
        格式化后的日期字符串，如 "2月16日"
    """
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        date_str = dt.strftime('%m月%d日')
        # 移除前导零
        return date_str.lstrip('0').replace('月0', '月')
    except Exception:
        return '未知日期'


def calculate_date_from_day(base_timestamp_ms: int, day: int, base_day: int = 101) -> str:
    """
    根据基础时间戳和天数计算具体日期

    Args:
        base_timestamp_ms: 基准时间戳（毫秒）
        day: 目标天数
        base_day: 基准天数，默认 101

    Returns:
        计算出的日期字符串，如 "2月16日"
    """
    try:
        base_dt = datetime.fromtimestamp(base_timestamp_ms / 1000)
        day_offset = day - base_day
        target_dt = base_dt + timedelta(days=day_offset)
        date_str = target_dt.strftime('%m月%d日')
        return date_str.lstrip('0').replace('月0', '月')
    except Exception:
        return f"第{day}天"


def format_remaining_time(expiry_timestamp_ms: int) -> str:
    """
    格式化剩余时间

    Args:
        expiry_timestamp_ms: 到期时间戳（毫秒）

    Returns:
        剩余时间字符串，如 "6天9小时"
    """
    try:
        now = datetime.now().timestamp() * 1000
        time_left = expiry_timestamp_ms - now

        if time_left <= 0:
            return "已结束"

        days_left = int(time_left / (1000 * 60 * 60 * 24))
        hours_left = int((time_left % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
        minutes_left = int((time_left % (1000 * 60 * 60)) / (1000 * 60))

        if days_left > 0:
            return f"{days_left}天{hours_left}小时"
        elif hours_left > 0:
            return f"{hours_left}小时{minutes_left}分钟"
        else:
            return f"{minutes_left}分钟"
    except Exception:
        return "未知"


def format_countdown(expiry_timestamp_ms: int) -> str:
    """
    格式化倒计时

    Args:
        expiry_timestamp_ms: 到期时间戳（毫秒）

    Returns:
        倒计时字符串，如 "6天9小时后更新"
    """
    remaining = format_remaining_time(expiry_timestamp_ms)
    if remaining == "已结束" or remaining == "未知":
        return remaining
    return f"{remaining}后更新"
