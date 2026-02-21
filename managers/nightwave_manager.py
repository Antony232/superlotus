"""
午夜电波管理器 - 管理午夜电波数据
"""

import logging
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime, timezone, timedelta
from core.translators.challenge_translator import ChallengeTranslator
import time

logger = logging.getLogger(__name__)


class NightwaveChallenge(TypedDict):
    """午夜电波挑战数据结构"""
    id: str
    title: str
    standing: int
    remaining_time: str
    is_daily: bool


class NightwaveData(TypedDict):
    """午夜电波数据结构"""
    season: int
    phase: int
    challenges: List[NightwaveChallenge]
    total_challenges: int


class NightwaveManager:
    """午夜电波管理器 - 处理午夜电波数据的获取和格式化"""

    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_time: Optional[datetime] = None
        self._translator = ChallengeTranslator()
        self._cache_duration = 3600  # 缓存1小时
        self.worldstate_url = "https://api.warframe.com/cdn/worldState.php"

    async def _fetch_world_state_from_api(self) -> Optional[Dict[str, Any]]:
        """从 Warframe API 获取世界状态数据"""
        try:
            import requests

            logger.info("从 Warframe API 获取实时数据")
            response = requests.get(self.worldstate_url, headers={'User-Agent': 'Warframe-Nightwave-Bot/1.0'}, timeout=10)

            if response.status_code == 200:
                # API 返回的是 text/html 但内容是 JSON 格式
                data = response.json()
                logger.info(f"成功获取世界状态数据，包含 SeasonInfo: {'SeasonInfo' in data}")
                return data
            else:
                logger.error(f"获取世界状态失败: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"从 API 获取世界状态异常: {e}", exc_info=True)
            return None

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self._cache or not self._cache_time:
            return False

        now = datetime.now(timezone.utc)
        time_diff = (now - self._cache_time).total_seconds()

        return time_diff < self._cache_duration

    def _should_force_refresh(self) -> bool:
        """
        检查是否应该强制刷新
        每天8:02强制刷新，确保数据已经更新
        """
        now = datetime.now()

        # 检查是否是8:02左右（8:02-8:05）
        if now.hour == 8 and 2 <= now.minute <= 5:
            logger.info("处于强制刷新时间段(8:02-8:05)，将刷新午夜电波数据")
            return True

        return False

    async def fetch_nightwave_info(self) -> Optional[NightwaveData]:
        """
        获取午夜电波信息（从 API 实时获取）

        Returns:
            午夜电波数据，如果失败返回None
        """
        # 检查是否需要强制刷新
        force_refresh = self._should_force_refresh()

        # 如果缓存有效且不需要强制刷新，使用缓存
        if not force_refresh and self._is_cache_valid():
            logger.info("使用缓存的午夜电波数据")
            return self._cache

        # 从 API 获取实时数据
        logger.info("从 Warframe API 加载午夜电波数据")
        world_state = await self._fetch_world_state_from_api()

        if not world_state:
            logger.error("无法从 API 获取世界状态数据")
            # 如果之前有缓存，即使过期也使用
            if self._cache:
                logger.info("使用过期缓存作为回退")
                return self._cache
            return None

        try:
            # 解析午夜电波数据
            nightwave_data = world_state.get('SeasonInfo', {})

            if not nightwave_data:
                logger.warning("API 返回的数据中没有 SeasonInfo")
                if self._cache:
                    return self._cache
                return None

            # 构建午夜电波数据结构
            result = self._parse_nightwave_data(nightwave_data)

            # 获得新缓存的同时删除旧缓存（更新缓存）
            self._cache = result
            self._cache_time = datetime.now(timezone.utc)

            logger.info(f"午夜电波数据加载成功: 赛季{result['season']}, 阶段{result['phase']}, 挑战数{result['total_challenges']}")

            return result

        except Exception as e:
            logger.error(f"解析午夜电波数据失败: {e}", exc_info=True)
            if self._cache:
                return self._cache
            return None

    def _parse_nightwave_data(self, nightwave_data: Dict[str, Any]) -> NightwaveData:
        """解析午夜电波数据"""
        result = NightwaveData(
            season=nightwave_data.get('Season', 0),
            phase=nightwave_data.get('Phase', 0),
            challenges=[],
            total_challenges=0
        )

        # 获取 ActiveChallenges 数组
        active_challenges = nightwave_data.get('ActiveChallenges', [])

        # 解析每个挑战
        for challenge in active_challenges:
            parsed = self._parse_challenge(challenge)
            if parsed:
                result['challenges'].append(parsed)

        # 按声望值排序（从低到高）
        result['challenges'].sort(key=lambda x: x['standing'])
        result['total_challenges'] = len(result['challenges'])

        return result

    def _parse_challenge(self, challenge: Dict[str, Any]) -> Optional[NightwaveChallenge]:
        """解析单个挑战"""
        try:
            challenge_id = challenge.get('Challenge', '')

            # 获取 Expiry 时间戳
            expiry_obj = challenge.get('Expiry', {})
            if isinstance(expiry_obj, dict) and '$date' in expiry_obj:
                expiry_timestamp = int(expiry_obj['$date'].get('$numberLong', 0))
            else:
                expiry_timestamp = 0

            # 判断是否为日常挑战
            is_daily = challenge.get('Daily', False)

            if not challenge_id:
                return None

            # 使用翻译器翻译挑战并获取声望值
            title, standing = self._translator.translate_challenge_with_standing(challenge_id)

            if not title:
                # 如果翻译失败，使用ID作为标题
                title = challenge_id.split('/')[-1]
                # 默认声望值
                standing = 1000 if is_daily else 3000

            # 格式化剩余时间
            remaining_time = self._translator.format_remaining_time(expiry_timestamp)

            return NightwaveChallenge(
                id=challenge_id,
                title=title,
                standing=standing,
                remaining_time=remaining_time,
                is_daily=is_daily
            )

        except Exception as e:
            logger.error(f"解析挑战失败 {challenge}: {e}")
            return None

    def format_nightwave_info(self, nightwave_data: NightwaveData) -> str:
        """
        格式化午夜电波信息为精简文本格式

        Args:
            nightwave_data: 午夜电波数据

        Returns:
            格式化的文本
        """
        import re

        lines = []

        # 标题
        lines.append(f"午夜电波 - 赛季{nightwave_data['season']} 阶段{nightwave_data['phase']}")
        lines.append("")

        # 挑战列表（精简格式）
        for idx, challenge in enumerate(nightwave_data['challenges'], 1):
            standing = challenge['standing']
            title = challenge['title']

            # 清理伤害类型标记 (如 <DT_VIRAL>、<DT_IMPACT> 等)
            title = re.sub(r'<DT_\w+>', '', title)

            time_info = f"({challenge['remaining_time']})" if challenge['remaining_time'] else ""

            # 精简格式：序号.[声望+数值] 挑战描述(剩余时间)
            line = f"{idx}.[声望+{standing}] {title}{time_info}"
            lines.append(line)

        return "\n".join(lines)
