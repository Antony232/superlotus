"""
时间工具模块 - 统一时间处理函数
消除各管理器中的重复时间处理代码
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Union

from core.constants import TimeZones


def parse_mongodb_timestamp(ts: Union[int, float, str, dict, None]) -> Optional[datetime]:
    """
    解析 MongoDB 时间戳（支持多种格式）
    
    Args:
        ts: 时间戳，支持以下格式：
            - int/float: 毫秒时间戳
            - str: 毫秒时间戳字符串或 ISO 格式字符串
            - dict: MongoDB 格式 {"$date": {"$numberLong": "1234567890"}}
            
    Returns:
        UTC datetime 对象，解析失败返回 None
    """
    if ts is None:
        return None
    
    try:
        # MongoDB 格式: {"$date": {"$numberLong": "1234567890"}}
        if isinstance(ts, dict):
            if '$date' in ts:
                date_val = ts['$date']
                if isinstance(date_val, dict) and '$numberLong' in date_val:
                    ts = int(date_val['$numberLong'])
                else:
                    ts = date_val
            else:
                return None
        
        # 字符串格式
        if isinstance(ts, str):
            # ISO 格式
            if 'T' in ts:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            # 毫秒时间戳字符串
            ts = int(ts)
        
        # 数字格式（毫秒时间戳）
        if isinstance(ts, (int, float)):
            return datetime.utcfromtimestamp(ts / 1000)
            
    except (ValueError, TypeError, OSError) as e:
        pass
    
    return None


def to_beijing_time(dt: datetime) -> datetime:
    """
    将 datetime 转换为北京时间
    
    Args:
        dt: 任意时区的 datetime 对象
        
    Returns:
        北京时间 datetime 对象（无时区信息）
    """
    beijing_tz = timezone(timedelta(hours=TimeZones.BEIJING_OFFSET))
    
    if dt.tzinfo is None:
        # 假设是 UTC 时间
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(beijing_tz).replace(tzinfo=None)


def format_timestamp(timestamp_ms: int, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    格式化毫秒时间戳为可读字符串（北京时间）

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


def calculate_time_left(time_input: Union[int, float, str, dict, None]) -> str:
    """
    通用时间计算函数 - 支持毫秒时间戳和ISO字符串
    
    兼容 game_status_manager.calculate_time_left 的功能

    Args:
        time_input: 到期时间（支持多种格式）

    Returns:
        剩余时间字符串，如 "2小时30分"
    """
    if not time_input:
        return "未知"
    
    expiry_utc = parse_mongodb_timestamp(time_input)
    if expiry_utc is None:
        return "未知"
    
    # 计算剩余时间
    now_utc = datetime.utcnow() if expiry_utc.tzinfo is None else datetime.now(timezone.utc)
    
    if expiry_utc.tzinfo is None:
        time_left = expiry_utc - now_utc.replace(tzinfo=None)
    else:
        time_left = expiry_utc - now_utc
    
    total_seconds = int(time_left.total_seconds())
    
    if total_seconds <= 0:
        return "已过期"
    
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours}小时{minutes}分"
    else:
        return f"{minutes}分{seconds}秒"


def convert_to_beijing(time_input: Union[int, float, str, dict, None]) -> str:
    """
    将时间戳或ISO字符串转换为北京时间字符串
    
    兼容 game_status_manager.convert_to_beijing 的功能

    Args:
        time_input: 时间输入（支持多种格式）

    Returns:
        北京时间字符串，格式 "YYYY-MM-DD HH:MM:SS"
    """
    if not time_input:
        return "未知时间"
    
    dt_utc = parse_mongodb_timestamp(time_input)
    if dt_utc is None:
        return "时间解析错误"
    
    dt_beijing = to_beijing_time(dt_utc)
    return dt_beijing.strftime('%Y-%m-%d %H:%M:%S')


def get_current_beijing_time() -> str:
    """
    获取当前北京时间字符串

    Returns:
        北京时间字符串，格式 "YYYY-MM-DD HH:MM:SS"
    """
    return (datetime.utcnow() + timedelta(hours=TimeZones.BEIJING_OFFSET)).strftime('%Y-%m-%d %H:%M:%S')


def get_current_beijing_hour_minute() -> str:
    """
    获取当前北京时间（仅时分）

    Returns:
        北京时间字符串，格式 "HH:MM"
    """
    return (datetime.utcnow() + timedelta(hours=TimeZones.BEIJING_OFFSET)).strftime('%H:%M')
