"""
常量定义模块 - 集中管理所有魔法数字和配置常量
消除代码中的硬编码值，提高可维护性
"""


class CacheTTL:
    """缓存过期时间（秒）"""
    WORLD_STATE = 300          # 世界状态缓存：5分钟
    BOUNTY = 300               # 赏金任务缓存：5分钟
    TRANSLATION = 3600         # 翻译缓存：1小时
    ITEM_DETAILS = 1800        # 物品详情缓存：30分钟
    ITEM_ORDERS = 300          # 物品订单缓存：5分钟
    PRICE_STATISTICS = 600     # 价格统计缓存：10分钟


class APIUrls:
    """API 端点地址"""
    WORLD_STATE = "https://api.warframe.com/cdn/worldState.php"
    WFM_BASE = "https://api.warframe.market/v2"
    BOUNTY_CYCLE = "https://oracle.browse.wf/bounty-cycle"


class Defaults:
    """默认配置值"""
    TARGET_GROUP = 813532268           # 默认目标群组
    MAX_SUBSCRIPTIONS = 10             # 最大订阅数
    REQUEST_TIMEOUT = 10               # 请求超时（秒）
    MAX_RETRIES = 3                    # 最大重试次数
    RATE_LIMIT_PER_SEC = 3             # API 速率限制（每秒请求数）


class FissureTiers:
    """裂缝等级映射"""
    T1 = "古纪"
    T2 = "前纪"
    T3 = "中纪"
    T4 = "后纪"
    T5 = "安魂"
    T6 = "钢铁"

    ORDER = ["VoidT1", "VoidT2", "VoidT3", "VoidT4", "VoidT5", "VoidT6"]

    NAMES = {
        "VoidT1": "古纪",
        "VoidT2": "前纪",
        "VoidT3": "中纪",
        "VoidT4": "后纪",
        "VoidT5": "安魂",
        "VoidT6": "钢铁",
    }


class ConquestTypes:
    """科研类型标识"""
    ARCHIMEDEA = "CT_LAB"      # 深层科研
    KAHL = "CT_HEX"            # 时光科研（Kahl任务）


class PlainCycles:
    """平原循环周期配置（秒）"""
    # 希图斯/夜灵平野
    CETUS_LENGTH = 9000              # 150分钟
    CETUS_DAY_START = 300 * 60       # 白天开始：300分钟
    CETUS_DAY_END = 700 * 60         # 白天结束：700分钟

    # 福尔图娜/奥布山谷（与希图斯相同周期）
    FORTUNA_LENGTH = 9000
    FORTUNA_DAY_START = 300 * 60     # 温暖期开始
    FORTUNA_DAY_END = 700 * 60       # 温暖期结束


class TimeZones:
    """时区配置"""
    BEIJING_OFFSET = 8  # 北京时间 UTC+8


class PlanetNames:
    """星球名称映射（中文 -> 显示名）"""
    MAP = {
        '地球': '地球',
        '金星': '金星',
        '水星': '水星',
        '火星': '火星',
        '火卫二': '火卫二',
        '谷神星': '穀神星',
        '木星': '木星',
        '木卫二': '木卫二',
        '土星': '土星',
        '天王星': '天王星',
        '海王星': '海王星',
        '冥王星': '冥王星',
        '阋神星': '阋神星',
        '虚空': '虚空',
        '赤毒要塞': 'Kuva 要塞',
        '月球': '月球',
        '扎里曼': '扎里曼'
    }


# 深层科研周期起始日期
ARCHIMEDEA_START_DATE = (2024, 11, 26)  # (年, 月, 日)
ARCHIMEDEA_CYCLE_WEEKS = 8               # 8周一个周期
