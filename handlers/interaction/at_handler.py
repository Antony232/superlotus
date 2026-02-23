# handlers/interaction/at_handler.py
import random
import nonebot
from nonebot.adapters.onebot.v11 import Bot, Event, Message, GroupMessageEvent, PrivateMessageEvent
from nonebot import on_message
from nonebot.rule import Rule, to_me
import logging
from utils.at_checker import is_at_me, extract_message_without_at
from config import config
from managers.translation_manager import translation_manager
from utils.price_query_utils import query_item_price  # 导入公共价格查询工具
from core.formatters.response_formatter import ResponseFormatter
from core.ai_manager import ai_manager

logger = logging.getLogger(__name__)


async def is_at_me_event(event: Event) -> bool:
    """判断是否@了机器人事件"""
    result = is_at_me(event)
    logger.info(f"检查@消息: {event.get_plaintext()[:50]}, is_at_me: {result}")
    return result


# 创建@处理器
at_handler = on_message(
    rule=Rule(is_at_me_event) & to_me(),
    priority=20,
    block=True
)


@at_handler.handle()
async def handle_at_message(bot: Bot, event: Event):
    """处理@机器人的消息
    
    群聊: 只进行闲聊，不查询
    私聊: 先尝试查询，失败再闲聊
    """
    logger.info(f"开始处理@消息: {event.get_plaintext()}")
    try:
        message_without_at = extract_message_without_at(event).strip()
        logger.info(f"去除@后的消息内容: '{message_without_at}'")

        # 纯@消息
        if not message_without_at:
            response = config.get_random_at_response()
            await bot.send(event, Message(f"🐾 {response}"))
            return

        # 群聊：只进行闲聊，不查询
        if isinstance(event, GroupMessageEvent):
            logger.info(f"群聊@消息，进行闲聊: '{message_without_at}'")
            response = await _generate_intelligent_response(message_without_at)
            await bot.send(event, Message(response))
            return

        # 私聊：先尝试价格查询
        result = await query_item_price(message_without_at)
        if result.success and result.english_slug:
            logger.info(f"私聊@价格查询成功: '{message_without_at}' -> '{result.english_slug}'")
            # 获取显示名称
            chinese_names = translation_manager.get_chinese_names(result.english_slug)
            display_name = chinese_names[0] if chinese_names else message_without_at

            # 构建响应
            if result.is_arcane:
                response = ResponseFormatter.format_price_response(
                    display_name, result.english_slug, result.orders or [],
                    is_translated=True, is_arcane=True,
                    rank0_orders=result.orders, max_rank_orders=result.max_rank_orders,
                    max_rank=result.max_rank
                )
            else:
                response = ResponseFormatter.format_price_response(
                    display_name, result.english_slug, result.orders,
                    is_translated=True
                )
            await bot.send(event, Message(response))
        else:
            # 智能闲聊回应
            response = await _generate_intelligent_response(message_without_at)
            await bot.send(event, Message(response))

    except Exception as e:
        logger.error(f"处理@消息异常: {e}", exc_info=True)
        error_response = ResponseFormatter.format_error_response("小莲有点困惑呢，主人能再说清楚一点吗？")
        await bot.send(event, Message(error_response))


async def _generate_intelligent_response(message: str) -> str:
    """生成智能回应（优先使用AI，失败时回退到预设回复）"""
    emoji = config.get_random_emoji()
    message_lower = message.lower()
    
    # 快速响应：功能询问（不需要AI）
    functions = ['你能做什么', '功能', '会什么', 'help', '有什么用', '干嘛的']
    if any(func in message_lower for func in functions):
        content = ResponseFormatter.format_full_help().split('\n')[1:]
        joined_content = '\n'.join(content)
        return f"{emoji} {joined_content}"
    
    # 尝试使用 AI 对话
    if ai_manager.is_enabled():
        try:
            ai_response = await ai_manager.chat(message)
            if ai_response:
                logger.info(f"AI对话成功: {message[:20]}...")
                return ai_response
        except Exception as e:
            logger.warning(f"AI对话失败，回退到预设回复: {e}")
    
    # AI 不可用或失败时的预设回复
    return _get_fallback_response(message_lower, emoji)


def _get_fallback_response(message_lower: str, emoji: str) -> str:
    """获取预设回复（AI不可用时）"""
    # 问候类
    greetings = ['你好', 'hello', 'hi', '早上好', '晚上好', '嗨', '在吗']
    if any(greeting in message_lower for greeting in greetings):
        content = random.choice([
            "主人你好呀！今天过得怎么样？",
            "哈喽~ 主人需要查询价格或游戏状态吗？",
            "你好你好！小莲随时为你服务哦~"
        ])
        return f"{emoji} {content}"

    # 询问身份
    who_keywords = ['你是谁', '你叫什么', '名字', 'who are you', 'what is your name']
    if any(keyword in message_lower for keyword in who_keywords):
        bot_name = config.personality.get('name', '超级小莲')
        content = f"我是{bot_name}，专门帮主人查询Warframe价格和游戏状态的猫娘助手哦！"
        return f"{emoji} {content}"

    # 感谢类
    thanks = ['谢谢', 'thanks', 'thank you', '辛苦了', 'thx']
    if any(thank in message_lower for thank in thanks):
        content = random.choice([
            "不客气啦！能帮到主人小莲好开心~",
            "主人不用谢！这是我应该做的呀",
            "（摇尾巴）能帮到主人就好啦！"
        ])
        return f"{emoji} {content}"

    # 默认回应
    content = random.choice([
        "主人在说什么呀？小莲没太听懂呢~",
        "需要查询价格或游戏状态的话，可以直接告诉我哦！",
        "主人是想闲聊还是有查询需求呀？可以具体说说~"
    ])
    return f"{emoji} {content}"