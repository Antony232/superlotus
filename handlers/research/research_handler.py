"""
科研命令处理器
统一处理/科研、/深层科研、/时光科研命令
"""
import logging
from typing import Optional

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment

from managers.archimedea_manager import ArchimedeaManager
from managers.temporal_archimedea_manager import get_temporal_archimedea_manager
from managers.game_status_manager import GameStatusManager

logger = logging.getLogger(__name__)


# 注册命令
research_cmd = on_command("科研", priority=10, block=True, aliases={"research"})


@research_cmd.handle()
async def handle_research(bot: Bot, event: Event):
    """处理科研查询命令 - 同时显示深层科研和时光科研"""
    try:
        # 获取管理器实例
        archimedea_manager, game_status_manager = _get_archimedea_manager()
        ta_manager = get_temporal_archimedea_manager()

        if not archimedea_manager or not ta_manager:
            await bot.send(event, Message("无法初始化科研管理器，请联系管理员"))
            return

        # 发送查询中提示
        from config import config
        querying_msg = f"{config.get_random_emoji()} 喵~ 正在查询科研数据..."
        await bot.send(event, Message(Message(querying_msg)))

        # 获取Archimedea信息
        archimedea_data = await archimedea_manager.get_archimedea_info()

        # 获取时光科研信息
        ta_data = await ta_manager.get_temporal_archimedea_info()

        # 需要重新获取conquests数据用于格式化
        world_state = await game_status_manager.fetch_world_state()
        conquests = world_state.get('Conquests', []) if world_state else []

        # 生成结构化数据
        content = []

        # T1: 大标题（居中）
        content.append({"type": "T1", "text": "科研任务查询", "align": "center"})

        # 深层科研结构化数据
        archimedea_structured = archimedea_manager.get_archimedea_structured(archimedea_data, conquests)
        content.extend(archimedea_structured)

        # 时光科研结构化数据
        ta_structured = ta_manager.get_temporal_archimedea_structured(ta_data)
        content.extend(ta_structured)

        # 转换为图片并发送
        from utils.text_to_image import text_to_image
        try:
            image_bytes = text_to_image.convert_structured(content)
            await bot.send(event, MessageSegment.image(image_bytes))
        except Exception as e:
            logger.error(f"转换为图片失败: {e}")
            # 如果图片转换失败，发送原始文本
            archimedea_text = archimedea_manager.format_archimedea_message(archimedea_data, conquests)
            ta_text = ta_manager.format_temporal_archimedea_message(ta_data)
            combined_text = f"{archimedea_text}\n\n{ta_text}"
            await bot.send(event, Message(combined_text))

    except Exception as e:
        logger.error(f"处理科研命令失败: {e}", exc_info=True)
        await bot.send(event, Message(f"查询科研信息时出错: {str(e)}"))


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
