"""
日历管理器 - 管理 1999 日历赛季数据
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, TypedDict

from core.translators.challenge_translator import ChallengeTranslator
from utils.game_constants import (
    SEASON_NAME_TRANSLATIONS,
    EVENT_TYPE_LABELS,
    get_season_name_translation,
    get_event_type_label,
)
from utils.time_utils import calculate_date_from_day, format_countdown

logger = logging.getLogger(__name__)


class CalendarEvent(TypedDict):
    """日历事件数据结构"""
    day: int
    date: str
    event_type: str
    label: str
    name: str
    desc: str


class CalendarSeasonData(TypedDict):
    """日历赛季数据结构"""
    season: str
    season_name: str
    year_iteration: int
    activation: int
    expiry: int
    countdown: str
    events: List[CalendarEvent]


# 挑战名称映射（日历专用）
CHALLENGE_NAME_MAP = {
    "CalendarKillTechrotEnemiesWithAbilitiesMedium": "化为乌有",
    "CalendarKillScaldraEnemiesWithAbilitiesEasy": "翻山震虎",
    "CalendarKillEnemiesMedium": "平分秋色",
    "CalendarKillEnemiesWithAbilitiesMedium": "力量展现",
    "CalendarKillEximusHard": "逝去卓越者",
    "CalendarKillEnemiesWithMeleeHard": "游刃有余",
}

# 奖励手动映射（日历专用）
MANUAL_REWARD_MAP = {
    "/Lotus/StoreItems/Types/Recipes/Components/FormaBlueprint": "Forma 蓝图",
    "/Lotus/Types/StoreItems/Boosters/ModDropChanceBooster3DayStoreItem": "3 天 Mod 掉落几率加成",
    "/Lotus/Types/StoreItems/Boosters/AffinityBooster3DayStoreItem": "3 天经验值加成",
    "/Lotus/StoreItems/Types/BoosterPacks/CalendarRivenPack": "紫卡包",
    "/Lotus/StoreItems/Types/Recipes/Components/WeaponUtilityUnlockerBlueprint": "武器特殊功能槽连接器 蓝图",
}


class CalendarManager:
    """日历管理器"""

    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_time: Optional[datetime] = None
        self._translator = ChallengeTranslator()
        self._cache_duration = 3600
        self.worldstate_url = "https://api.warframe.com/cdn/worldState.php"
        self.zh_translations = self._load_zh_translations()

    def _load_zh_translations(self) -> Dict[str, str]:
        """加载 zh.json 翻译文件"""
        zh_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "translations", "zh.json")
        try:
            with open(zh_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"无法加载 zh.json: {e}")
            return {}

    async def _fetch_world_state_from_api(self) -> Optional[Dict[str, Any]]:
        """从 Warframe API 获取世界状态数据"""
        try:
            import aiohttp

            logger.info("从 Warframe API 获取实时日历数据")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.worldstate_url,
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={'User-Agent': 'Warframe-Calendar-Bot/1.0'}
                ) as response:
                    if response.status == 200:
                        text_data = await response.text()
                        data = json.loads(text_data)
                        logger.info("成功获取世界状态数据")
                        return data
                    else:
                        logger.error(f"获取世界状态失败: HTTP {response.status}")
                        return None

        except Exception as e:
            logger.error(f"从 API 获取世界状态异常: {e}", exc_info=True)
            return None

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self._cache or not self._cache_time:
            return False
        now = datetime.now()
        return (now - self._cache_time).total_seconds() < self._cache_duration

    async def fetch_calendar_info(self) -> Optional[CalendarSeasonData]:
        """获取日历信息"""
        if self._is_cache_valid():
            logger.info("使用缓存的日历数据")
            return self._cache

        logger.info("从 Warframe API 加载日历数据")
        world_state = await self._fetch_world_state_from_api()

        if not world_state:
            logger.error("无法从 API 获取世界状态数据")
            if self._cache:
                return self._cache
            return None

        try:
            calendar_seasons = world_state.get('KnownCalendarSeasons', [])

            if not calendar_seasons:
                logger.warning("API 返回的数据中没有 KnownCalendarSeasons")
                if self._cache:
                    return self._cache
                return None

            season_data = calendar_seasons[0]
            result = self._parse_calendar_data(season_data)

            self._cache = result
            self._cache_time = datetime.now()

            logger.info(f"日历数据加载成功: {result['season_name']}")
            return result

        except Exception as e:
            logger.error(f"解析日历数据失败: {e}", exc_info=True)
            if self._cache:
                return self._cache
            return None

    def _parse_calendar_data(self, season_data: Dict[str, Any]) -> CalendarSeasonData:
        """解析日历数据"""
        season_code = season_data.get("Season", "UNKNOWN")
        season_name = get_season_name_translation(season_code)
        year_iteration = season_data.get("YearIteration", 0)

        activation_ms = 0
        expiry_ms = 0
        if "Activation" in season_data:
            activation_ms = int(season_data["Activation"].get("$date", {}).get("$numberLong", 0))
        if "Expiry" in season_data:
            expiry_ms = int(season_data["Expiry"].get("$date", {}).get("$numberLong", 0))

        countdown = format_countdown(expiry_ms)
        events = self._parse_events(season_data.get("Days", []), activation_ms)

        return CalendarSeasonData(
            season=season_code,
            season_name=season_name,
            year_iteration=year_iteration,
            activation=activation_ms,
            expiry=expiry_ms,
            countdown=countdown,
            events=events
        )

    def _parse_events(self, days: List[Dict[str, Any]], activation_ms: int) -> List[CalendarEvent]:
        """解析事件列表"""
        events = []

        for day_info in days:
            day = day_info.get("day", 0)
            day_events = day_info.get("events", [])

            if not day_events:
                continue

            date_str = calculate_date_from_day(activation_ms, day)

            for event in day_events:
                parsed = self._parse_single_event(event, day, date_str)
                if parsed:
                    events.append(parsed)

        return events

    def _parse_single_event(self, event: Dict[str, Any], day: int, date_str: str) -> Optional[CalendarEvent]:
        """解析单个事件"""
        event_type = event.get("type", "UNKNOWN")
        label = get_event_type_label(event_type)

        if event_type == "CET_CHALLENGE":
            challenge_id = event.get("challenge", "")
            if challenge_id:
                challenge_desc = self._translator.translate_challenge(challenge_id)
                challenge_name = CHALLENGE_NAME_MAP.get(challenge_id.split('/')[-1], "")
                return CalendarEvent(
                    day=day, date=date_str, event_type=event_type,
                    label=label, name=challenge_name, desc=challenge_desc or challenge_id,
                )

        elif event_type == "CET_REWARD":
            reward_path = event.get("reward", "")
            if reward_path:
                reward_name = self._translate_reward(reward_path)
                return CalendarEvent(
                    day=day, date=date_str, event_type=event_type,
                    label=label, name="", desc=reward_name,
                )

        elif event_type == "CET_UPGRADE":
            upgrade_path = event.get("upgrade", "")
            if upgrade_path:
                upgrade_info = self._translate_upgrade(upgrade_path)
                return CalendarEvent(
                    day=day, date=date_str, event_type=event_type,
                    label=label, name=upgrade_info["name"], desc=upgrade_info["desc"],
                )

        return None

    def _translate_reward(self, reward_path: str) -> str:
        """翻译奖励物品"""
        if reward_path in MANUAL_REWARD_MAP:
            return MANUAL_REWARD_MAP[reward_path]

        parts = reward_path.split('/')
        item_name = parts[-1] if parts else reward_path

        # 在 1999 语言包中查找
        name_key_1999 = f"/Lotus/Language/1999/{item_name}Name"
        desc_key_1999 = f"/Lotus/Language/1999/{item_name}Desc"

        if name_key_1999 in self.zh_translations:
            name = self.zh_translations[name_key_1999]
            if desc_key_1999 in self.zh_translations:
                desc = self.zh_translations[desc_key_1999]
                return f"{name} - {desc}"
            return name

        # 在 Items 语言包中查找
        name_key_items = f"/Lotus/Language/Items/{item_name}"
        if name_key_items in self.zh_translations:
            return self.zh_translations[name_key_items]

        # 简化命名
        item_name = item_name.replace('Blueprint', '蓝图').replace('Pack', '包')
        item_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', item_name)
        return item_name

    def _translate_upgrade(self, upgrade_path: str) -> Dict[str, str]:
        """翻译升级项"""
        parts = upgrade_path.split('/')
        upgrade_name = parts[-1] if parts else upgrade_path

        name_key = f"/Lotus/Language/1999/{upgrade_name}Name"
        desc_key = f"/Lotus/Language/1999/{upgrade_name}Desc"

        if name_key in self.zh_translations:
            name = self.zh_translations[name_key]
            if desc_key in self.zh_translations:
                desc = self.zh_translations[desc_key]
                # 清理异常状态标签
                for tag in ['<DT_EXPLOSION>', '<DT_RADIATION>', '<DT_GAS>', '<DT_MAGNETIC>', '|CONDITION|']:
                    desc = desc.replace(tag, '')
                return {"name": name, "desc": desc}
            return {"name": name, "desc": ""}

        return {"name": upgrade_name, "desc": ""}

    def format_calendar_info(self, calendar_data: CalendarSeasonData) -> str:
        """格式化日历信息为文本格式"""
        lines = [
            f"📅  1999    {calendar_data['season_name']}",
            f"⏰ {calendar_data['countdown']}",
        ]

        current_day = 0
        for event in calendar_data['events']:
            if event['day'] != current_day:
                current_day = event['day']
                lines.extend(["", f"{current_day:2d}  {event['date']:8s}  {event['label']:>10s}"])

            if event['event_type'] == "CET_CHALLENGE":
                if event['name']:
                    lines.append(f"    {event['name']}")
                lines.append(f"    {event['desc']}")
            elif event['event_type'] == "CET_REWARD":
                lines.append(f"    {event['desc']}")
            elif event['event_type'] == "CET_UPGRADE":
                lines.append(f"    {event['name']}")
                if event['desc']:
                    lines.append(f"    {event['desc']}")

        return "\n".join(lines)

    def get_calendar_structured(self, calendar_data: CalendarSeasonData) -> List[Dict[str, str]]:
        """获取日历结构化数据，用于图片生成"""
        content = []

        # T1: 大标题（居中）
        content.append({
            "type": "T1",
            "text": "1999 日历",
            "align": "center"
        })

        # T2: 赛季 + 倒计时
        content.append({
            "type": "T2",
            "text": f"{calendar_data['season_name']} · {calendar_data['countdown']}",
            "align": "center"
        })

        # 空行分隔
        content.append({"type": "T4", "text": ""})

        current_day = 0
        for event in calendar_data['events']:
            if event['day'] != current_day:
                current_day = event['day']
                # T3: 日期 + 类型
                content.append({
                    "type": "T3",
                    "text": f"{event['date']} · {event['label']}"
                })

            if event['event_type'] == "CET_CHALLENGE":
                # T4: 挑战名称
                if event['name']:
                    content.append({
                        "type": "T4",
                        "text": event['name']
                    })
                # T4: 挑战描述
                content.append({
                    "type": "T4",
                    "text": event['desc']
                })
            elif event['event_type'] == "CET_REWARD":
                # T4: 奖励描述
                content.append({
                    "type": "T4",
                    "text": event['desc']
                })
            elif event['event_type'] == "CET_UPGRADE":
                # T4: 升级项名称
                content.append({
                    "type": "T4",
                    "text": event['name']
                })
                # T4: 升级项描述
                if event['desc']:
                    content.append({
                        "type": "T4",
                        "text": event['desc']
                    })

        return content
