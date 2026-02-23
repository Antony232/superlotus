# game_status_config.py - 配套配置文件
import json
import os
from pathlib import Path

class GameStatusConfig:
    def __init__(self):
        self.config_dir = Path("./game_status_data")
        self.config_dir.mkdir(exist_ok=True)

        # 平原循环状态名称映射
        self.plain_cycles = {
            'CetusSyndicate': {'name': '夜灵平野', 'states': ['白天', '夜晚']},
            'SolarisSyndicate': {'name': '奥布山谷', 'states': ['温暖', '寒冷']},
            'EntratiSyndicate': {'name': '魔胎之境', 'states': ['Fass', 'Vome']}
        }

        # 虚空裂缝等级名称映射
        self.fissure_tiers = {
            'VoidT1': '古纪',
            'VoidT2': '前纪',
            'VoidT3': '中纪',
            'VoidT4': '后纪',
            'VoidT5': '安魂',
            'VoidT6': '全能'
        }

        # 突击任务类型名称
        self.sortie_types = {
            'regular': '普通突击',
            'lite': 'Archon突击'
        }

        # 星球名称列表（中英文）
        self.planets_cn = [
            "水星", "金星", "地球", "火星", "木星", "土星", "天王星", "海王星",
            "冥王星", "赛德娜", "欧罗巴", "阋神星", "火卫二", "火卫一", "月球",
            "帕尔沃斯的姐妹", "星环", "钢铁之路", "虚空"
        ]

        self.planets_en = [
            "Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune",
            "Pluto", "Sedna", "Europa", "Eris", "Deimos", "Phobos", "Lua",
            "Parvos Granum", "Orb Vallis", "Steel Path", "Void"
        ]

        # 任务类型映射
        self.mission_types = {
            "defense": "防御",
            "capture": "捕获",
            "survival": "生存",
            "spy": "间谍",
            "extermination": "歼灭",
            "mobile defense": "移动防御",
            "rescue": "救援",
            "sabotage": "破坏",
            "interception": "拦截",
            "assassination": "刺杀",
            "excavation": "挖掘",
            "defection": "叛逃",
            "disruption": "中断",
            "hive": "清巢",
            "alchemy": "元素转换"
        }

        # 平原昼夜计算核心配置（官方正确参数）
        self.plain_calculation_config = {
            "cetus": {  # 希图斯(地球平原)
                "name": "夜灵平野（希图斯）",
                "start": 1509371722,  # 基准时间戳（官方）
                "length": 8998.8748,  # 完整周期（秒）≈150分钟
                "day_start": 2249.7187,  # 白天起始偏移
                "day_end": 8248.9686    # 白天结束偏移
            },
            "fortuna": {  # 福尔图娜(金星平原) - 官方源码参数
                "name": "奥布山谷（福尔图娜）",
                "start": 1542131224,  # 源码中的基准时间（原1542131227，修正为官方值）
                "length": 1600,        # 总周期（源码值）
                "day_start": 800,      # 温暖期起始（源码值）
                "day_end": 1200        # 温暖期结束（源码值）
            },
            "deimos": {  # 魔胎之境（同步希图斯）
                "name": "魔胎之境（双衍王境）",
                "sync_with": "cetus",  # 关联希图斯的循环
                "fass_state": "Fass（活跃期）",  # 对应希图斯白天
                "vome_state": "Vome（平静期）"   # 对应希图斯夜晚
            }
        }

# 全局配置实例
game_status_config = GameStatusConfig()