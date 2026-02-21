# handlers/fissure_subscription_handler.py - 裂缝订阅处理器
import nonebot
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot import on_command
from nonebot.params import CommandArg
from managers.subscription_manager import subscription_manager, SubscriptionManager
from managers.translation_manager import translation_manager
from core.formatters.response_formatter import ResponseFormatter
from config import config
from utils.game_status_config import game_status_config
import logging

logger = logging.getLogger(__name__)

# 支持的星球名称（中文和英文）- 使用配置文件
SUPPORTED_PLANETS = {
    # 中文星球
    "水星": "水星", "金星": "金星", "地球": "地球", "火星": "火星",
    "木星": "木星", "土星": "土星", "天王星": "天王星", "海王星": "海王星",
    "冥王星": "冥王星", "赛德娜": "赛德娜", "欧罗巴": "欧罗巴", "阋神星": "阋神星",
    "火卫二": "火卫二", "火卫一": "火卫一", "月球": "月球",
    "帕尔沃斯": "帕尔沃斯的姐妹", "星环": "星环", "钢铁之路": "钢铁之路",
    # 英文星球
    "mercury": "水星", "venus": "金星", "earth": "地球", "mars": "火星",
    "jupiter": "木星", "saturn": "土星", "uranus": "天王星", "neptune": "海王星",
    "pluto": "冥王星", "sedna": "赛德娜", "europa": "欧罗巴", "eris": "阋神星",
    "deimos": "火卫二", "phobos": "火卫一", "lua": "月球",
    "parvos": "帕尔沃斯的姐妹", "orokin": "月球", "void": "虚空",
    "steel": "钢铁之路", "steel path": "钢铁之路",
    # 通用
    "全部": "all", "所有": "all", "all": "all"
}

# 支持的裂缝任务类型（中文和英文）- 使用配置文件
SUPPORTED_MISSION_TYPES = {
    # 中文任务类型
    "防御": "防御", "捕获": "捕获", "生存": "生存", "间谍": "间谍",
    "歼灭": "歼灭", "移动防御": "移动防御", "移动防禦": "移动防御",  # 繁体支持
    "救援": "救援", "破壞": "破坏", "破坏": "破坏",
    "攔截": "拦截", "拦截": "拦截", "刺殺": "刺杀", "刺杀": "刺杀",
    "挖掘": "挖掘", "叛逃": "叛逃", "中斷": "中断", "中断": "中断",
    "清巢": "清巢", "元素轉換": "元素转换", "元素转换": "元素转换",
    # 英文任务类型
    "defense": "防御", "capture": "捕获", "survival": "生存",
    "spy": "间谍", "extermination": "歼灭", "mobile defense": "移动防御",
    "mobiledefense": "移动防御", "rescue": "救援", "sabotage": "破坏",
    "interception": "拦截", "assassination": "刺杀", "excavation": "挖掘",
    "defection": "叛逃", "disruption": "中断", "hive": "清巢", "alchemy": "元素转换",
    "defense (archwing)": "防御", "mobile defense (archwing)": "移动防御",
    "extermination (archwing)": "歼灭"
}

# 支持的裂缝等级 - 使用配置文件
SUPPORTED_TIERS = {
    "古纪": "古纪", "前纪": "前纪", "中纪": "中纪", "后纪": "后纪",
    "安魂": "安魂", "全能": "全能",
    "全部": "all", "所有": "all", "all": "all"
}

# 支持的难度
SUPPORTED_DIFFICULTIES = {
    "钢铁": "steel", "普通": "normal", "steel": "steel", "hard": "steel",
    "normal": "normal", "所有": "both", "both": "both"
}

# 创建命令处理器
subscribe_handler = on_command("订阅裂缝", aliases={"订阅", "subscribe", "订阅虚空裂缝"}, priority=15, block=True)
unsubscribe_handler = on_command("取消订阅", aliases={"取消", "退订", "unsubscribe"}, priority=15, block=True)
list_subscriptions_handler = on_command("我的订阅", aliases={"订阅列表", "list", "subscriptions"}, priority=15, block=True)


@subscribe_handler.handle()
async def handle_subscribe_command(bot: Bot, event: Event, args: Message = CommandArg()):
    """处理订阅裂缝命令"""
    try:
        # 检查是否在群聊中
        if not hasattr(event, 'group_id') or not event.group_id:
            await bot.send(event, Message("❌ 订阅功能仅在群聊中可用"))
            return

        raw_args = args.extract_plain_text().strip()
        if not raw_args:
            await bot.send(event, Message(get_subscribe_help()))
            return

        # 分割参数
        parts = raw_args.split()

        # 解析参数
        difficulty = "normal"
        mission_type = None
        tier = "all"
        planet = "all"
        node_filter = None

        # 先尝试找到难度参数
        difficulty_found = False
        difficulty_index = -1

        for i, part in enumerate(parts):
            if part.lower() in SUPPORTED_DIFFICULTIES:
                difficulty = SUPPORTED_DIFFICULTIES[part.lower()]
                difficulty_found = True
                difficulty_index = i
                break

        # 如果找到难度参数，从列表中移除
        if difficulty_found:
            parts.pop(difficulty_index)

        # 剩下的参数中，检查是否有星球参数
        planet_found = False
        planet_index = -1

        for i, part in enumerate(parts):
            if part.lower() in SUPPORTED_PLANETS:
                planet = SUPPORTED_PLANETS[part.lower()]
                planet_found = True
                planet_index = i
                break

        # 如果找到星球参数，从列表中移除
        if planet_found:
            parts.pop(planet_index)

        # 剩下的参数中，最后一个可能是等级，尝试匹配
        if parts:
            last_part = parts[-1].lower()
            if last_part in SUPPORTED_TIERS:
                tier = SUPPORTED_TIERS[last_part]
                parts.pop()  # 移除等级参数

        # 剩下的部分组合起来作为任务类型
        if parts:
            mission_input = "".join(parts)  # 合并剩余部分
            mission_input_lower = mission_input.lower()

            # 尝试匹配任务类型
            mission_type = None

            # 1. 完全匹配
            if mission_input in SUPPORTED_MISSION_TYPES:
                mission_type = SUPPORTED_MISSION_TYPES[mission_input]
            elif mission_input_lower in SUPPORTED_MISSION_TYPES:
                mission_type = SUPPORTED_MISSION_TYPES[mission_input_lower]
            else:
                # 2. 部分匹配（遍历查找）
                for key, value in SUPPORTED_MISSION_TYPES.items():
                    if mission_input in key or key in mission_input:
                        mission_type = value
                        break
                    if mission_input_lower in key.lower() or key.lower() in mission_input_lower:
                        mission_type = value
                        break

            if not mission_type:
                await bot.send(event, Message(f"❌ 不支持的任务类型: {mission_input}\n\n{get_subscribe_help()}"))
                return
        else:
            await bot.send(event, Message(get_subscribe_help()))
            return

        # 添加订阅
        user_id = str(event.user_id)
        group_id = str(event.group_id)

        success = subscription_manager.add_subscription(
            user_id=user_id,
            group_id=group_id,
            mission_type=mission_type,
            difficulty=difficulty,
            tier=tier,
            planet=planet,
            node_filter=node_filter
        )

        if success:
            difficulty_text = "钢铁" if difficulty == "steel" else "普通"
            tier_text = tier if tier != "all" else "所有等级"
            planet_text = planet if planet != "all" else "所有星球"

            response = (
                f"✅ 订阅成功！\n"
                f"================\n"
                f"📋 订阅详情:\n"
                f"• 任务类型: {mission_type}\n"
                f"• 难度: {difficulty_text}\n"
                f"• 等级: {tier_text}\n"
                f"• 星球: {planet_text}\n"
                f"• 通知方式: 在群聊中@提醒\n\n"
                f"💡 当游戏中出现符合条件的裂缝时，我会在群里@您通知！\n"
                f"⏰ 监控频率: 每5分钟检查一次"
                f"💡 每个用户最多可订阅 {SubscriptionManager.MAX_SUBSCRIPTIONS_PER_USER} 个裂缝"
            )
        else:
            # 检查是否达到订阅上限
            user_subs = [s for s in subscription_manager.subscriptions if s.user_id == user_id]
            if len(user_subs) >= SubscriptionManager.MAX_SUBSCRIPTIONS_PER_USER:
                response = f"⚠️ 订阅失败：已达到订阅上限（{SubscriptionManager.MAX_SUBSCRIPTIONS_PER_USER}个）\n请先取消一些订阅后再试"
            else:
                response = "⚠️ 您已经订阅过相同的裂缝任务了"

        await bot.send(event, Message(response))

    except Exception as e:
        logger.error(f"处理订阅命令异常: {e}", exc_info=True)
        await bot.send(event, Message("❌ 订阅失败，请稍后再试"))


@unsubscribe_handler.handle()
async def handle_unsubscribe_command(bot: Bot, event: Event, args: Message = CommandArg()):
    """处理取消订阅命令"""
    try:
        # 检查是否在群聊中
        if not hasattr(event, 'group_id') or not event.group_id:
            await bot.send(event, Message("❌ 取消订阅功能仅在群聊中可用"))
            return
        
        raw_args = args.extract_plain_text().strip()
        user_id = str(event.user_id)
        group_id = str(event.group_id)
        
        if not raw_args:
            # 显示用户的订阅列表供选择
            subs = subscription_manager.get_user_subscriptions(user_id, group_id)
            if not subs:
                await bot.send(event, Message("📭 您当前没有任何裂缝订阅"))
                return
            
            subscription_list = format_subscription_list(subs)
            response = (
                f"📋 您的订阅列表:\n"
                f"================\n"
                f"{subscription_list}\n\n"
                f"💡 要取消订阅，请使用:\n"
                f"• /取消订阅 [任务类型] - 取消指定类型的订阅\n"
                f"• /取消订阅 全部 - 取消所有订阅"
            )
            await bot.send(event, Message(response))
            return
        
        if raw_args.lower() in ["全部", "所有", "all"]:
            # 取消所有订阅
            removed = subscription_manager.remove_subscription(user_id, group_id)
            if removed:
                response = f"✅ 已取消您的 {len(removed)} 个裂缝订阅"
            else:
                response = "📭 您当前没有任何裂缝订阅"
            await bot.send(event, Message(response))
            return
        
        # 解析任务类型
        mission_type_input = raw_args.lower()
        mission_type = None
        
        # 尝试匹配任务类型
        for key, value in SUPPORTED_MISSION_TYPES.items():
            if mission_type_input == key.lower() or mission_type_input == value.lower():
                mission_type = value
                break
        
        if not mission_type:
            # 模糊匹配
            for key, value in SUPPORTED_MISSION_TYPES.items():
                if mission_type_input in key.lower() or mission_type_input in value.lower():
                    mission_type = value
                    break
        
        if not mission_type:
            await bot.send(event, Message(f"❌ 不支持的任务类型: {raw_args}\n\n{get_unsubscribe_help()}"))
            return
        
        # 取消指定类型的订阅
        removed = subscription_manager.remove_subscription(
            user_id=user_id,
            group_id=group_id,
            mission_type=mission_type
        )
        
        if removed:
            response = f"✅ 已取消您的 {mission_type} 裂缝订阅（共 {len(removed)} 个）"
        else:
            response = f"📭 您没有订阅 {mission_type} 裂缝"
        
        await bot.send(event, Message(response))
        
    except Exception as e:
        logger.error(f"处理取消订阅命令异常: {e}", exc_info=True)
        await bot.send(event, Message("❌ 取消订阅失败，请稍后再试"))


@list_subscriptions_handler.handle()
async def handle_list_subscriptions_command(bot: Bot, event: Event):
    """处理查看订阅列表命令"""
    try:
        # 检查是否在群聊中
        if not hasattr(event, 'group_id') or not event.group_id:
            # 私聊查看所有群的订阅
            user_id = str(event.user_id)
            subs = subscription_manager.get_user_subscriptions(user_id)
            
            if not subs:
                await bot.send(event, Message("📭 您当前没有任何裂缝订阅"))
                return
            
            # 按群组分组
            subs_by_group = {}
            for sub in subs:
                if sub.group_id not in subs_by_group:
                    subs_by_group[sub.group_id] = []
                subs_by_group[sub.group_id].append(sub)
            
            response = "📋 您的裂缝订阅列表:\n================\n"
            
            for group_id, group_subs in subs_by_group.items():
                response += f"\n📁 群组: {group_id}\n"
                response += format_subscription_list(group_subs)
            
            await bot.send(event, Message(response))
            return
        
        # 群聊中查看当前群的订阅
        user_id = str(event.user_id)
        group_id = str(event.group_id)
        
        subs = subscription_manager.get_user_subscriptions(user_id, group_id)
        
        if not subs:
            await bot.send(event, Message("📭 您在当前群聊没有任何裂缝订阅"))
            return
        
        subscription_list = format_subscription_list(subs)
        response = (
            f"📋 您的裂缝订阅列表 (群: {group_id}):\n"
            f"================\n"
            f"{subscription_list}\n\n"
            f"📊 统计: 共 {len(subs)} 个订阅"
        )
        
        await bot.send(event, Message(response))
        
    except Exception as e:
        logger.error(f"处理查看订阅列表命令异常: {e}", exc_info=True)
        await bot.send(event, Message("❌ 查看订阅列表失败，请稍后再试"))


def format_subscription_list(subscriptions) -> str:
    """格式化订阅列表为文本"""
    if not subscriptions:
        return "无订阅"

    result = ""
    for i, sub in enumerate(subscriptions, 1):
        difficulty_text = "钢铁" if sub.difficulty == "steel" else "普通"
        tier_text = sub.tier if sub.tier != "all" else "所有等级"
        planet_text = sub.planet if sub.planet != "all" else "所有星球"

        # 计算订阅时长
        from datetime import datetime
        created_time = datetime.fromtimestamp(sub.created_time)
        now = datetime.now()
        days = (now - created_time).days

        result += f"{i}. {sub.mission_type} ({difficulty_text}, {tier_text}, {planet_text})\n"
        result += f"   订阅于: {created_time.strftime('%Y-%m-%d')} ({days}天前)\n"

    return result


def get_subscribe_help() -> str:
    """获取订阅帮助信息"""
    mission_types = list(set(SUPPORTED_MISSION_TYPES.values()))
    mission_types.sort()

    # 只显示前10个任务类型，避免消息过长
    mission_types_display = mission_types[:10]

    planets_list = ["水星", "金星", "地球", "火星", "木星", "土星", "天王星", "海王星",
                     "冥王星", "火卫二", "月球", "所有"]

    return (
        "💡 裂缝订阅帮助:\n"
        "================\n"
        "📝 命令格式: /订阅裂缝 [难度] [任务类型] [星球(可选)] [等级(可选)]\n\n"
        "📍 参数说明:\n"
        "• 难度: 钢铁 / 普通 (默认: 普通)\n"
        "• 任务类型: " + "、".join(mission_types_display) + "...\n"
        "• 星球: " + "、".join(planets_list) + " (默认: 所有)\n"
        "• 等级: 古纪、前纪、中纪、后纪、安魂、全能、全部 (默认: 全部)\n\n"
        "📌 示例:\n"
        "• /订阅裂缝 钢铁 防御\n"
        "• /订阅裂缝 普通 捕获 天王星\n"
        "• /订阅裂缝 钢铁 生存 火卫二 古纪\n"
        "• /订阅裂缝 防御 (默认普通难度、所有星球)\n\n"
        "🔔 功能说明:\n"
        "当游戏中出现符合条件的裂缝时，我会在群里@您通知！\n"
        "支持同时匹配多个条件，例如只订阅天王星的钢铁防御裂缝。"
    )


def get_unsubscribe_help() -> str:
    """获取取消订阅帮助信息"""
    return (
        "💡 取消订阅帮助:\n"
        "================\n"
        "📝 命令格式: /取消订阅 [任务类型/全部]\n\n"
        "📍 参数说明:\n"
        "• 任务类型: 要取消的裂缝任务类型\n"
        "• 全部: 取消所有订阅\n\n"
        "📌 示例:\n"
        "• /取消订阅 防御 - 取消防御裂缝订阅\n"
        "• /取消订阅 全部 - 取消所有订阅\n"
        "• /取消订阅 - 查看您的订阅列表"
    )