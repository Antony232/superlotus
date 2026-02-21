"""
深层科研(Archimedea)命令处理器
处理/深层科研命令
"""
import logging
from pathlib import Path
from typing import Optional

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment

from managers.archimedea_manager import ArchimedeaManager
from managers.game_status_manager import GameStatusManager

logger = logging.getLogger(__name__)


# 注册命令
archimedea_cmd = on_command("深层科研", priority=10, block=True, aliases={"archimedea", "archi"})


@archimedea_cmd.handle()
async def handle_archimedea(bot: Bot, event: Event):
    """处理深层科研查询命令 - 直接返回文本"""
    try:
        # 获取管理器实例
        archimedea_manager, game_status_manager = _get_archimedea_manager()

        if not archimedea_manager:
            await bot.send(event, Message("无法初始化Archimedea管理器，请联系管理员"))
            return

        # 发送查询中提示
        from config import config
        querying_msg = f"{config.get_random_emoji()} 喵~ 正在查询深层科研数据..."
        await bot.send(event, Message(querying_msg))

        # 获取Archimedea信息
        archimedea_data = await archimedea_manager.get_archimedea_info()

        # 格式化消息
        # 需要重新获取conquests数据用于格式化
        world_state = await game_status_manager.fetch_world_state()
        conquests = world_state.get('Conquests', []) if world_state else []
        message_text = archimedea_manager.format_archimedea_message(archimedea_data, conquests)

        # 直接发送文本
        await bot.send(event, Message(message_text))

    except Exception as e:
        logger.error(f"处理深层科研命令失败: {e}", exc_info=True)
        await bot.send(event, Message(f"查询深层科研信息时出错: {str(e)}"))


def _get_archimedea_manager() -> tuple[Optional[ArchimedeaManager], Optional[GameStatusManager]]:
    """
    获取ArchimedeaManager和GameStatusManager实例

    Returns:
        元组(ArchimedeaManager实例, GameStatusManager实例)，如果初始化失败则返回(None, None)
    """
    try:
        from managers.translation_manager import TranslationManager, GameStatusTranslator

        # 创建实例
        game_status_manager = GameStatusManager()
        translation_manager = TranslationManager()
        game_translator = GameStatusTranslator()

        # 加载翻译
        translation_manager.load_translations()
        game_translator.load_translations()

        # 创建Archimedea管理器
        archimedea_manager = ArchimedeaManager(
            translation_manager=translation_manager,
            game_translator=game_translator,
            world_state_fetcher=game_status_manager.fetch_world_state
        )

        return archimedea_manager, game_status_manager

    except Exception as e:
        logger.error(f"初始化ArchimedeaManager失败: {e}")
        return None, None
