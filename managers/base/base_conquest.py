"""
Conquest 解析基类
消除 archimedea_manager, kahl_manager, temporal_archimedea_manager 中的重复代码
"""
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from utils.time_utils import format_timestamp, format_remaining_time
from utils.game_constants import (
    get_mission_type_translation,
    get_faction_translation,
    get_difficulty_type_translation,
    get_mission_variant_translation,
)

logger = logging.getLogger(__name__)


class BaseConquestManager(ABC):
    """
    科研任务解析基类
    
    统一处理 Conquest 数据的解析逻辑，子类只需实现：
    1. _get_conquest_type() - 返回 Conquest 类型标识
    2. _get_translation_prefix() - 返回翻译键前缀
    """
    
    def __init__(
        self,
        translation_manager=None,
        game_translator=None,
        world_state_fetcher: Optional[Callable] = None
    ):
        """
        初始化基类
        
        Args:
            translation_manager: 物品翻译管理器
            game_translator: 游戏状态翻译器
            world_state_fetcher: 世界状态获取函数
        """
        self.translation_manager = translation_manager
        self.game_translator = game_translator
        self.fetch_world_state = world_state_fetcher
        self._translations = self._load_translations()
    
    def _load_translations(self) -> Dict[str, str]:
        """加载翻译文件"""
        translations = {}
        
        # 加载 zh.json
        try:
            zh_path = Path(__file__).parent.parent.parent / 'data' / 'translations' / 'zh.json'
            if zh_path.exists():
                with open(zh_path, 'r', encoding='utf-8') as f:
                    translations.update(json.load(f))
        except Exception as e:
            logger.warning(f"加载 zh.json 失败: {e}")
        
        # 加载特定类型的翻译文件（如 archimedea_tags.json）
        specific_path = self._get_specific_translation_path()
        if specific_path:
            try:
                if specific_path.exists():
                    with open(specific_path, 'r', encoding='utf-8') as f:
                        translations.update(json.load(f))
            except Exception as e:
                logger.warning(f"加载特定翻译文件失败: {e}")
        
        return translations
    
    def _get_specific_translation_path(self) -> Optional[Path]:
        """获取特定翻译文件路径，子类可重写"""
        return None
    
    def get_translation(self, key: str) -> str:
        """获取翻译文本"""
        if key in self._translations:
            return self._translations[key]
        
        # 回退到游戏状态翻译器
        if self.game_translator:
            result = self.game_translator.translate_text(key)
            if result != key:
                return result
        
        return key
    
    @abstractmethod
    def _get_conquest_type(self) -> str:
        """
        返回 Conquest 类型标识
        
        Returns:
            类型标识，如 "CT_LAB"（深层科研）或 "CT_HEX"（时光科研）
        """
        pass
    
    @abstractmethod
    def _get_translation_prefix(self) -> str:
        """
        返回翻译键前缀
        
        Returns:
            前缀，如 "LabConquest" 或 "HexConquest"
        """
        pass
    
    async def get_conquest_info(self) -> Dict[str, Any]:
        """
        获取科研信息（通用实现）
        
        Returns:
            包含科研信息的字典
        """
        try:
            world_state = await self.fetch_world_state()
            
            if not world_state:
                return {'success': False, 'error': '无法获取世界状态数据'}
            
            conquests = world_state.get('Conquests', [])
            
            if not conquests:
                return {'success': False, 'error': '当前没有科研数据'}
            
            # 查找指定类型的 Conquest
            conquest_type = self._get_conquest_type()
            target_conquest = None
            
            for conquest in conquests:
                if conquest.get('Type') == conquest_type:
                    target_conquest = conquest
                    break
                # 对于深层科研，可能没有 Type 字段
                if conquest_type is None and conquest.get('jobType'):
                    target_conquest = conquest
                    break
            
            if not target_conquest:
                return {'success': False, 'error': f'当前没有 {self._get_display_name()} 数据'}
            
            # 解析数据
            data = {
                'success': True,
                'cycles': [],
                'conquest': target_conquest
            }
            
            cycle_data = self._parse_conquest(target_conquest)
            if cycle_data:
                data['cycles'].append(cycle_data)
            
            return data
            
        except Exception as e:
            logger.error(f"获取科研信息失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_display_name(self) -> str:
        """获取显示名称，子类可重写"""
        return "科研任务"
    
    def _parse_conquest(self, conquest: Dict) -> Optional[Dict[str, Any]]:
        """
        解析单个 Conquest 数据（通用实现）
        
        Args:
            conquest: Conquest 数据对象
            
        Returns:
            解析后的信息字典
        """
        try:
            # 解析时间
            activation = conquest.get('Activation', {})
            expiry = conquest.get('Expiry', {})
            
            start_time = activation.get('$date', {}).get('$numberLong', '')
            end_time = expiry.get('$date', {}).get('$numberLong', '')
            
            start_str = format_timestamp(int(start_time)) if start_time else '未知'
            end_str = format_timestamp(int(end_time)) if end_time else '未知'
            time_left = format_remaining_time(int(end_time)) if end_time else '未知'
            
            # 解析任务
            missions = conquest.get('Missions', [])
            mission_list = [self._parse_mission(m) for m in missions if m]
            mission_list = [m for m in mission_list if m]
            
            # 解析个人变量
            variables = conquest.get('Variables', [])
            
            return {
                'start_time': start_str,
                'end_time': end_str,
                'time_left': time_left,
                'missions': mission_list,
                'variables': variables,
                'job_type': conquest.get('jobType', ''),
                'region': conquest.get('RegionTag', '')
            }
            
        except Exception as e:
            logger.error(f"解析 Conquest 失败: {e}")
            return None
    
    def _parse_mission(self, mission: Dict) -> Optional[Dict[str, Any]]:
        """
        解析任务信息（通用实现）
        
        Args:
            mission: 任务数据对象
            
        Returns:
            解析后的任务信息
        """
        try:
            mission_type = mission.get('missionType', '')
            faction = mission.get('faction', '')
            difficulties = mission.get('difficulties', [])
            
            # 翻译任务类型
            mission_type_cn = self._translate_mission_type(mission_type)
            faction_cn = get_faction_translation(faction) if faction else ''
            
            # 解析难度和条件
            difficulty_list = []
            conditions = []
            
            for diff in difficulties:
                diff_info = self._parse_difficulty(diff)
                if diff_info:
                    difficulty_list.append(diff_info)
                
                # 收集条件（用于显示）
                deviation = diff.get('deviation', '')
                if deviation:
                    var_name = self._translate_deviation(deviation)
                    if var_name and var_name not in conditions:
                        conditions.append(var_name)
                
                for risk in diff.get('risks', []):
                    risk_name = self._translate_risk(risk)
                    if risk_name and risk_name not in conditions:
                        conditions.append(risk_name)
            
            return {
                'mission_type': mission_type,
                'mission_type_cn': mission_type_cn,
                'faction': faction,
                'faction_cn': faction_cn,
                'difficulties': difficulty_list,
                'conditions': conditions[:5]  # 限制条件数量
            }
            
        except Exception as e:
            logger.error(f"解析任务失败: {e}")
            return None
    
    def _parse_difficulty(self, diff: Dict) -> Optional[Dict[str, Any]]:
        """解析难度信息"""
        try:
            diff_type = diff.get('type', '')
            deviation = diff.get('deviation', '')
            
            diff_info = {
                'type': diff_type,
                'type_cn': get_difficulty_type_translation(diff_type),
                'deviation': deviation,
                'deviation_cn': self._translate_deviation(deviation) if deviation else '',
                'risks': []
            }
            
            for risk in diff.get('risks', []):
                risk_info = self._translate_risk_full(risk)
                diff_info['risks'].append(risk_info)
            
            return diff_info
            
        except Exception as e:
            logger.error(f"解析难度失败: {e}")
            return None
    
    def _translate_mission_type(self, mission_type: str) -> str:
        """翻译任务类型"""
        # 先尝试通用翻译
        result = get_mission_type_translation(mission_type)
        if result != mission_type:
            return result
        
        # 尝试特定翻译
        return self.get_translation(f'/Lotus/Language/Conquest/MissionType_{mission_type}')
    
    def _translate_deviation(self, deviation: str) -> str:
        """翻译变体/偏差"""
        if not deviation:
            return ''
        
        prefix = self._get_translation_prefix()
        
        # 尝试特定前缀
        keys = [
            f'/Lotus/Language/Conquest/MissionVariant_{prefix}_{deviation}',
            f'/Lotus/Language/Conquest/MissionVariant_{deviation}',
        ]
        
        for key in keys:
            result = self.get_translation(key)
            if result != key:
                return result
        
        return get_mission_variant_translation(deviation)
    
    def _translate_risk(self, risk: str) -> str:
        """翻译风险条件（仅名称）"""
        if not risk:
            return ''
        
        key = f'/Lotus/Language/Conquest/Condition_{risk}'
        result = self.get_translation(key)
        
        if result != key:
            return result
        
        # 回退到通用翻译
        return get_mission_variant_translation(risk)
    
    def _translate_risk_full(self, risk: str) -> Dict[str, str]:
        """翻译风险条件（完整信息）"""
        return {
            'tag': risk,
            'name': self._translate_risk(risk),
            'description': self.get_translation(f'/Lotus/Language/Conquest/Condition_{risk}_Desc')
        }
    
    def _translate_variable(self, var: str) -> str:
        """翻译个人变量"""
        if not var:
            return ''
        
        # 变量映射
        var_mapping = getattr(self, '_VARIABLE_MAPPING', {})
        mapped_var = var_mapping.get(var, var)
        
        keys = [
            f'/Lotus/Language/Conquest/PersonalMod_{mapped_var}',
            f'/Lotus/Language/Conquest/Condition_{mapped_var}',
            f'/Lotus/Language/Conquest/PersonalMod_{var}',
        ]
        
        for key in keys:
            result = self.get_translation(key)
            if result != key:
                return result
        
        return var
    
    def format_conquest_message(self, data: Dict[str, Any], title: str = "科研任务") -> str:
        """
        格式化科研信息为可读文本（通用实现）
        
        Args:
            data: 科研数据
            title: 标题文本
            
        Returns:
            格式化后的文本消息
        """
        if not data.get('success'):
            error = data.get('error', '未知错误')
            return f"获取{title}信息失败: {error}"
        
        cycles = data.get('cycles', [])
        if not cycles:
            return f"当前没有活跃的{title}周期"
        
        cycle = cycles[0]
        missions = cycle.get('missions', [])
        variables = cycle.get('variables', [])
        
        if not missions:
            return f"当前没有{title}任务数据"
        
        lines = [f"【{title}】"]
        
        # 收集每个任务的条件
        mission_conditions = [m.get('conditions', [])[:3] for m in missions[:3]]
        
        # 显示三个任务节点
        for i, mission in enumerate(missions[:3], 1):
            mission_type = mission.get('mission_type_cn', mission.get('mission_type', '未知'))
            lines.append(f"{i}.{mission_type}")
            
            conditions = mission_conditions[i-1] if i-1 < len(mission_conditions) else []
            if conditions:
                lines.append("  ".join(conditions))
        
        # 显示个人变量
        if variables:
            lines.append("【可选风险变量】")
            var_names = [self._translate_variable(v) for v in variables[:4]]
            lines.append("  ".join(var_names))
        
        return '\n'.join(lines)
    
    def get_conquest_structured(
        self,
        data: Dict[str, Any],
        title: str = "科研任务"
    ) -> List[Dict]:
        """
        格式化科研信息为结构化数据（用于图片生成）
        
        Args:
            data: 科研数据
            title: 标题文本
            
        Returns:
            结构化内容列表
        """
        if not data.get('success'):
            error = data.get('error', '未知错误')
            return [{"type": "T4", "text": f"获取{title}信息失败: {error}"}]
        
        cycles = data.get('cycles', [])
        if not cycles:
            return [{"type": "T4", "text": f"当前没有活跃的{title}周期"}]
        
        cycle = cycles[0]
        missions = cycle.get('missions', [])
        variables = cycle.get('variables', [])
        
        if not missions:
            return [{"type": "T4", "text": f"当前没有{title}任务数据"}]
        
        content = [{"type": "T2", "text": f"【{title}】"}]
        
        # 收集每个任务的条件
        mission_conditions = [m.get('conditions', [])[:3] for m in missions[:3]]
        
        # 显示三个任务节点
        for i, mission in enumerate(missions[:3], 1):
            mission_type = mission.get('mission_type_cn', mission.get('mission_type', '未知'))
            content.append({"type": "T3", "text": f"{i}.{mission_type}"})
            
            conditions = mission_conditions[i-1] if i-1 < len(mission_conditions) else []
            if conditions:
                content.append({"type": "T4", "text": "  ".join(conditions)})
        
        # 显示个人变量
        content.append({"type": "T3", "text": "【可选风险变量】"})
        
        if variables:
            var_names = [self._translate_variable(v) for v in variables[:4]]
            content.append({"type": "T4", "text": "  ".join(var_names)})
        else:
            content.append({"type": "T4", "text": "暂无个人变量数据"})
        
        return content
