# handlers/bounty_handler.py - 赏金任务命令处理器
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from managers.bounty_manager import bounty_manager
from core.formatters.response_formatter import ResponseFormatter
from utils.text_to_image import text_to_image
from config import config
import logging

logger = logging.getLogger(__name__)

# 创建赏金任务命令处理器
bounty_handler = on_command("赏金", aliases={"bounty", "bounties", "赏金任务"}, priority=15, block=True)


@bounty_handler.handle()
async def handle_bounty_command(bot: Bot, event: Event):
    """处理赏金任务命令"""
    try:
        # 确保数据已加载
        if not bounty_manager.data_loaded:
            await bot.send(event, Message("⏳ 正在加载数据，请稍候..."))
            bounty_manager.load_data()

        # 发送查询中提示
        querying_msg = f"{config.get_random_emoji()} 喵~ 正在查询赏金任务数据..."
        await bot.send(event, Message(querying_msg))
        logger.info(f"📤 已向用户发送查询中提示")

        # 获取赏金任务
        bounty_data = await bounty_manager.fetch_bounty_cycles()
        if not bounty_data:
            await bot.send(event, Message("❌ 获取赏金任务失败，请稍后再试"))
            return

        # 格式化为文本
        bounty_text = bounty_manager.format_bounty_cycles(bounty_data)

        # 转换为图片
        try:
            image_bytes = text_to_image.convert_simple(bounty_text, title="赏金任务查询")
            await bot.send(event, MessageSegment.image(image_bytes))
        except Exception as e:
            logger.error(f"转换图片失败: {e}")
            # 图片转换失败，发送纯文本
            await bot.send(event, Message(bounty_text))

    except Exception as e:
        logger.error(f"处理赏金命令异常: {e}", exc_info=True)
        await bot.send(event, Message(ResponseFormatter.format_error_response("查询赏金任务失败")))
