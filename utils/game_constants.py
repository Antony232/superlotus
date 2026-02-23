"""
游戏常量模块 - 存放任务类型、派系等翻译映射
避免在多个管理器中重复定义
"""

# 任务类型翻译映射
MISSION_TYPE_TRANSLATIONS = {
    'MT_EXTERMINATION': '歼灭',
    'MT_SURVIVAL': '生存',
    'MT_DEFENSE': '防御',
    'MT_MOBILE_DEFENSE': '移动防御',
    'MT_CAPTURE': '捕获',
    'MT_RESCUE': '救援',
    'MT_SPY': '间谍',
    'MT_SABOTAGE': '破坏',
    'MT_ASSASSINATION': '刺杀',
    'MT_INTEL': '间谍',
    'MT_TERRITORY': '拦截',
    'MT_ALCHEMY': '元素转换',
    'MT_ARTIFACT': '中断',
    'MT_EXCAVATE': '挖掘',
    'MT_VOID_CASCADE': '虚空覆涌',
    'MT_RETRIEVAL': '劫持',
    'MT_HIVE': '清巢',
    'MT_CORRUPTION': '虚空洪流',
    'MT_ASSAULT': '强袭',
    'MT_ENDLESS_CAPTURE': '传承种收割'
}

# 派系翻译映射
FACTION_TRANSLATIONS = {
    'FC_GRINEER': 'Grineer',
    'FC_CORPUS': 'Corpus',
    'FC_INFESTATION': 'Infested',
    'FC_OROKIN': 'Orokin',
    'FC_CORRUPTED': '堕落者',
    'FC_MITW': '低语者'
}

# 难度类型翻译映射
DIFFICULTY_TYPE_TRANSLATIONS = {
    'CD_NORMAL': '普通',
    'CD_HARD': '困难'
}

# 任务变体翻译映射
MISSION_VARIANT_TRANSLATIONS = {
    'GrowingIncursion': '增兵',
    'DoubleTrouble': '双重麻烦',
    'EximusGrenadiers': '卓越者榴弹手'
}

# 赛季名称翻译映射
SEASON_NAME_TRANSLATIONS = {
    "CST_WINTER": "冬季",
    "CST_SPRING": "春季",
    "CST_SUMMER": "夏季",
    "CST_FALL": "秋季",
    "CST_AUTUMN": "秋季"
}

# 事件类型标签翻译
EVENT_TYPE_LABELS = {
    "CET_CHALLENGE": "待办清单",
    "CET_REWARD": "选择奖励",
    "CET_UPGRADE": "增益覆写",
}


def get_mission_type_translation(mission_type: str) -> str:
    """获取任务类型翻译"""
    return MISSION_TYPE_TRANSLATIONS.get(mission_type, mission_type)


def get_faction_translation(faction: str) -> str:
    """获取派系翻译"""
    return FACTION_TRANSLATIONS.get(faction, faction)


def get_difficulty_type_translation(diff_type: str) -> str:
    """获取难度类型翻译"""
    return DIFFICULTY_TYPE_TRANSLATIONS.get(diff_type, diff_type)


def get_mission_variant_translation(variant: str) -> str:
    """获取任务变体翻译"""
    return MISSION_VARIANT_TRANSLATIONS.get(variant, variant)


def get_season_name_translation(season: str) -> str:
    """获取赛季名称翻译"""
    return SEASON_NAME_TRANSLATIONS.get(season, season)


def get_event_type_label(event_type: str) -> str:
    """获取事件类型标签"""
    return EVENT_TYPE_LABELS.get(event_type, "未知")
