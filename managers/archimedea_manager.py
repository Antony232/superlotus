"""
深层科研(Archimedea)管理器 - 重构版
继承 BaseConquestManager，消除重复代码
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from managers.base.base_conquest import BaseConquestManager
from core.constants import ARCHIMEDEA_START_DATE, ARCHIMEDEA_CYCLE_WEEKS

logger = logging.getLogger(__name__)


class ArchimedeaManager(BaseConquestManager):
    """深层科研管理器"""
    
    # 个人变量映射
    _VARIABLE_MAPPING = {
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
    
    def _get_conquest_type(self) -> str:
        """
        深层科研使用 CT_LAB 类型，但有些数据没有 Type 字段
        返回 None 表示由 get_conquest_info 的逻辑处理
        """
        return "CT_LAB"
    
    def _get_translation_prefix(self) -> str:
        """返回翻译键前缀"""
        return "LabConquest"
    
    def _get_display_name(self) -> str:
        """获取显示名称"""
        return "深层科研"
    
    def _get_specific_translation_path(self) -> Optional[Path]:
        """获取 Archimedea 专用翻译文件路径"""
        return Path(__file__).parent.parent / 'data' / 'archimedea_tags.json'
    
    def _calculate_week_number(self) -> int:
        """计算当前周数"""
        start_date = datetime(*ARCHIMEDEA_START_DATE)
        now = datetime.now()
        delta = now - start_date
        weeks = delta.days // 7
        return weeks % ARCHIMEDEA_CYCLE_WEEKS
    
    async def get_archimedea_info(self) -> Dict[str, Any]:
        """
        获取深层科研信息（重写以支持周数计算）
        
        注意：深层科研的 Conquest 数据可能没有 Type 字段，
        需要特殊处理
        """
        try:
            world_state = await self.fetch_world_state()
            
            if not world_state:
                return {'success': False, 'error': '无法获取世界状态数据'}
            
            conquests = world_state.get('Conquests', [])
            
            if not conquests:
                return {'success': False, 'error': '当前没有深层科研数据'}
            
            # 查找深层科研数据（有 jobType 字段的）
            archimedea_conquest = None
            for conquest in conquests:
                # 优先匹配 Type 为 CT_LAB
                if conquest.get('Type') == 'CT_LAB':
                    archimedea_conquest = conquest
                    break
                # 回退：匹配有 jobType 但不是 CT_HEX 的
                if conquest.get('jobType') and conquest.get('Type') != 'CT_HEX':
                    archimedea_conquest = conquest
                    break
            
            if not archimedea_conquest:
                return {'success': False, 'error': '当前没有深层科研数据'}
            
            # 解析数据
            current_week = self._calculate_week_number()
            
            data = {
                'success': True,
                'current_week': current_week,
                'cycles': [],
                'conquests': conquests  # 保留原始数据用于提取 Variables
            }
            
            cycle_data = self._parse_conquest(archimedea_conquest)
            if cycle_data:
                data['cycles'].append(cycle_data)
            
            return data
            
        except Exception as e:
            logger.error(f"获取深层科研信息失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _translate_deviation(self, deviation: str) -> str:
        """翻译变体（优先使用 LabConquest 前缀）"""
        if not deviation:
            return ''
        
        # 先尝试 LabConquest 前缀
        key = f'/Lotus/Language/Conquest/MissionVariant_LabConquest_{deviation}'
        result = self.get_translation(key)
        if result != key:
            return result
        
        # 回退到 HexConquest 前缀
        key = f'/Lotus/Language/Conquest/MissionVariant_HexConquest_{deviation}'
        result = self.get_translation(key)
        if result != key:
            return result
        
        # 最后使用通用翻译
        return super()._translate_deviation(deviation)
    
    def _translate_personal_variable(self, var: str) -> tuple:
        """翻译个人变量（可选风险）"""
        if not var:
            return "", ""
        
        mapped_var = self._VARIABLE_MAPPING.get(var, var)
        
        keys = [
            f'/Lotus/Language/Conquest/PersonalMod_{mapped_var}',
            f'/Lotus/Language/Conquest/Condition_{mapped_var}'
        ]
        
        for key in keys:
            name = self.get_translation(key)
            desc = self.get_translation(f'{key}_Desc')
            if name != key:
                return name, desc
        
        return var, ""
    
    def format_archimedea_message(
        self, 
        archimedea_data: Dict[str, Any], 
        conquests: List[Dict] = None
    ) -> str:
        """
        格式化Archimedea信息为可读文本
        
        Args:
            archimedea_data: API返回的科研数据
            conquests: 原始conquests数据（用于提取Variables）
        """
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

        # 提取 Variables
        raw_conquests = conquests if conquests else archimedea_data.get('conquests', [])
        personal_vars = []
        if raw_conquests and len(raw_conquests) > 0:
            personal_vars = raw_conquests[0].get('Variables', [])

        lines = ["【深层科研】"]

        # 收集每个任务的条件
        mission_conditions = []
        for mission in missions[:3]:
            conditions = []
            for diff in mission.get('difficulties', []):
                deviation = diff.get('deviation', '')
                if deviation:
                    var_name = self._translate_deviation(deviation)
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
            lines.append(f"{i}.{mission_type}")

            conditions = mission_conditions[i-1] if i-1 < len(mission_conditions) else []
            if conditions:
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

    def get_archimedea_structured(
        self, 
        archimedea_data: Dict[str, Any], 
        conquests: List[Dict] = None
    ) -> List[Dict]:
        """
        格式化Archimedea信息为结构化数据（用于图片生成）
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

        # 收集每个任务的条件
        mission_conditions = []
        for mission in missions[:3]:
            conditions = []
            for diff in mission.get('difficulties', []):
                deviation = diff.get('deviation', '')
                if deviation:
                    var_name = self._translate_deviation(deviation)
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
            content.append({"type": "T3", "text": f"{i}.{mission_type}"})

            conditions = mission_conditions[i-1] if i-1 < len(mission_conditions) else []
            if conditions:
                content.append({"type": "T4", "text": "  ".join(conditions)})

        # 显示个人变量
        content.append({"type": "T3", "text": "【可选风险变量】"})

        if personal_vars:
            var_names = []
            for var in personal_vars[:4]:
                var_name, _ = self._translate_personal_variable(var)
                var_names.append(var_name if var_name else var)
            content.append({"type": "T4", "text": "  ".join(var_names)})
        else:
            content.append({"type": "T4", "text": "暂无个人变量数据"})

        return content
