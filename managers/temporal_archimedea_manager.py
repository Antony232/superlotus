"""
时光科研(Temporal Archimedea)管理器
处理时光科研任务数据的获取、解析和格式化
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from utils.game_constants import (
    get_mission_type_translation,
    get_mission_variant_translation,
)
from utils.time_utils import format_timestamp, format_remaining_time

logger = logging.getLogger(__name__)


class TemporalArchimedeaManager:
    """时光科研管理器"""

    def __init__(self, translation_manager, game_translator, world_state_fetcher):
        self.translation_manager = translation_manager
        self.game_translator = game_translator
        self.fetch_world_state = world_state_fetcher
        self.zh_translations = self._load_zh_translations()

    def _load_zh_translations(self) -> Dict[str, str]:
        """加载zh.json翻译文件"""
        try:
            zh_path = Path(__file__).parent.parent / 'data' / 'translations' / 'zh.json'
            if zh_path.exists():
                with open(zh_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载zh.json翻译文件失败: {e}")
        return {}

    def get_translation(self, key: str) -> str:
        """获取翻译文本"""
        if key in self.zh_translations:
            return self.zh_translations[key]
        return key

    async def get_temporal_archimedea_info(self) -> Dict[str, Any]:
        """获取时光科研信息"""
        try:
            world_state = await self.fetch_world_state()

            if not world_state:
                return {'success': False, 'error': '无法获取WorldState数据'}

            conquests = world_state.get('Conquests', [])

            if not conquests:
                return {'success': False, 'error': '当前没有时光科研数据'}

            # 查找Type为CT_HEX的Conquest（时光科研）
            ta_conquest = next((c for c in conquests if c.get('Type') == 'CT_HEX'), None)

            if not ta_conquest:
                return {'success': False, 'error': '当前没有时光科研数据'}

            ta_data = {
                'success': True,
                'cycles': [],
                'conquest': ta_conquest
            }

            cycle_data = self._parse_conquest(ta_conquest)
            if cycle_data:
                ta_data['cycles'].append(cycle_data)

            return ta_data

        except Exception as e:
            logger.error(f"获取时光科研信息失败: {e}")
            return {'success': False, 'error': str(e)}

    def _parse_conquest(self, conquest: Dict) -> Optional[Dict[str, Any]]:
        """解析单个Conquest数据"""
        try:
            activation = conquest.get('Activation', {})
            expiry = conquest.get('Expiry', {})

            start_time = activation.get('$date', {}).get('$numberLong', '')
            end_time = expiry.get('$date', {}).get('$numberLong', '')

            start_str = format_timestamp(int(start_time)) if start_time else '未知'
            end_str = format_timestamp(int(end_time)) if end_time else '未知'
            time_left = format_remaining_time(int(end_time)) if end_time else '未知'

            missions = conquest.get('Missions', [])
            mission_list = [self._parse_mission(m) for m in missions if m]
            mission_list = [m for m in mission_list if m]

            variables = conquest.get('Variables', [])

            return {
                'start_time': start_str,
                'end_time': end_str,
                'time_left': time_left,
                'missions': mission_list,
                'variables': variables
            }
        except Exception as e:
            logger.error(f"解析Conquest失败: {e}")
            return None

    def _parse_mission(self, mission: Dict) -> Optional[Dict[str, Any]]:
        """解析单个任务信息"""
        try:
            mission_type = mission.get('missionType', '')
            difficulties = mission.get('difficulties', [])

            mission_type_cn = self._translate_mission_type(mission_type)

            # 提取困难模式的条件
            conditions = []
            hard_diff = next((d for d in difficulties if d.get('type') == 'CD_HARD'), None)

            if hard_diff:
                deviation = hard_diff.get('deviation', '')
                if deviation:
                    conditions.append(self._translate_deviation(deviation))

                for risk in hard_diff.get('risks', []):
                    conditions.append(self._translate_risk(risk))

            return {
                'mission_type': mission_type,
                'mission_type_cn': mission_type_cn,
                'faction': mission.get('faction', ''),
                'conditions': conditions
            }
        except Exception as e:
            logger.error(f"解析任务失败: {e}")
            return None

    def _translate_mission_type(self, mission_type: str) -> str:
        """翻译任务类型"""
        # 时光科研有额外的 DT_ 前缀任务类型
        extra_translations = {
            'DT_EXTERMINATE': '歼灭',
            'DT_SURVIVAL': '生存',
            'DT_DEFENSE': '防御',
            'DT_ALCHEMY': '元素转换',
            'DT_INTERCEPTION': '拦截'
        }
        if mission_type in extra_translations:
            return extra_translations[mission_type]
        return get_mission_type_translation(mission_type)

    def _translate_deviation(self, deviation: str) -> str:
        """翻译变体"""
        keys = [
            f'/Lotus/Language/Conquest/MissionVariant_HexConquest_{deviation}',
            f'/Lotus/Language/Conquest/MissionVariant_LabConquest_{deviation}',
            f'/Lotus/Language/Conquest/Condition_{deviation}'
        ]

        for key in keys:
            result = self.get_translation(key)
            if result != key:
                return result

        # 内置映射
        translations = {
            'ContaminationZone': '屏住呼吸',
            'ExplosiveEnergy': '自爆虫浆',
            'EscalateImmediately': '破坏补给',
            'UnpoweredCapsules': '未通电胶囊',
            'EximusGrenadiers': '卓越者榴弹手',
            'GrowingIncursion': '增兵'
        }
        return translations.get(deviation, deviation)

    def _translate_risk(self, risk: str) -> str:
        """翻译风险条件"""
        key = f'/Lotus/Language/Conquest/Condition_{risk}'
        result = self.get_translation(key)
        if result != key:
            return result

        # 内置映射
        translations = {
            'FactionSwarm_Techrot': '技术腐烂派系蜂群',
            'CompetitionSpillover': '竞争溢出',
            'WinterFrost': '凛冬严寒',
            'Voidburst': '虚空爆发',
            'AcceleratedEnemies': '敌人加速',
            'HeavyWarfare': '重型战争',
            'RegeneratingEnemies': '敌人再生',
            'Quicksand': '流沙',
            'DrainingResiduals': '能量抽吸残留',
            'ExplosiveCrawlers': '爆炸爬行者',
            'AntiMaterialWeapons': '反物质武器',
            'EMPBlackHole': '电磁脉冲黑洞'
        }
        return translations.get(risk, risk)

    def _translate_variable(self, var: str) -> str:
        """翻译个人变量"""
        var_mapping = {
            'Undersupplied': 'MaxAmmo',
            'OverSensitive': 'OverSensitive',
            'VoidEnergyOverload': 'VoidEnergyOverload',
            'DullBlades': 'ComboCountChance',
            'Exhaustion': 'Exhaustion',
            'TimeDilation': 'TimeDilation',
            'Knifestep': 'Knifestep',
            'ShieldDelay': 'ShieldDelay',
            'DecayingFlesh': 'DecayingFlesh',
            'Starvation': 'Starvation',
            'ContactDamage': 'ContactDamage',
            'OperatorLockout': 'OperatorLockout'
        }

        mapped_var = var_mapping.get(var, var)

        keys = [
            f'/Lotus/Language/Conquest/PersonalMod_{mapped_var}',
            f'/Lotus/Language/Conquest/Condition_{mapped_var}'
        ]

        for key in keys:
            result = self.get_translation(key)
            if result != key:
                return result

        translations = {
            'ShieldDelay': '护盾延迟',
            'DecayingFlesh': '腐烂血肉',
            'Starvation': '饥饿',
            'ContactDamage': '接触伤害',
            'OperatorLockout': '指挥官锁定',
            'Undersupplied': '补给短缺',
            'Exhaustion': '力竭'
        }
        return translations.get(var, var)

    def format_temporal_archimedea_message(self, ta_data: Dict[str, Any]) -> str:
        """格式化时光科研信息为可读文本"""
        if not ta_data.get('success'):
            error = ta_data.get('error', '未知错误')
            return f"获取时光科研信息失败: {error}"

        cycles = ta_data.get('cycles', [])

        if not cycles:
            return "当前没有活跃的时光科研周期"

        cycle = cycles[0]
        missions = cycle.get('missions', [])
        variables = cycle.get('variables', [])

        if not missions:
            return "当前没有时光科研任务数据"

        lines = ["【时光科研】"]

        # 收集每个任务的条件
        mission_conditions = [m.get('conditions', [])[:3] for m in missions[:3]]

        # 显示三个任务节点（条件在同一行显示）
        for i, mission in enumerate(missions[:3], 1):
            mission_type = mission.get('mission_type_cn', mission.get('mission_type', '未知'))
            lines.append(f"{i}.{mission_type}")

            conditions = mission_conditions[i-1] if i-1 < len(mission_conditions) else []
            if conditions:
                # 三个条件在同一行显示，用空格分隔
                lines.append("  ".join(conditions))

        # 显示个人变量
        if variables:
            lines.append("【可选风险变量】")
            var_names = [self._translate_variable(v) for v in variables[:4]]
            lines.append("  ".join(var_names))

        return '\n'.join(lines)

    def get_temporal_archimedea_structured(self, ta_data: Dict[str, Any]) -> List[Dict]:
        """
        格式化时光科研信息为结构化数据

        Args:
            ta_data: API返回的时光科研数据

        Returns:
            结构化内容列表，每项为 {"type": "T1-T4", "text": "内容"}
        """
        if not ta_data.get('success'):
            error = ta_data.get('error', '未知错误')
            return [{"type": "T4", "text": f"获取时光科研信息失败: {error}"}]

        cycles = ta_data.get('cycles', [])
        if not cycles:
            return [{"type": "T4", "text": "当前没有活跃的时光科研周期"}]

        cycle = cycles[0]
        missions = cycle.get('missions', [])
        variables = cycle.get('variables', [])

        if not missions:
            return [{"type": "T4", "text": "当前没有时光科研任务数据"}]

        content = []

        # T2: 【时光科研】标题
        content.append({"type": "T2", "text": "【时光科研】"})

        # 收集每个任务的条件
        mission_conditions = [m.get('conditions', [])[:3] for m in missions[:3]]

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

        if variables:
            var_names = [self._translate_variable(v) for v in variables[:4]]
            # T4: 变量列表
            content.append({"type": "T4", "text": "  ".join(var_names)})

        return content


# 全局时光科研管理器实例
ta_manager = None


def get_temporal_archimedea_manager() -> Optional[TemporalArchimedeaManager]:
    """获取TemporalArchimedeaManager实例（懒加载）"""
    global ta_manager

    if ta_manager is not None:
        return ta_manager

    try:
        from managers.translation_manager import TranslationManager, GameStatusTranslator
        from managers.game_status_manager import GameStatusManager

        game_status_manager = GameStatusManager()
        translation_manager = TranslationManager()
        game_translator = GameStatusTranslator()

        translation_manager.load_translations()
        game_translator.load_translations()

        ta_manager = TemporalArchimedeaManager(
            translation_manager=translation_manager,
            game_translator=game_translator,
            world_state_fetcher=game_status_manager.fetch_world_state
        )

        return ta_manager

    except Exception as e:
        logger.error(f"初始化TemporalArchimedeaManager失败: {e}")
        return None
