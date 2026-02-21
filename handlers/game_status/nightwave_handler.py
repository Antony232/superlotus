"""
午夜电波处理器 - 处理 /电波 命令
"""

import logging
from typing import Union
from managers.nightwave_manager import NightwaveManager, NightwaveData
from utils.message_builder import MessageBuilder
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


class NightwaveHandler:
    """午夜电波命令处理器"""

    def __init__(self):
        self.manager = NightwaveManager()
        self.message_builder = MessageBuilder()

    async def handle_nightwave_command(self, event: Union[MessageEvent, None] = None) -> str:
        """
        处理午夜电波命令

        Args:
            event: 消息事件（可选）

        Returns:
            格式化后的午夜电波信息（纯文本）
        """
        try:
            # 获取午夜电波数据（异步）
            nightwave_data = await self.manager.fetch_nightwave_info()

            if not nightwave_data:
                error_msg = "无法获取午夜电波数据"
                logger.error(error_msg)
                return error_msg

            # 直接返回格式化文本
            return self.manager.format_nightwave_info(nightwave_data)

        except Exception as e:
            logger.error(f"处理午夜电波命令失败: {e}", exc_info=True)
            return f"处理午夜电波命令时发生错误: {str(e)}"

    async def get_nightwave_text(self) -> str:
        """
        获取午夜电波文本（用于本地测试）

        Returns:
            格式化的午夜电波文本
        """
        nightwave_data = await self.manager.fetch_nightwave_info()

        if not nightwave_data:
            return "无法获取午夜电波数据"

        return self.manager.format_nightwave_info(nightwave_data)


# 创建处理器实例
nightwave_handler = NightwaveHandler()

# 注册NoneBot命令（如果可用）
if NONE_BOT_AVAILABLE:
    nightwave_cmd = on_command("电波", aliases={"午夜电波", "nightwave"}, priority=15, block=True)

    @nightwave_cmd.handle()
    async def handle_nightwave(bot: Bot, event: MessageEvent):
        """处理午夜电波命令 - 返回图片"""
        try:
            result = await nightwave_handler.handle_nightwave_command(event)
            
            # 转换为图片（使用更宽的宽度以显示完整内容）
            try:
                image_bytes = text_to_image.convert_simple(result, title="午夜电波", max_width=650)
                await nightwave_cmd.finish(MessageSegment.image(image_bytes))
            except FinishedException:
                raise  # 正常结束，继续抛出
            except Exception as e:
                logger.error(f"转换图片失败: {e}")
                # 图片转换失败，发送纯文本
                await nightwave_cmd.finish(result)
        except FinishedException:
            raise  # 正常结束，继续抛出
        except Exception as e:
            logger.error(f"处理午夜电波命令异常: {e}", exc_info=True)
            await nightwave_cmd.finish(f"查询午夜电波失败: {str(e)}")
else:
    logger.info("NoneBot 不可用，跳过命令注册")
