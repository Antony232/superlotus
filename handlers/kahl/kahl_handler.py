"""
时光科研(Kahl)命令处理器
处理/时光科研命令
"""
import logging
from pathlib import Path
from typing import Optional

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment

from managers.kahl_manager import get_kahl_manager

logger = logging.getLogger(__name__)


# 注册命令
kahl_cmd = on_command("时光科研", priority=10, block=True, aliases={"kahl", "时光"})


@kahl_cmd.handle()
async def handle_kahl(bot: Bot, event: Event):
    """处理时光科研查询命令 - 直接返回文本"""
    try:
        # 获取管理器实例
        kahl_manager = get_kahl_manager()

        if not kahl_manager:
            await bot.send(event, Message("无法初始化时光科研管理器，请联系管理员"))
            return

        # 发送查询中提示
        from config import config
        querying_msg = f"{config.get_random_emoji()} 喵~ 正在查询时光科研数据..."
        await bot.send(event, Message(querying_msg))

        # 获取Kahl信息
        kahl_data = await kahl_manager.get_kahl_info()

        # 格式化消息
        message_text = kahl_manager.format_kahl_message(kahl_data)

        # 直接发送文本
        await bot.send(event, Message(message_text))

    except Exception as e:
        logger.error(f"处理时光科研命令失败: {e}", exc_info=True)
        await bot.send(event, Message(f"查询时光科研信息时出错: {str(e)}"))
