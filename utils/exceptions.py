"""
自定义异常类 - 统一异常处理
"""


class BotBaseException(Exception):
    """机器人基础异常"""
    pass


class APIError(BotBaseException):
    """API 调用异常"""
    def __init__(self, message: str, status_code: int = None, url: str = None):
        self.status_code = status_code
        self.url = url
        super().__init__(message)


class TranslationError(BotBaseException):
    """翻译异常"""
    def __init__(self, message: str, item_id: str = None):
        self.item_id = item_id
        super().__init__(message)


class CacheError(BotBaseException):
    """缓存异常"""
    pass


class ConfigError(BotBaseException):
    """配置异常"""
    pass


class ValidationError(BotBaseException):
    """输入验证异常"""
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message)


class RateLimitError(APIError):
    """API 限流异常"""
    def __init__(self, message: str = "API 请求频率超限", retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(message, status_code=429)
