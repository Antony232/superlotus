"""
日历处理器 - 处理 /日历 命令
"""

import logging
from typing import Union
from managers.calendar_manager import CalendarManager, CalendarSeasonData
from utils.text_to_image import text_to_image

logger = logging.getLogger(__name__)

# 尝试导入NoneBot相关模块，用于本地测试兼容性
try:
    from nonebot import on_command
    from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
    from nonebot.adapters.onebot.v11 import Bot
    from nonebot.exception import FinishedException

    NONE_BOT_AVAILABLE = True
except ImportError:
    NONE_BOT_AVAILABLE = False
    # 创建占位符类用于本地测试
    class MessageEvent:
        def __init__(self, user_id: int = 123456):
            self.user_id = user_id

    class MessageSegment:
        @staticmethod
        def text(content: str):
            return f"[TEXT]{content}"

        @staticmethod
        def image(file_path: str):
            return f"[IMAGE]{file_path}"

    class Bot:
        pass

    def on_command(cmd: str, **kwargs):
        def decorator(func):
            return func
        return decorator


class CalendarHandler:
    """日历命令处理器"""

    def __init__(self):
        self.manager = CalendarManager()

    async def handle_calendar_command(self, event: Union[MessageEvent, None] = None) -> str:
        """
        处理日历命令

        Args:
            event: 消息事件（可选）

        Returns:
            格式化后的日历信息（纯文本）
        """
        try:
            # 获取日历数据（异步）
            calendar_data = await self.manager.fetch_calendar_info()

            if not calendar_data:
                error_msg = "无法获取日历数据"
                logger.error(error_msg)
                return error_msg

            # 直接返回格式化文本
            return self.manager.format_calendar_info(calendar_data)

        except Exception as e:
            logger.error(f"处理日历命令失败: {e}", exc_info=True)
            return f"处理日历命令时发生错误: {str(e)}"

    async def get_calendar_text(self) -> str:
        """
        获取日历文本（用于本地测试）

        Returns:
            格式化的日历文本
        """
        calendar_data = await self.manager.fetch_calendar_info()

        if not calendar_data:
            return "无法获取日历数据"

        return self.manager.format_calendar_info(calendar_data)


# 创建处理器实例
calendar_handler = CalendarHandler()

# 注册NoneBot命令（如果可用）
if NONE_BOT_AVAILABLE:
    calendar_cmd = on_command("日历", aliases={"calendar"}, priority=15, block=True)

    @calendar_cmd.handle()
    async def handle_calendar(bot: Bot, event: MessageEvent):
        """处理日历命令 - 返回图片"""
        try:
            calendar_data = await calendar_handler.manager.fetch_calendar_info()
            
            if not calendar_data:
                await calendar_cmd.finish("无法获取日历数据")
                return
            
            # 获取结构化数据并转换为图片
            try:
                structured_content = calendar_handler.manager.get_calendar_structured(calendar_data)
                image_bytes = text_to_image.convert_structured(structured_content)
                await calendar_cmd.finish(MessageSegment.image(image_bytes))
            except FinishedException:
                raise  # 正常结束，继续抛出
            except Exception as e:
                logger.error(f"转换图片失败: {e}")
                # 图片转换失败，发送纯文本
                result = calendar_handler.manager.format_calendar_info(calendar_data)
                await calendar_cmd.finish(result)
        except FinishedException:
            raise  # 正常结束，继续抛出
        except Exception as e:
            logger.error(f"处理日历命令异常: {e}", exc_info=True)
            await calendar_cmd.finish(f"查询日历失败: {str(e)}")
else:
    logger.info("NoneBot 不可用，跳过命令注册")
