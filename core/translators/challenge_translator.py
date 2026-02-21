"""
挑战翻译器 - 午夜电波挑战翻译模块
仅处理午夜电波的挑战翻译
"""

import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class ChallengeTranslator:
    """挑战翻译器类 - 仅处理午夜电波挑战翻译"""

    def __init__(self):
        self._translations_cache: Optional[Dict[str, Any]] = None
        self._challenges_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None

    def load_data(self) -> None:
        """加载翻译数据"""
        try:
            # 加载 zh.json 翻译（包含 NightwaveChallenges 的翻译）
            with open('data/translations/zh.json', 'r', encoding='utf-8') as f:
                self._translations_cache = json.load(f)

            # 加载挑战数据
            with open('data/game_data/ExportChallenges.json', 'r', encoding='utf-8') as f:
                self._challenges_cache = json.load(f)

            self._cache_timestamp = datetime.now(timezone.utc)
            logger.info("挑战翻译器数据加载成功")

        except Exception as e:
            logger.error(f"加载挑战翻译数据失败: {e}")
            self._translations_cache = {}
            self._challenges_cache = {}

    def translate_challenge(self, challenge_id: str) -> Optional[str]:
        """
        翻译午夜电波挑战描述

        翻译流程：
        1. worldState.json challenge ID → ExportChallenges.json 键
        2. ExportChallenges.json 获取 name 字段（翻译键）
        3. 将 name 字段的 _Name 替换为 _Description
        4. 从 zh.json 获取 _Description 的翻译
        5. 使用 ExportChallenges.json 中的 requiredCount 替换 |COUNT|

        Args:
            challenge_id: 挑战ID（如 /Lotus/Types/Challenges/DailyChallenge_CompleteAnyMission）

        Returns:
            翻译后的挑战描述，如果失败返回None
        """
        if not self._challenges_cache or not self._translations_cache:
            self.load_data()

        try:
            # 将 worldState ID 映射到 ExportChallenges.json 的键
            export_key = self._map_to_export_key(challenge_id)

            if not export_key:
                logger.warning(f"无法映射挑战ID: {challenge_id}")
                return self._fallback_translation(challenge_id)

            # 从 ExportChallenges.json 获取挑战数据
            if export_key not in self._challenges_cache:
                logger.warning(f"ExportChallenges.json 中未找到键: {export_key}")
                return self._fallback_translation(challenge_id)

            challenge_data = self._challenges_cache[export_key]
            if not isinstance(challenge_data, dict):
                return self._fallback_translation(challenge_id)

            # 获取 name 翻译键（如 /Lotus/Language/NightwaveChallenges/Challenge_SeasonDailyCompleteMission_Name）
            name_key = challenge_data.get('name', '')
            if not name_key or not isinstance(name_key, str):
                return self._fallback_translation(challenge_id)

            # 将 _Name 替换为 _Description，获取描述翻译键
            if not name_key.endswith('_Name'):
                logger.warning(f"name 字段格式不正确: {name_key}")
                return self._fallback_translation(challenge_id)

            desc_key = name_key.replace('_Name', '_Description')

            # 从 zh.json 获取实际翻译
            if desc_key not in self._translations_cache:
                logger.warning(f"zh.json 中未找到翻译键: {desc_key}")
                return self._fallback_translation(challenge_id)

            translation = self._translations_cache[desc_key]

            # 替换 |COUNT| 占位符（使用 ExportChallenges.json 中的 requiredCount）
            required_count = challenge_data.get('requiredCount', 0)
            if required_count > 0 and '|COUNT|' in translation:
                translation = translation.replace('|COUNT|', str(required_count))

            return translation

        except Exception as e:
            logger.error(f"翻译挑战失败 {challenge_id}: {e}", exc_info=True)
            return self._fallback_translation(challenge_id)

    def translate_challenge_with_standing(self, challenge_id: str) -> tuple[Optional[str], int]:
        """
        翻译午夜电波挑战描述并获取声望值

        Args:
            challenge_id: 挑战ID

        Returns:
            (翻译后的挑战描述, 声望值)，如果失败返回 (None, 0)
        """
        if not self._challenges_cache or not self._translations_cache:
            self.load_data()

        try:
            # 将 worldState ID 映射到 ExportChallenges.json 的键
            export_key = self._map_to_export_key(challenge_id)

            if not export_key:
                logger.warning(f"无法映射挑战ID: {challenge_id}")
                return (self._fallback_translation(challenge_id), 0)

            # 从 ExportChallenges.json 获取挑战数据
            if export_key not in self._challenges_cache:
                logger.warning(f"ExportChallenges.json 中未找到键: {export_key}")
                return (self._fallback_translation(challenge_id), 0)

            challenge_data = self._challenges_cache[export_key]
            if not isinstance(challenge_data, dict):
                return (self._fallback_translation(challenge_id), 0)

            # 获取声望值
            standing = challenge_data.get('standing', 0)

            # 获取 name 翻译键
            name_key = challenge_data.get('name', '')
            if not name_key or not isinstance(name_key, str):
                return (self._fallback_translation(challenge_id), standing)

            # 将 _Name 替换为 _Description
            if not name_key.endswith('_Name'):
                logger.warning(f"name 字段格式不正确: {name_key}")
                return (self._fallback_translation(challenge_id), standing)

            desc_key = name_key.replace('_Name', '_Description')

            # 从 zh.json 获取实际翻译
            if desc_key not in self._translations_cache:
                logger.warning(f"zh.json 中未找到翻译键: {desc_key}")
                return (self._fallback_translation(challenge_id), standing)

            translation = self._translations_cache[desc_key]

            # 替换 |COUNT| 占位符
            required_count = challenge_data.get('requiredCount', 0)
            if required_count > 0 and '|COUNT|' in translation:
                translation = translation.replace('|COUNT|', str(required_count))

            return (translation, standing)

        except Exception as e:
            logger.error(f"翻译挑战失败 {challenge_id}: {e}", exc_info=True)
            return (self._fallback_translation(challenge_id), 0)

    def _normalize_challenge_key(self, challenge_id: str) -> str:
        """
        标准化challenge键，用于匹配ExportChallenges.json
        例如：/Lotus/Types/Challenges/Zariman/ZarimanUseVoidRiftsEasyChallenge
        保持原样，不去除Easy等后缀
        """
        return challenge_id

    def _get_translation_key(self, challenge_path: str) -> str:
        """
        获取翻译键，用于匹配zh.json（赏金任务方式）
        例如：
        输入：/Lotus/Types/Challenges/Zariman/ZarimanUseVoidRiftsEasyChallenge
        输出：/Lotus/Language/Challenges/Challenge_ZarimanUseVoidRiftsChallenge_Desc

        规则：
        1. 将 /Types/ 改为 /Language/
        2. 在路径前加 Challenge_
        3. 去除Easy/Medium/Hard等难度后缀（如果有）
        4. 在末尾添加 _Desc 后缀
        """
        parts = challenge_path.split('/')
        filename = parts[-1]  # 最后部分：ZarimanUseVoidRiftsEasyChallenge

        # 去除难度后缀
        difficulty_suffixes = ['Easy', 'Medium', 'Hard', 'VeryHard', 'Normal', 'Tier1', 'Tier2', 'Tier3']
        for suffix in difficulty_suffixes:
            if filename.endswith(suffix):
                filename = filename[:-len(suffix)]
                break

        # 转换为翻译键格式
        translation_key = f"/Lotus/Language/Challenges/Challenge_{filename}_Desc"
        return translation_key

    def _map_to_export_key(self, challenge_id: str) -> Optional[str]:
        """
        将 worldState.json 的挑战ID映射到 ExportChallenges.json 的键

        新版 API（SeasonInfo.ActiveChallenges）：
        - 直接使用挑战 ID，如 /Lotus/Types/Challenges/Seasons/Daily/SeasonDailyKillEnemiesWithViral

        旧版 API（worldState.SeasonInfo）：
        - worldState.json: /Lotus/Types/Challenges/DailyChallenge_CompleteAnyMission
        - ExportChallenges.json: /Lotus/Types/Challenges/Seasons/Daily/SeasonDailyCompleteMission

        Calendar1999 挑战：
        - 直接使用完整 ID，如 /Lotus/Types/Challenges/Calendar1999/CalendarKillTechrotEnemiesWithAbilitiesMedium
        - ExportChallenges.json 中键与 ID 完全一致
        """
        # 如果 ID 已经是 Seasons/Calendar1999/Zariman/Hex 格式，直接返回
        if any(prefix in challenge_id for prefix in ['/Seasons/', '/Calendar1999/', '/Zariman/', '/Hex/']):
            return challenge_id

        # 旧版 API 映射规则
        # 预定义的映射字典（解决名称不一致的问题）
        WORLDSTATE_TO_EXPORT_MAP = {
            # 日常挑战
            '/Lotus/Types/Challenges/DailyChallenge_CompleteAnyMission': '/Lotus/Types/Challenges/Seasons/Daily/SeasonDailyCompleteMission',

            # 周常挑战
            '/Lotus/Types/Challenges/WeeklyChallenge_KillEnemies': '/Lotus/Types/Challenges/Seasons/Weekly/SeasonWeeklyKillEnemies',
            '/Lotus/Types/Challenges/WeeklyChallenge_CompleteSpyMissions': '/Lotus/Types/Challenges/Seasons/Weekly/SeasonWeeklyCompleteSpy',

            # 精英周常挑战 (注意：精英挑战也使用 SeasonWeekly，不是 SeasonElite)
            '/Lotus/Types/Challenges/WeeklyEliteChallenge_CompleteSorties': '/Lotus/Types/Challenges/Seasons/Weekly/SeasonWeeklyCompleteSortie',
        }

        # 优先使用预定义映射
        if challenge_id in WORLDSTATE_TO_EXPORT_MAP:
            return WORLDSTATE_TO_EXPORT_MAP[challenge_id]

        try:
            # 移除前缀，获取挑战名称
            if not challenge_id.startswith('/Lotus/Types/Challenges/'):
                return None

            challenge_name = challenge_id.replace('/Lotus/Types/Challenges/', '')

            # 通用映射规则
            if challenge_name.startswith('DailyChallenge_'):
                name_part = challenge_name.replace('DailyChallenge_', '')
                return f"/Lotus/Types/Challenges/Seasons/Daily/SeasonDaily{name_part}"
            elif challenge_name.startswith('WeeklyChallenge_'):
                name_part = challenge_name.replace('WeeklyChallenge_', '')
                return f"/Lotus/Types/Challenges/Seasons/Weekly/SeasonWeekly{name_part}"
            elif challenge_name.startswith('WeeklyEliteChallenge_'):
                name_part = challenge_name.replace('WeeklyEliteChallenge_', '')
                return f"/Lotus/Types/Challenges/Seasons/Weekly/SeasonElite{name_part}"

            return None

        except Exception as e:
            logger.error(f"映射挑战ID失败 {challenge_id}: {e}")
            return None

    def _extract_translation(self, challenge_id: str, challenge_type: str) -> Optional[str]:
        """从挑战数据中提取翻译"""
        if not self._challenges_cache:
            return None

        # 直接查找
        if challenge_id in self._challenges_cache:
            challenge_data = self._challenges_cache[challenge_id]
            if isinstance(challenge_data, dict):
                # 尝试获取中文翻译
                if 'name' in challenge_data:
                    name = challenge_data['name']
                    if isinstance(name, dict) and 'zh' in name:
                        return name['zh']
                    elif isinstance(name, str):
                        # 检查是否在物品翻译中
                        if self._translations_cache and name in self._translations_cache:
                            return self._translations_cache[name]
                        return name

        return None

    def _replace_count_placeholder(self, translation: str, challenge_id: str) -> str:
        """替换 |COUNT| 占位符"""
        # 从挑战ID中提取数量（如果存在）
        count_match = re.search(r'(\d+)', challenge_id)
        if count_match and '|COUNT|' in translation:
            count = count_match.group(1)
            translation = translation.replace('|COUNT|', count)

        return translation

    def _fallback_translation(self, challenge_id: str) -> Optional[str]:
        """回退翻译方案 - 实现完整的回退逻辑"""
        try:
            # 从ID中提取最后一部分
            parts = challenge_id.split('/')
            if not parts:
                return challenge_id

            simple_name = parts[-1]

            # 移除常见前缀
            prefixes = ['DailyChallenge_', 'WeeklyChallenge_', 'WeeklyEliteChallenge_']
            for prefix in prefixes:
                if simple_name.startswith(prefix):
                    simple_name = simple_name[len(prefix):]
                    break

            # 移除常见后缀
            suffixes = ['Challenge', 'Easy', 'Medium', 'Hard', 'VeryHard', 'Normal', 'Tier1', 'Tier2', 'Tier3']
            for suffix in suffixes:
                if simple_name.endswith(suffix):
                    simple_name = simple_name[:-len(suffix)]
                    break

            # 分割驼峰命名
            spaced_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', simple_name)
            spaced_name = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', spaced_name)

            # 检查是否在翻译缓存中
            if self._translations_cache and spaced_name in self._translations_cache:
                return self._translations_cache[spaced_name]

            # 返回处理后的名称
            return spaced_name

        except Exception as e:
            logger.error(f"回退翻译失败 {challenge_id}: {e}")
            return challenge_id

    def format_remaining_time(self, expiry_timestamp: Optional[int] = None) -> str:
        """
        格式化剩余时间

        Args:
            expiry_timestamp: 到期时间戳（毫秒）

        Returns:
            格式化的剩余时间字符串，如"剩余6天12小时"
        """
        if not expiry_timestamp:
            return ""

        try:
            # 转换毫秒到秒
            expiry_time = datetime.fromtimestamp(expiry_timestamp / 1000, tz=timezone.utc)
            now = datetime.now(timezone.utc)

            time_diff = expiry_time - now

            if time_diff.total_seconds() <= 0:
                return "已过期"

            days = time_diff.days
            hours = time_diff.seconds // 3600

            if days > 0:
                if hours > 0:
                    return f"剩余{days}天{hours}小时"
                else:
                    return f"剩余{days}天"
            elif hours > 0:
                return f"剩余{hours}小时"
            else:
                minutes = (time_diff.seconds // 60) % 60
                return f"剩余{minutes}分钟"

        except Exception as e:
            logger.error(f"格式化剩余时间失败: {e}")
            return ""
