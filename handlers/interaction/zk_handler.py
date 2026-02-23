# zk_handler.py - 仅修改紫卡查询结果为图片，其他功能不变
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import nonebot
import aiohttp
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot import on_command
from nonebot.params import CommandArg
from core.cache_manager import cache
from core.formatters.response_formatter import ResponseFormatter
from config import config
import logging

logger = logging.getLogger(__name__)

# 导入文本转图片工具（关键：新增）
from utils.text_to_image import text_to_image

# ===================== 紫卡属性汉化映射（保持原有逻辑不变）=====================
RIVEN_ATTR_MAP = {
    "punch_through": "穿透",
    "slash_damage": "切割伤害",
    "impact_damage": "冲击伤害",
    "toxin_damage": "毒素伤害",
    "status_duration": "异常持续时间",
    "ammo_maximum": "最大弹药量",
    "recoil": "后坐力",
    "zoom": "变焦",
    "channeling_damage": "初始连击",
    "channeling_efficiency": "重击效率",
    "critical_chance": "暴击几率",
    "critical_damage": "暴击伤害",
    "base_damage_/_melee_damage": "基础伤害/近战伤害",
    "heat_damage": "火焰伤害",
    "multishot": "多重射击",
    "reload_speed": "换弹速度",
    "range": "攻击范围",
    "damage_vs_corpus": "对科普斯伤害",
    "damage_vs_grineer": "对克隆尼伤害",
    "puncture_damage": "穿刺伤害",
    "damage_vs_infested": "对感染者伤害",
    "electric_damage": "电击伤害",
    "finisher_damage": "处决伤害",
    "fire_rate_/_attack_speed": "射速/攻击速度",
    "projectile_speed": "投射物速度",
    "magazine_capacity": "弹匣容量",
    "status_chance": "异常几率",
    "cold_damage": "冰冻伤害",
    "combo_duration": "连击持续时间",
    "critical_chance_on_slide_attack": "滑砍暴击几率",
    "chance_to_gain_extra_combo_count": "额外连击计数几率",
    "chance_to_gain_combo_count": "获取连击计数几率"
}

# ===================== 极性映射（保持原有逻辑不变）=====================
POLARITY_MAP = {
    "madurai": "r槽 Madurai",
    "vazarin": "三角 Vazarin",
    "naramon": "横槽 Naramon",
}


# ===================== 加载武器映射（保持原有逻辑不变）=====================
def load_weapon_mapping(json_file: str = "data/game_data/riven_weapons.json") -> Dict[str, str]:
    weapon_map = {}
    try:
        file_path = Path(json_file)
        logger.debug(f"📂 尝试加载武器映射文件：{file_path.absolute()}")

        # 检查文件是否存在
        if not file_path.exists():
            logger.error(f"❌ 武器映射文件不存在！请确认{json_file}在项目根目录")
            return weapon_map

        # 读取JSON文件
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 解析JSON数据（需为数组格式）
        if isinstance(data, list):
            logger.debug(f"✅ 成功读取JSON数组，共{len(data)}条数据")
            for idx, item in enumerate(data):
                if isinstance(item, dict):
                    zh_name = item.get("weapon_name_zh")
                    url_name = item.get("weapon_url_name")
                    if zh_name and url_name:
                        weapon_map[zh_name] = url_name
                    else:
                        logger.warning(f"⚠️ 第{idx + 1}条数据缺少weapon_name_zh或weapon_url_name字段")
        else:
            logger.error(f"❌ JSON格式错误！文件应为数组格式（开头[，结尾]）")

        # 日志输出加载结果
        logger.debug(f"✅ 武器映射加载完成，共收录{len(weapon_map)}种武器")

    except json.JSONDecodeError:
        logger.error(f"❌ JSON文件解析失败！请检查文件格式（逗号、引号是否正确）", exc_info=True)
    except Exception as e:
        logger.error(f"❌ 加载武器映射失败：{str(e)}", exc_info=True)
    return weapon_map


# 执行武器映射加载
WEAPON_MAP = load_weapon_mapping()

# ===================== 紫卡查询处理器（命令：/紫卡，保持不变）=====================
riven_handler = on_command(
    "紫卡",  # 主命令（用户发送/紫卡触发）
    priority=12,  # 优先级（低于帮助命令，高于@回应）
    block=True  # 阻断后续处理器
)


# ===================== 辅助函数：解析用户参数（分离武器名和0洗标识）=====================
def parse_args(raw_text: str) -> Tuple[str, bool]:
    """
    解析用户输入格式：
    - 支持：/紫卡 武器名 0洗 或 /紫卡 0洗 武器名
    - 返回：(武器中文名称, 是否为0洗紫卡)
    """
    raw_text = raw_text.strip()
    # 判断是否包含"0洗"关键词
    is_zero_roll = "0洗" in raw_text
    # 移除"0洗"，提取纯武器名
    weapon_zh = raw_text.replace("0洗", "").strip()
    return weapon_zh, is_zero_roll


# ===================== 紫卡查询核心逻辑（修改结果为图片）=====================
@riven_handler.handle()
async def handle_riven_command(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 1. 获取用户原始输入
        raw_input = args.extract_plain_text().strip()
        user_id = event.get_user_id()
        logger.info(f"🔍 收到紫卡查询请求：原始输入={raw_input}，用户={user_id}")

        # 2. 解析参数（分离武器名和0洗标识）
        weapon_zh, is_zero_roll = parse_args(raw_input)

        # 3. 处理空输入（用户只发了/紫卡，没带武器名）
        if not weapon_zh:
            help_text = (
                "喵~ 紫卡查询用法：\n"
                "基础格式：/紫卡 + 武器中文名称\n"
                "示例：/紫卡 玻之武杖、/紫卡 科林斯\n"
                "0洗筛选：/紫卡 玻之武杖 0洗 或 /紫卡 0洗 玻之武杖\n"
                "自动返回价格最低的3个在售紫卡（卖家在线）"
            )
            logger.info(f"ℹ️ 用户{user_id}发送空查询，返回帮助信息")
            await bot.send(event, Message(help_text))
            return

        # 4. 检查武器是否在映射表中（确保能找到对应的API名称）
        if weapon_zh not in WEAPON_MAP:
            error_msg = f"喵~ 未找到【{weapon_zh}】的映射数据！"
            # 提供相似武器推荐（提升用户体验）
            similar_names = [name for name in WEAPON_MAP.keys() if weapon_zh in name]
            if similar_names:
                error_msg += f"\n相似武器：{', '.join(similar_names[:3])}"  # 最多显示3个
            logger.warning(f"⚠️ 用户{user_id}查询的武器{weapon_zh}不在映射表中")
            await bot.send(event, Message(error_msg))
            return

        # 5. 发送查询中提示（区分0洗和普通查询）
        if is_zero_roll:
            querying_msg = f"{config.get_random_emoji()} 喵~ 正在查询【{weapon_zh}】的0洗紫卡数据..."
        else:
            querying_msg = f"{config.get_random_emoji()} 喵~ 正在查询【{weapon_zh}】的紫卡数据..."
        await bot.send(event, Message(querying_msg))
        logger.info(f"📤 已向用户{user_id}发送查询中提示")

        # 6. 获取武器的API名称（从映射表中读取）
        weapon_url_name = WEAPON_MAP[weapon_zh]
        logger.info(f"🌐 开始查询紫卡API：weapon_url_name={weapon_url_name}，是否0洗={is_zero_roll}")

        # 7. 缓存逻辑（优先从缓存获取，避免重复调用API）
        cached_rivens = await cache.get("riven_data", weapon_url_name)
        if cached_rivens:
            logger.info(f"✅ 从缓存获取到{len(cached_rivens)}条{weapon_zh}紫卡数据")
            rivens_data = cached_rivens
        else:
            # 缓存未命中，调用API获取数据
            rivens_data = await query_riven_api_async(weapon_url_name)
            if rivens_data:
                # 缓存新获取的数据（过期时间由cache_manager控制）
                await cache.set("riven_data", rivens_data, weapon_url_name)
                logger.info(f"✅ API查询成功，获取{len(rivens_data)}条{weapon_zh}紫卡数据并缓存")
            else:
                # API查询失败
                logger.error(f"❌ 用户{user_id}查询{weapon_zh}紫卡时API返回空数据")
                error_msg = "喵~ API查询失败，请稍后再试！"
                await bot.send(event, Message(error_msg))
                return

        # 8. 筛选有效紫卡（未关闭+卖家在线）
        logger.info(f"🔧 开始筛选{weapon_zh}紫卡数据：原始{len(rivens_data)}条")
        valid_rivens = [
            r for r in rivens_data
            if r.get("closed") is False and r.get("owner", {}).get("status") == "ingame"
        ]

        # 9. 0洗筛选（仅保留重Roll次数为0的紫卡）
        if is_zero_roll:
            valid_rivens = [
                r for r in valid_rivens
                if r.get("item", {}).get("re_rolls", 0) == 0
            ]
            logger.info(f"✅ 0洗筛选后：{len(valid_rivens)}条（重Roll次数=0）")
        else:
            logger.info(f"✅ 筛选后（未关闭+卖家在线）：{len(valid_rivens)}条")

        # 10. 处理无有效紫卡的情况
        if not valid_rivens:
            if is_zero_roll:
                error_msg = f"喵~ 【{weapon_zh}】暂无在售且卖家在线的0洗紫卡"
            else:
                error_msg = f"喵~ 【{weapon_zh}】暂无在售且卖家在线的紫卡"
            logger.info(f"ℹ️ 用户{user_id}查询{weapon_zh}紫卡无有效结果")
            await bot.send(event, Message(error_msg))
            return

        # 11. 按价格升序排序（取最低价前3条）
        valid_rivens.sort(
            key=lambda x: x.get("starting_price", 99999) or x.get("buyout_price", 99999)
        )
        top3_rivens = valid_rivens[:3]
        logger.info(f"📊 已筛选出{weapon_zh}紫卡价格最低前3条")

        # 12. 生成紫卡结果文本（修改：去除分割线）
        response_text = format_rivens_response(weapon_zh, top3_rivens, is_zero_roll)

        # 13. 文本转图片（使用紫卡专用转换方法，宽度600）
        title = f"【{weapon_zh}】紫卡查询结果"
        if is_zero_roll:
            title = f"【{weapon_zh}】0洗紫卡查询结果"

        if hasattr(text_to_image, 'convert_riven'):
            img_byte_io = text_to_image.convert_riven(
                text=response_text,
                title=title,
                max_width=700  # 设置宽度为600
            )
        else:
            # 回退到简单转换方法
            img_byte_io = text_to_image.convert_simple(
                text=response_text,
                title=title,
                max_width=700  # 设置宽度为600
            )

        # 14. 发送图片回复
        await bot.send(event, MessageSegment.image(img_byte_io))
        logger.info(f"📤 已向用户{user_id}发送{weapon_zh}紫卡图片结果")

    except Exception as e:
        # 全局异常处理（避免机器人崩溃，提供明确错误提示）
        error_detail = str(e)[:30]  # 截取前30字符，避免消息过长
        weapon_name = weapon_zh if 'weapon_zh' in locals() else '未知武器'
        error_msg = f"喵~ 查询【{weapon_name}】紫卡时出错：{error_detail}...\n请检查日志或稍后再试"
        logger.error(f"❌ 紫卡查询全程异常（用户{event.get_user_id()}）：{str(e)}", exc_info=True)
        await bot.send(event, Message(error_msg))


# ===================== 异步API查询函数（使用aiohttp）=====================
async def query_riven_api_async(weapon_url_name: str) -> List[dict]:
    """
    异步调用Warframe Market API获取紫卡拍卖数据
    :param weapon_url_name: 武器的API名称（从映射表获取）
    :return: 紫卡拍卖数据列表（空列表表示失败）
    """
    api_url = "https://api.warframe.market/v1/auctions/search"
    # API参数（筛选PC平台、直接购买、指定武器）
    params = {
        "type": "riven",
        "sort_by": "price_asc",  # 按价格升序
        "weapon_url_name": weapon_url_name,
        "platform": "pc",
        "buyout_policy": "direct"  # 仅显示支持直接购买的
    }
    # 请求头（模拟浏览器，避免被API拦截）
    headers = {
        "Accept": "application/json",
        "Language": "zh-hans",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        logger.info(f"📡 发送紫卡API请求：{api_url}，参数={params}")
        # 使用aiohttp发送异步请求（超时15秒）
        async with aiohttp.ClientSession() as session:
            async with session.get(
                api_url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                response.raise_for_status()  # 触发HTTP错误（如404、500）
                data = await response.json()
                # 提取拍卖数据（API返回格式固定在payload.auctions）
                auctions = data.get("payload", {}).get("auctions", [])
                logger.info(f"📥 紫卡API返回{len(auctions)}条拍卖数据")
                return auctions

    except aiohttp.ClientTimeout:
        logger.error(f"❌ 紫卡API请求超时（15秒）")
        return []
    except aiohttp.ClientError as e:
        logger.error(f"❌ 紫卡API请求失败：{str(e)}")
        return []
    except Exception as e:
        logger.error(f"❌ 紫卡API查询异常：{str(e)}", exc_info=True)
        return []


# ===================== 紫卡结果文本格式化（修改：去除分割线）=====================
def format_rivens_response(weapon_zh: str, rivens: List[dict], is_zero_roll: bool) -> str:
    """
    生成紫卡查询结果的文本内容（供后续转图片使用）
    :param weapon_zh: 武器中文名称
    :param rivens: 筛选后的紫卡数据（前3条最低价）
    :param is_zero_roll: 是否为0洗紫卡
    :return: 格式化后的文本字符串
    """
    # 标题区分0洗和普通紫卡（去除emoji）
    if is_zero_roll:
        title = f"喵~ 找到【{weapon_zh}】的0洗紫卡啦！（价格最低前3）"
    else:
        title = f"喵~ 找到【{weapon_zh}】的紫卡啦！（价格最低前3）"

    # 构建文本内容列表（便于后续拼接）
    lines = [
        title,
        ""  # 空行代替分割线
    ]

    # 遍历前3条紫卡，逐行添加信息
    for idx, riven in enumerate(rivens, 1):
        # 提取紫卡基础信息
        item = riven.get("item", {})
        owner = riven.get("owner", {})
        starting_price = riven.get("starting_price", 0)
        buyout_price = riven.get("buyout_price")  # 直接购买价（可能为None）
        re_rolls = item.get("re_rolls", 0)  # 重Roll次数
        mastery_level = item.get("mastery_level", 0)  # 段位要求
        mod_rank = item.get("mod_rank", 0)  # 紫卡等级

        # 处理极性（映射为中文显示）
        raw_polarity = item.get("polarity", "无").lower()
        polarity = POLARITY_MAP.get(raw_polarity, raw_polarity.capitalize())

        # 解析紫卡属性（含正负属性标识）
        attrs_raw = item.get("attributes", [])
        attrs = []
        for attr in attrs_raw:
            if not isinstance(attr, dict):
                continue
            # 处理属性值（保留1位小数）
            val = round(attr.get("value", 0), 1)
            # 正负属性标识（+为正属性，-为负属性）
            positive = attr.get("positive", False)
            url_name = attr.get("url_name", "未知属性")

            sign = "+" if positive else "-"
            # 映射属性名为中文
            attr_name = RIVEN_ATTR_MAP.get(url_name, url_name)
            attrs.append(f"{sign}{val} {attr_name}")

        # 处理属性显示（无属性时提示）
        attr_str = " | ".join(attrs) if attrs else "无属性"
        # 处理卖家名称（未知时显示默认值）
        seller_name = owner.get("ingame_name", "未知卖家")
        # 处理价格显示（优先显示直接购买价，无则显示起拍价）
        if buyout_price is not None:
            price_str = f"{buyout_price} 白金（直接购买）"
        else:
            price_str = f"{starting_price} 白金（起拍价）"

        # 拼接单条紫卡信息（去除emoji）
        lines.extend([
            f"【第{idx}条】",
            f"价格：{price_str}",
            f"段位要求：{mastery_level} | 紫卡等级：{mod_rank} | 重Roll次数：{re_rolls}次 | 极性：{polarity}",
            f"紫卡属性：{attr_str}",
            f"卖家：{seller_name}（在线可交易）",
            ""  # 每个紫卡之间添加空行
        ])

    # 添加小贴士（引导用户交易，去除emoji）
    lines.append("提示：价格单位为白金，游戏内直接搜索卖家名称即可发起交易~")

    # 拼接为完整文本（换行符分隔）
    return "\n".join(lines)