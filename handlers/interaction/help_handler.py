# handlers/interaction/help_handler.py
import nonebot
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot import on_message
from nonebot.rule import Rule
from utils.command_checker import is_help_command
from core.formatters.response_formatter import ResponseFormatter

# 创建帮助处理器
help_handler = on_message(rule=Rule(is_help_command), priority=5, block=True)

@help_handler.handle()
async def handle_help_message(bot: Bot, event: Event):
    """处理帮助命令（使用完整帮助方法）"""
    # 使用新增的完整帮助方法
    help_response = ResponseFormatter.format_full_help()
    await bot.send(event, Message(help_response))
