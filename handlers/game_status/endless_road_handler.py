# handlers/game_status/endless_road_handler.py - 无尽回廊查询
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)

# 延迟导入NoneBot相关模块，避免在本地测试时导入失败
try:
    import nonebot
    from nonebot.adapters.onebot.v11 import Bot, Event, Message
    from nonebot import on_command
    from nonebot.params import CommandArg
    NONE_BOT_AVAILABLE = True
except ImportError:
    NONE_BOT_AVAILABLE = False
    # 创建占位符类
    class Bot:
        pass
    class Event:
        pass
    class Message:
        @staticmethod
        def __init__(self, message):
            pass
    class CommandArg:
        pass
    def on_command(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

# 加载紫卡武器映射表用于翻译（复用紫卡的武器映射）
def load_weapon_mapping() -> Dict[str, str]:
    """加载武器英文名称到中文名称的映射"""
    weapon_map = {}
    try:
        json_file = Path("data/game_data/riven_weapons.json")
        if not json_file.exists():
            logger.error(f"武器映射文件不存在: {json_file}")
            return weapon_map
        
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "weapon_name_en" in item:
                    en_name = item["weapon_name_en"]
                    zh_name = item.get("weapon_name_zh", "")
                    # 移除空格和特殊字符的键用于匹配（如AckAndBrunt匹配Ack & Brunt）
                    en_key = en_name.replace(" & ", "").replace(" ", "")
                    if en_name and zh_name:
                        weapon_map[en_key] = zh_name
                        weapon_map[en_name] = zh_name  # 同时保存原始名称
        
        logger.debug(f"武器映射加载完成，共收录{len(weapon_map)}种武器")
    except Exception as e:
        logger.error(f"加载武器映射失败: {e}", exc_info=True)
    return weapon_map

# 加载武器映射
WEAPON_MAP = load_weapon_mapping()

# 无尽回廊查询处理器（仅在NoneBot可用时创建）
if NONE_BOT_AVAILABLE:
    from managers.game_status_manager import game_status_manager
    from core.formatters.response_formatter import ResponseFormatter
    
    endless_road_handler = on_command(
        "无尽回廊",
        aliases={"endless", "road", "回廊", "无尽"},
        priority=15,
        block=True
    )
else:
    # 本地测试时创建占位符
    endless_road_handler = None
    ResponseFormatter = None


def translate_weapon_name(weapon_en: str) -> str:
    """
    翻译武器名称（处理无尽回廊中的武器名格式）
    例如：AckAndBrunt -> 认知 & 冲击
    """
    if not weapon_en:
        return "未知"
    
    # 先直接查找
    if weapon_en in WEAPON_MAP:
        return WEAPON_MAP[weapon_en]
    
    # 处理没有空格的形式（如AckAndBrunt）
    for en_name, zh_name in WEAPON_MAP.items():
        if en_name.replace(" & ", "").replace(" ", "").lower() == weapon_en.lower():
            return zh_name
    
    # 特殊处理
    special_cases = {
        "AckAndBrunt": "认知 & 冲击",
        "NamiSolo": "海波单剑",
    }
    if weapon_en in special_cases:
        return special_cases[weapon_en]
    
    # 如果没找到，返回原始名称（首字母大写）
    return weapon_en


def format_endless_road_response(endless_data: List[Dict]) -> str:
    """
    格式化无尽回廊响应文本
    """
    if not endless_data:
        return "当前没有无尽回廊数据"
    
    lines = ["无尽回廊选项", "=" * 30, ""]
    
    for category in endless_data:
        category_type = category.get("Category", "")
        choices = category.get("Choices", [])
        
        if category_type == "EXC_NORMAL":
            lines.append("【普通无尽回廊】")
            lines.append("可选战甲：")
            for choice in choices:
                lines.append(f"• {choice}")
        elif category_type == "EXC_HARD":
            lines.append("【钢铁无尽回廊】")
            lines.append("可灵化武器：")
            for choice in choices:
                zh_name = translate_weapon_name(choice)
                lines.append(f"• {zh_name} ({choice})")
        else:
            # 未知类型
            lines.append(f"【未知类型: {category_type}】")
            for choice in choices:
                lines.append(f"• {choice}")
        
        lines.append("")  # 添加空行分隔
    
    return "\n".join(lines).strip()


# 仅在NoneBot可用时定义处理器函数
if NONE_BOT_AVAILABLE and endless_road_handler:
    @endless_road_handler.handle()
    async def handle_endless_road_command(bot: Bot, event: Event, args: Message = CommandArg()):
        """处理无尽回廊查询命令"""
        try:
            await bot.send(event, Message("正在查询无尽回廊选项..."))
            
            # 获取世界状态数据
            data = await game_status_manager.fetch_world_state()
            if not data:
                error_msg = ResponseFormatter.format_error_response("获取无尽回廊数据失败")
                await bot.send(event, Message(error_msg))
                return
            
            # 获取无尽回廊数据
            endless_choices = data.get("EndlessXpChoices", [])
            if not endless_choices:
                await bot.send(event, Message("当前没有无尽回廊数据"))
                return
            
            # 格式化响应
            response_text = format_endless_road_response(endless_choices)
            
            # 使用格式化器格式化最终响应（添加猫娘风格）
            final_response = ResponseFormatter.format_game_status_response(response_text)
            
            await bot.send(event, Message(final_response))
            
        except Exception as e:
            logger.error(f"查询无尽回廊异常: {e}", exc_info=True)
            error_msg = ResponseFormatter.format_error_response("查询无尽回廊信息失败")
            await bot.send(event, Message(error_msg))


# 本地测试辅助函数（不依赖NoneBot）
async def get_endless_road_data():
    """
    获取无尽回廊数据（本地测试使用，不依赖NoneBot）
    """
    try:
        # 延迟导入，避免循环导入
        from managers.game_status_manager import game_status_manager
        
        # 获取世界状态数据
        data = await game_status_manager.fetch_world_state()
        if not data:
            return None
        
        # 获取无尽回廊数据
        return data.get("EndlessXpChoices", [])
    except Exception as e:
        logger.error(f"获取无尽回廊数据失败: {e}", exc_info=True)
        return None
