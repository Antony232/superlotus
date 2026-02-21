"""
市场分析命令处理器 - 处理 /市场分析 命令
使用Service层简化业务逻辑
"""
import logging
import asyncio
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment

from services.market_report_service import market_report_service

logger = logging.getLogger(__name__)

# 创建市场分析命令处理器
market_analysis = on_command("市场分析", priority=10, block=True)


@market_analysis.handle()
async def handle_market_analysis(bot: Bot, event: Event):
    """处理 /市场分析 命令 - 发送4张市场分析图片"""
    try:
        # 使用Service层获取完整报告（含图片）
        full_report = await market_report_service.get_report_with_images(force_refresh=False)

        if not full_report:
            error_msg = "❌ 暂无市场数据，请稍后再试"
            await bot.send(event, Message(error_msg))
            return

        # 发送图片
        messages = [Message("📊 PRIME市场分析报告")]

        for idx, (title, image_path) in enumerate(full_report['images'], 1):
            msg = Message(f"图片{idx}/4: {title}")
            msg += MessageSegment.image(image_path.read_bytes())
            messages.append(msg)

        for msg in messages:
            await bot.send(event, msg)
            await asyncio.sleep(0.3)  # 避免发送过快

        logger.info("市场分析命令处理成功")

    except Exception as e:
        error_msg = f"❌ 市场分析异常: {str(e)[:80]}"
        logger.error(error_msg, exc_info=True)
        await bot.send(event, Message(error_msg))
