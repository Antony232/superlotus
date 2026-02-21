"""
时光科研(Temporal Archimedea)命令处理器
处理/时光科研命令
"""
import logging
from typing import Optional

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message

from managers.temporal_archimedea_manager import get_temporal_archimedea_manager

logger = logging.getLogger(__name__)


# 注册命令
ta_cmd = on_command("时光科研", priority=10, block=True, aliases={"temporal", "时光"})


@ta_cmd.handle()
async def handle_ta(bot: Bot, event: Event):
    """处理时光科研查询命令 - 直接返回文本"""
    try:
        # 获取管理器实例
        ta_manager = get_temporal_archimedea_manager()

        if not ta_manager:
            await bot.send(event, Message("无法初始化时光科研管理器，请联系管理员"))
            return

        # 发送查询中提示
        from config import config
        querying_msg = f"{config.get_random_emoji()} 喵~ 正在查询时光科研数据..."
        await bot.send(event, Message(Message(querying_msg)))

        # 获取时光科研信息
        ta_data = await ta_manager.get_temporal_archimedea_info()

        # 格式化消息
        message_text = ta_manager.format_temporal_archimedea_message(ta_data)

        # 直接发送文本
        await bot.send(event, Message(message_text))

    except Exception as e:
        logger.error(f"处理时光科研命令失败: {e}", exc_info=True)
        await bot.send(event, Message(f"查询时光科研信息时出错: {str(e)}"))
