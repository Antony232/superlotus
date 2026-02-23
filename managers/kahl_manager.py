# kahl_manager.py - 时光科研(Kahl)管理器 - 重构版
"""
时光科研(Kahl)管理器
继承 BaseConquestManager，消除重复代码
"""
import logging
from typing import Dict, Optional

from managers.base.base_conquest import BaseConquestManager

logger = logging.getLogger(__name__)


class KahlManager(BaseConquestManager):
    """时光科研管理器 - 处理Kahl任务数据"""
    
    # 个人变量映射
    _VARIABLE_MAPPING = {
        'Undersupplied': 'MaxAmmo',
        'OverSensitive': 'OverSensitive',
        'VoidEnergyOverload': 'VoidEnergyOverload',
        'DullBlades': 'ComboCountChance',
        'Exhaustion': 'Exhaustion',
        'TimeDilation': 'TimeDilation',
        'Knifestep': 'Knifestep'
    }
    
    # 变体翻译映射（内置回退）
    _DEVIATION_FALLBACK = {
        'ContaminationZone': '屏住呼吸',
        'ExplosiveEnergy': '自爆虫浆',
        'EscalateImmediately': '破坏补给'
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
    
    def _translate_deviation(self, deviation: str) -> str:
        """翻译变体（带内置回退）"""
        result = super()._translate_deviation(deviation)
        if result == deviation or not result:
            return self._DEVIATION_FALLBACK.get(deviation, deviation)
        return result
    
    # ========== 兼容旧代码的方法 ==========
    
    async def get_kahl_info(self) -> Dict:
        """获取Kahl时光科研信息（兼容旧方法名）"""
        return await self.get_conquest_info()
    
    def format_kahl_message(self, data: Dict) -> str:
        """格式化Kahl信息为可读文本"""
        return self.format_conquest_message(data, title="时光科研")


# 全局Kahl管理器实例
kahl_manager: Optional[KahlManager] = None


def get_kahl_manager() -> Optional[KahlManager]:
    """
    获取KahlManager实例（懒加载）
    """
    global kahl_manager

    if kahl_manager is not None:
        return kahl_manager

    try:
        from managers.translation_manager import TranslationManager, GameStatusTranslator
        from managers.game_status_manager import game_status_manager

        translation_manager = TranslationManager()
        game_translator = GameStatusTranslator()

        translation_manager.load_translations()
        game_translator.load_translations()

        kahl_manager = KahlManager(
            translation_manager=translation_manager,
            game_translator=game_translator,
            world_state_fetcher=game_status_manager.fetch_world_state
        )

        return kahl_manager

    except Exception as e:
        logger.error(f"初始化KahlManager失败: {e}")
        return None
