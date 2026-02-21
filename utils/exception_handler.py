# utils/exception_handler.py - 异常处理装饰器
import logging
from functools import wraps
from typing import Callable, Optional
from core.formatters.response_formatter import ResponseFormatter

logger = logging.getLogger(__name__)


def handle_exception(default_msg: str = "操作失败"):
    """
    统一异常处理装饰器
    自动捕获异常并返回格式化的错误消息
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{func.__name__} 异常: {e}", exc_info=True)
                # 假设第一个参数是bot，第二个是event
                bot = args[0] if args else None
                event = args[1] if len(args) > 1 else None
                if bot and event:
                    from nonebot.adapters.onebot.v11 import Message
                    await bot.send(event, Message(ResponseFormatter.format_error_response(default_msg)))
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{func.__name__} 异常: {e}", exc_info=True)
                raise  # 同步函数重新抛出异常
        
        # 根据函数是否是协程来选择包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
