"""
深层科研(Archimedea)管理器
处理Archimedea数据的获取、解析和格式化
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from utils.game_constants import (
    get_mission_type_translation,
    get_faction_translation,
    get_difficulty_type_translation,
    get_mission_variant_translation,
)
from utils.time_utils import format_timestamp

logger = logging.getLogger(__name__)


class ArchimedeaManager:
    """Archimedea管理器"""

    def __init__(self, translation_manager, game_translator, world_state_fetcher):
        """
        初始化Archimedea管理器

        Args:
            translation_manager: 物品翻译管理器实例
            game_translator: 游戏状态翻译器实例
            world_state_fetcher: WorldState数据获取函数
        """
        self.translation_manager = translation_manager
        self.game_translator = game_translator
        self.fetch_world_state = world_state_fetcher
        self.archimedea_tags = self._load_archimedea_translations()

    def _load_archimedea_translations(self) -> Dict[str, str]:
        """加载Archimedea专用翻译文件"""
        try:
            tags_path = Path(__file__).parent.parent / 'data' / 'archimedea_tags.json'
            if tags_path.exists():
                with open(tags_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载Archimedea翻译文件失败: {e}")
        return {}

    def get_translation(self, key: str) -> str:
        """
        获取翻译文本

        Args:
            key: 翻译键

        Returns:
            翻译文本，如果找不到则返回原始键
        """
        # 优先使用Archimedea专用翻译
        if key in self.archimedea_tags:
            return self.archimedea_tags[key]

        # 回退到游戏状态翻译器
        if self.game_translator:
            return self.game_translator.translate_text(key)

        return key

    def _calculate_week_number(self, start_date: datetime) -> int:
        """计算从起始日期开始的周数"""
        now = datetime.now()
        delta = now - start_date
        weeks = delta.days // 7
        return weeks % 8  # Archimedea周期为8周

    async def get_archimedea_info(self) -> Dict[str, Any]:
        """获取Archimedea信息"""
        try:
            world_state = await self.fetch_world_state()

            if not world_state:
                return {'success': False, 'error': '无法获取WorldState数据'}

            conquests = world_state.get('Conquests', [])

            if not conquests:
                return {'success': False, 'error': '当前没有Archimedea数据'}

            start_date = datetime(2024, 11, 26)
            current_week = self._calculate_week_number(start_date)

            archimedea_data = {
                'success': True,
                'current_week': current_week,
                'cycles': [],
                'conquests': conquests
            }

            for conquest in conquests:
                cycle_data = self._parse_conquest(conquest)
                if cycle_data:
                    archimedea_data['cycles'].append(cycle_data)

            return archimedea_data

        except Exception as e:
            logger.error(f"获取Archimedea信息失败: {e}")
            return {'success': False, 'error': str(e)}

    def _parse_conquest(self, conquest: Dict) -> Optional[Dict[str, Any]]:
        """解析单个Conquest数据"""
        try:
            job_type = conquest.get('jobType', '')
            activation = conquest.get('Activation', {})
            expiry = conquest.get('Expiry', {})

            start_time = activation.get('$date', {}).get('$numberLong', '')
            end_time = expiry.get('$date', {}).get('$numberLong', '')

            start_str = format_timestamp(int(start_time)) if start_time else '未知'
            end_str = format_timestamp(int(end_time)) if end_time else '未知'

            missions = conquest.get('Missions', [])
            mission_list = [self._parse_mission(m) for m in missions if m]
            mission_list = [m for m in mission_list if m]

            return {
                'job_type': job_type,
                'region': conquest.get('RegionTag', ''),
                'start_time': start_str,
                'end_time': end_str,
                'missions': mission_list
            }

        except Exception as e:
            logger.error(f"解析Conquest失败: {e}")
            return None

    def _parse_mission(self, mission: Dict) -> Optional[Dict[str, Any]]:
        """解析任务信息"""
        try:
            mission_type = mission.get('missionType', '')
            faction = mission.get('faction', '')
            difficulties = mission.get('difficulties', [])

            difficulty_list = []
            for diff in difficulties:
                diff_info = {
                    'type': diff.get('type', ''),
                    'type_cn': get_difficulty_type_translation(diff.get('type', '')),
                    'deviation': diff.get('deviation', ''),
                    'deviation_cn': get_mission_variant_translation(diff.get('deviation', '')),
                    'risks': []
                }

                for risk in diff.get('risks', []):
                    risk_tag = risk
                    condition_name = self.get_translation(f'/Lotus/Language/Conquest/Condition_{risk_tag}')
                    condition_desc = self.get_translation(f'/Lotus/Language/Conquest/Condition_{risk_tag}_Desc')

                    diff_info['risks'].append({
                        'tag': risk_tag,
                        'name': condition_name,
                        'description': condition_desc
                    })

                difficulty_list.append(diff_info)

            return {
                'mission_type': mission_type,
                'mission_type_cn': get_mission_type_translation(mission_type),
                'faction': faction,
                'faction_cn': get_faction_translation(faction),
                'difficulties': difficulty_list
            }

        except Exception as e:
            logger.error(f"解析任务失败: {e}")
            return None

    def _translate_mission_variant(self, variant_tag: str) -> tuple:
        """翻译任务变体（偏差）"""
        if not variant_tag:
            return "", ""

        name = self.get_translation(f'/Lotus/Language/Conquest/MissionVariant_LabConquest_{variant_tag}')
        desc = self.get_translation(f'/Lotus/Language/Conquest/MissionVariant_LabConquest_{variant_tag}_Desc')

        if name and name != variant_tag:
            return name, desc

        name = self.get_translation(f'/Lotus/Language/Conquest/MissionVariant_HexConquest_{variant_tag}')
        desc = self.get_translation(f'/Lotus/Language/Conquest/MissionVariant_HexConquest_{variant_tag}_Desc')

        if name and name != variant_tag:
            return name, desc

        return variant_tag, ""

    def _translate_personal_variable(self, var_tag: str) -> tuple:
        """翻译个人变量（可选风险）"""
        if not var_tag:
            return "", ""

        # 可选风险使用 PersonalMod_ 前缀
        name = self.get_translation(f'/Lotus/Language/Conquest/PersonalMod_{var_tag}')
        desc = self.get_translation(f'/Lotus/Language/Conquest/PersonalMod_{var_tag}_Desc')

        if name and name != var_tag:
            return name, desc

        # 回退尝试 Condition_ 前缀
        name = self.get_translation(f'/Lotus/Language/Conquest/Condition_{var_tag}')
        desc = self.get_translation(f'/Lotus/Language/Conquest/Condition_{var_tag}_Desc')

        if name and name != var_tag:
            return name, desc

        return var_tag, ""

    def format_archimedea_message(self, archimedea_data: Dict[str, Any], conquests: List[Dict] = None) -> str:
        """格式化Archimedea信息为可读文本"""
        if not archimedea_data.get('success'):
            error = archimedea_data.get('error', '未知错误')
            return f"获取深层科研信息失败: {error}"

        cycles = archimedea_data.get('cycles', [])

        if not cycles:
            return "当前没有活跃的深层科研周期"

        cycle = cycles[0]
        missions = cycle.get('missions', [])

        if not missions:
            return "当前没有深层科研任务数据"

        raw_conquests = conquests if conquests else archimedea_data.get('conquests', [])
        personal_vars = []
        if raw_conquests and len(raw_conquests) > 0:
            personal_vars = raw_conquests[0].get('Variables', [])

        lines = ["【深层科研】"]

        # 收集每个任务的条件名称
        mission_conditions = []
        for mission in missions[:3]:
            conditions = []
            for diff in mission.get('difficulties', []):
                deviation = diff.get('deviation', '')
                if deviation:
                    var_name, _ = self._translate_mission_variant(deviation)
                    if var_name and var_name not in conditions:
                        conditions.append(var_name)

                for risk in diff.get('risks', []):
                    risk_name = risk.get('name', '')
                    if risk_name and risk_name != risk.get('tag', '') and risk_name not in conditions:
                        conditions.append(risk_name)

            mission_conditions.append(conditions[:3])

        # 显示三个任务节点（条件在同一行显示）
        for i, mission in enumerate(missions[:3], 1):
            mission_type = mission.get('mission_type_cn', mission.get('mission_type', '未知'))
            lines.append(f"{i}.{mission_type}")

            conditions = mission_conditions[i-1] if i-1 < len(mission_conditions) else []
            if conditions:
                # 三个条件在同一行显示，用空格分隔
                lines.append("  ".join(conditions))

        # 显示个人变量
        if personal_vars:
            lines.append("【可选风险变量】")
            var_names = []
            for var in personal_vars[:4]:
                var_name, _ = self._translate_personal_variable(var)
                var_names.append(var_name if var_name else var)
            lines.append("  ".join(var_names))
        else:
            lines.extend(["【可选风险变量】", "暂无个人变量数据"])

        return '\n'.join(lines)

    def get_archimedea_structured(self, archimedea_data: Dict[str, Any], conquests: List[Dict] = None) -> List[Dict]:
        """
        格式化Archimedea信息为结构化数据

        Args:
            archimedea_data: API返回的科研数据
            conquests: 原始conquests数据

        Returns:
            结构化内容列表，每项为 {"type": "T1-T4", "text": "内容"}
        """
        if not archimedea_data.get('success'):
            error = archimedea_data.get('error', '未知错误')
            return [{"type": "T4", "text": f"获取深层科研信息失败: {error}"}]

        cycles = archimedea_data.get('cycles', [])
        if not cycles:
            return [{"type": "T4", "text": "当前没有活跃的深层科研周期"}]

        cycle = cycles[0]
        missions = cycle.get('missions', [])
        if not missions:
            return [{"type": "T4", "text": "当前没有深层科研任务数据"}]

        raw_conquests = conquests if conquests else archimedea_data.get('conquests', [])
        personal_vars = []
        if raw_conquests and len(raw_conquests) > 0:
            personal_vars = raw_conquests[0].get('Variables', [])

        content = []

        # T2: 【深层科研】标题
        content.append({"type": "T2", "text": "【深层科研】"})

        # 收集每个任务的条件名称
        mission_conditions = []
        for mission in missions[:3]:
            conditions = []
            for diff in mission.get('difficulties', []):
                deviation = diff.get('deviation', '')
                if deviation:
                    var_name, _ = self._translate_mission_variant(deviation)
                    if var_name and var_name not in conditions:
                        conditions.append(var_name)

                for risk in diff.get('risks', []):
                    risk_name = risk.get('name', '')
                    if risk_name and risk_name != risk.get('tag', '') and risk_name not in conditions:
                        conditions.append(risk_name)

            mission_conditions.append(conditions[:3])

        # 显示三个任务节点
        for i, mission in enumerate(missions[:3], 1):
            mission_type = mission.get('mission_type_cn', mission.get('mission_type', '未知'))
            # T3: 任务行
            content.append({"type": "T3", "text": f"{i}.{mission_type}"})

            conditions = mission_conditions[i-1] if i-1 < len(mission_conditions) else []
            if conditions:
                # T4: 条件行
                content.append({"type": "T4", "text": "  ".join(conditions)})

        # 显示个人变量
        content.append({"type": "T3", "text": "【可选风险变量】"})

        if personal_vars:
            var_names = []
            for var in personal_vars[:4]:
                var_name, _ = self._translate_personal_variable(var)
                var_names.append(var_name if var_name else var)
            # T4: 变量列表
            content.append({"type": "T4", "text": "  ".join(var_names)})
        else:
            content.append({"type": "T4", "text": "暂无个人变量数据"})

        return content
