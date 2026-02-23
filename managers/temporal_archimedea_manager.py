"""
时光科研(Temporal Archimedea)管理器 - 重构版
继承 BaseConquestManager，消除重复代码
"""
import logging
from typing import Dict, Optional

from managers.base.base_conquest import BaseConquestManager

logger = logging.getLogger(__name__)


class TemporalArchimedeaManager(BaseConquestManager):
    """时光科研管理器"""
    
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
    
    # 变体翻译映射（内置回退）
    _DEVIATION_FALLBACK = {
        'ContaminationZone': '屏住呼吸',
        'ExplosiveEnergy': '自爆虫浆',
        'EscalateImmediately': '破坏补给',
        'UnpoweredCapsules': '未通电胶囊',
        'EximusGrenadiers': '卓越者榴弹手',
        'GrowingIncursion': '增兵'
    }
    
    # 风险条件翻译映射（内置回退）
    _RISK_FALLBACK = {
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
    
    # 变量翻译映射（内置回退）
    _VARIABLE_FALLBACK = {
        'ShieldDelay': '护盾延迟',
        'DecayingFlesh': '腐烂血肉',
        'Starvation': '饥饿',
        'ContactDamage': '接触伤害',
        'OperatorLockout': '指挥官锁定',
        'Undersupplied': '补给短缺',
        'Exhaustion': '力竭'
    }
    
    def _get_conquest_type(self) -> str:
        """返回时光科研类型标识"""
        return "CT_HEX"
    
    def _get_translation_prefix(self) -> str:
        """返回翻译键前缀"""
        return "HexConquest"
    
    def _get_display_name(self) -> str:
        """获取显示名称"""
        return "时光科研"
    
    def _translate_mission_type(self, mission_type: str) -> str:
        """翻译任务类型（时光科研有特殊的 DT_ 前缀）"""
        extra_translations = {
            'DT_EXTERMINATE': '歼灭',
            'DT_SURVIVAL': '生存',
            'DT_DEFENSE': '防御',
            'DT_ALCHEMY': '元素转换',
            'DT_INTERCEPTION': '拦截'
        }
        if mission_type in extra_translations:
            return extra_translations[mission_type]
        return super()._translate_mission_type(mission_type)
    
    def _translate_deviation(self, deviation: str) -> str:
        """翻译变体（带内置回退）"""
        result = super()._translate_deviation(deviation)
        if result == deviation or not result:
            return self._DEVIATION_FALLBACK.get(deviation, deviation)
        return result
    
    def _translate_risk(self, risk: str) -> str:
        """翻译风险条件（带内置回退）"""
        result = super()._translate_risk(risk)
        if result == risk or not result:
            return self._RISK_FALLBACK.get(risk, risk)
        return result
    
    def _translate_variable(self, var: str) -> str:
        """翻译个人变量（带内置回退）"""
        result = super()._translate_variable(var)
        if result == var or not result:
            return self._VARIABLE_FALLBACK.get(var, var)
        return result
    
    # ========== 兼容旧代码的方法 ==========
    
    async def get_temporal_archimedea_info(self) -> Dict:
        """获取时光科研信息（兼容旧方法名）"""
        return await self.get_conquest_info()
    
    def format_temporal_archimedea_message(self, data: Dict) -> str:
        """格式化时光科研信息为可读文本"""
        return self.format_conquest_message(data, title="时光科研")
    
    def get_temporal_archimedea_structured(self, data: Dict) -> list:
        """格式化时光科研信息为结构化数据"""
        return self.get_conquest_structured(data, title="时光科研")


# 全局时光科研管理器实例
ta_manager: Optional[TemporalArchimedeaManager] = None


def get_temporal_archimedea_manager() -> Optional[TemporalArchimedeaManager]:
    """获取TemporalArchimedeaManager实例（懒加载）"""
    global ta_manager

    if ta_manager is not None:
        return ta_manager

    try:
        from managers.translation_manager import TranslationManager, GameStatusTranslator
        from managers.game_status_manager import game_status_manager

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
