# handlers/wm_handler.py - 价格查询处理器（使用公共查询工具）
import nonebot
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot import on_message
from nonebot.rule import Rule
from nonebot.matcher import Matcher
import logging
from utils.command_checker import is_wm_command, extract_wm_query
from core.formatters.response_formatter import ResponseFormatter
from managers.translation_manager import translation_manager
from utils.price_query_utils import query_item_price  # 导入公共价格查询工具
from config import config

logger = logging.getLogger(__name__)

# 创建WM处理器
wm_handler = on_message(rule=Rule(is_wm_command), priority=10, block=True)


@wm_handler.handle()
async def handle_wm_message(bot: Bot, event: Event, matcher: Matcher):
    """处理/wm消息（使用公共查询逻辑，优化代码结构）"""
    msg = event.get_plaintext().strip()
    original_query = extract_wm_query(msg)

    # 空查询显示帮助
    if not original_query:
        short_help = ResponseFormatter.format_short_help()
        await bot.send(event, Message(short_help))
        return

    try:
        # 使用公共工具查询价格
        result = await query_item_price(original_query)

        if not result.english_slug:
            error_response = ResponseFormatter.format_error_response("无法识别物品名称")
            await bot.send(event, Message(error_response))
            return

        # 获取显示名称（翻译文件第一个中文名称）
        chinese_names = translation_manager.get_chinese_names(result.english_slug)
        display_name = chinese_names[0] if chinese_names else original_query
        logger.info(f"翻译结果: '{original_query}' -> '{result.english_slug}' | 显示名称: {display_name}")

        # 构建响应
        if result.is_arcane:
            if not result.orders and not result.max_rank_orders:
                error_response = ResponseFormatter.format_error_response(f"没有找到'{display_name}'的价格信息")
                await bot.send(event, Message(error_response))
                return

            response = ResponseFormatter.format_price_response(
                display_name, result.english_slug, result.orders or [],
                is_translated=True, is_arcane=True,
                rank0_orders=result.orders, max_rank_orders=result.max_rank_orders,
                max_rank=result.max_rank
            )
        else:
            if not result.orders:
                error_msg = f"物品 '{display_name}' 不存在或无卖出订单"
                error_response = ResponseFormatter.format_error_response(error_msg)
                await bot.send(event, Message(error_response))
                return

            response = ResponseFormatter.format_price_response(
                display_name, result.english_slug, result.orders,
                is_translated=True
            )

        await bot.send(event, Message(response))

    except Exception as e:
        error_msg = str(e)[:80]
        logger.error(f"查询异常: {error_msg}", exc_info=True)
        error_response = ResponseFormatter.format_error_response(f"查询'{display_name}'异常: {error_msg}")
        await bot.send(event, Message(error_response))