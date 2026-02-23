# managers/game_status_manager.py
"""
游戏状态管理器 - 重构版
使用统一的 WorldStateClient 和 time_utils
"""
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from config import config
from core.constants import CacheTTL, FissureTiers, PlanetNames
from core.world_state_client import world_state_client, fetch_world_state
from utils.time_utils import (
    calculate_time_left,
    convert_to_beijing,
    get_current_beijing_hour_minute,
)
from utils.game_status_config import game_status_config
from managers.translation_manager import translator

logger = logging.getLogger(__name__)


class GameStatusManager:
    """
    游戏状态管理器
    
    职责：
    1. 提供游戏状态数据的便捷访问方法
    2. 格式化各类游戏数据
    3. 委托 WorldStateClient 处理数据获取和缓存
    """
    
    def __init__(self):
        # 直接使用全局 world_state_client，无需重复缓存
        self.plain_config = game_status_config.plain_calculation_config
    
    async def fetch_world_state(self) -> Optional[Dict]:
        """
        获取世界状态数据
        
        委托给统一的 WorldStateClient，保持方法签名兼容
        """
        return await world_state_client.fetch()
    
    # ========== 时间处理方法（保留以兼容现有调用）==========
    # 这些方法现在委托给 utils/time_utils.py
    
    def convert_to_beijing(self, time_input) -> str:
        """将时间戳或ISO字符串转换为北京时间"""
        return convert_to_beijing(time_input)
    
    def calculate_time_left(self, time_input) -> str:
        """通用时间计算函数"""
        return calculate_time_left(time_input)
    
    def convert_iso_to_beijing(self, iso_time_str: str) -> str:
        """将ISO格式时间字符串转换为北京时间"""
        return self.convert_to_beijing(iso_time_str)
    
    # ========== 游戏状态获取方法 ==========
    
    async def get_alerts(self) -> str:
        """获取警报信息（去除emoji）"""
        data = await self.fetch_world_state()
        if not data:
            return "获取警报数据失败"

        alerts = data.get('Alerts', [])

        if not alerts:
            return "当前没有警报"

        response = "警报任务\n"
        response += "=" * 30 + "\n"
        response += f"当前有 {len(alerts)} 个警报:\n\n"

        for i, alert in enumerate(alerts[:5], 1):
            mission_info = alert.get('MissionInfo', {})
            mission_type = mission_info.get('missionType', '未知类型')
            location = mission_info.get('location', '未知地点')
            faction = mission_info.get('faction', '未知派系')

            location_name = translator.translate_node(location)
            mission_type_translated = translator.translate_mission_type(mission_type)
            faction_translated = translator.translate_faction(faction)

            reward_info = mission_info.get('missionReward', {})
            credits = reward_info.get('credits', 0)

            expiry = alert.get('Expiry', {}).get('$date', {}).get('$numberLong')

            response += f"【警报{i}】\n"
            response += f"• 任务: {mission_type_translated} @ {location_name}\n"
            response += f"• 派系: {faction_translated}\n"
            if credits > 0:
                response += f"• 奖励: {credits:,}现金\n"
            response += f"• 剩余: {self.calculate_time_left(expiry)}\n\n"

        if len(alerts) > 5:
            response += f"... 还有 {len(alerts) - 5} 个警报\n"

        return response.strip()

    async def get_sorties(self) -> str:
        """获取突击信息（去除emoji）"""
        data = await self.fetch_world_state()
        if not data:
            return "获取突击数据失败"

        sorties = data.get('Sorties', [])
        lite_sorties = data.get('LiteSorties', [])

        if not sorties and not lite_sorties:
            return "突击任务\n==============================\n当前没有突击任务"

        response_lines = ["突击任务", "=============================="]

        # 处理普通突击
        if sorties:
            for sortie in sorties:
                expiry = sortie.get('Expiry', {}).get('$date', {}).get('$numberLong')
                remaining_time = self.calculate_time_left(expiry)

                response_lines.append("\n【普通突击】")
                response_lines.append(f"剩余时间: {remaining_time}")

                variants = sortie.get('Variants', [])
                for j, variant in enumerate(variants, 1):
                    node = variant.get('node', '未知节点')
                    mission_type = variant.get('missionType', '未知类型')

                    node_name = translator.translate_node(node)
                    mission_type_translated = translator.translate_mission_type(mission_type)
                    node_display = self._format_node_with_planet(node_name)

                    response_lines.append(f"阶段{j}: {mission_type_translated} @ {node_display}")

        # 处理执行官猎杀（Archon突击）
        if lite_sorties:
            for lite_sortie in lite_sorties:
                expiry = lite_sortie.get('Expiry', {}).get('$date', {}).get('$numberLong')
                remaining_time = self.calculate_time_left(expiry)

                response_lines.append("\n【执行官猎杀】")
                response_lines.append(f"剩余时间: {remaining_time}")

                missions = lite_sortie.get('Missions', [])
                for j, mission in enumerate(missions, 1):
                    node = mission.get('node', '未知节点')
                    mission_type = mission.get('missionType', '未知类型')

                    node_name = translator.translate_node(node)
                    mission_type_translated = translator.translate_mission_type(mission_type)
                    node_display = self._format_node_with_planet(node_name)

                    response_lines.append(f"阶段{j}: {mission_type_translated} @ {node_display}")

        return "\n".join(response_lines)

    def _format_node_with_planet(self, node_name: str) -> str:
        """格式化节点名称，添加星球显示"""
        for planet_cn, planet_display in PlanetNames.MAP.items():
            if planet_cn in node_name:
                return f"{node_name} ({planet_display})"
        return node_name

    async def get_void_fissures(self, difficulty_filter: str = "all") -> str:
        """获取虚空裂缝信息（新格式）"""
        data = await self.fetch_world_state()
        if not data:
            return "获取裂缝数据失败"

        fissures = data.get('ActiveMissions', [])

        if not fissures:
            return "当前没有虚空裂缝"

        # 按难度过滤
        if difficulty_filter == "hard":
            fissures = [f for f in fissures if f.get('Hard', False)]
        elif difficulty_filter == "normal":
            fissures = [f for f in fissures if not f.get('Hard', False)]

        if not fissures:
            return f"当前没有{difficulty_filter}裂缝"

        # 按等级分组
        fissures_by_tier = {}
        for fissure in fissures:
            tier = fissure.get('Modifier', '未知等级')
            if tier not in fissures_by_tier:
                fissures_by_tier[tier] = []
            fissures_by_tier[tier].append(fissure)

        response_lines = []

        # 按等级排序显示
        for tier in FissureTiers.ORDER:
            if tier in fissures_by_tier:
                tier_fissures = fissures_by_tier[tier]
                tier_name = FissureTiers.NAMES.get(tier, tier.replace('VoidT', 'T'))

                response_lines.append(f"【{tier_name}裂缝】")

                for fissure in tier_fissures:
                    node = fissure.get('Node', '未知节点')
                    mission_type = fissure.get('MissionType', '未知类型')
                    expiry = fissure.get('Expiry', {}).get('$date', {}).get('$numberLong')
                    is_hard = fissure.get('Hard', False)

                    node_name = translator.translate_node(node)
                    mission_type_translated = translator.translate_mission_type(mission_type)

                    difficulty_prefix = "【钢铁】" if is_hard else "【普通】"
                    line = f"{difficulty_prefix} {mission_type_translated} @ {node_name} 剩余：{self.calculate_time_left(expiry)}"
                    response_lines.append(line)

                response_lines.append("")

        if response_lines and response_lines[-1] == "":
            response_lines.pop()

        return "\n".join(response_lines).strip()

    async def get_plains_status(self) -> str:
        """计算并返回所有平原的昼夜状态"""
        response_lines = []
        current_utc = time.time()

        # 1. 希图斯（夜灵平野）
        cetus_info = self.plain_config.get("cetus", {})
        if cetus_info:
            plain_status = self._calculate_plain_status(
                cetus_info, current_utc, 
                day_states=("白天", "夜晚"),
                warm_states=("白天", "夜晚")
            )
            if plain_status:
                response_lines.append(f"【{cetus_info['name']}】")
                response_lines.extend(plain_status)
                response_lines.append("")

        # 2. 福尔图娜（奥布山谷）
        fortuna_info = self.plain_config.get("fortuna", {})
        if fortuna_info:
            plain_status = self._calculate_plain_status(
                fortuna_info, current_utc,
                day_states=("温暖期", "寒冷期"),
                warm_states=("温暖期", "寒冷期")
            )
            if plain_status:
                response_lines.append(f"【{fortuna_info['name']}】")
                response_lines.extend(plain_status)
                response_lines.append("")

        # 3. 魔胎之境（双衍王境）
        deimos_info = self.plain_config.get("deimos", {})
        if deimos_info and cetus_info:
            plain_status = self._calculate_plain_status(
                cetus_info, current_utc,
                day_states=("Fass（活跃期）", "Vome（平静期）"),
                warm_states=("Fass（活跃期）", "Vome（平静期）")
            )
            if plain_status:
                response_lines.append(f"【{deimos_info['name']}】")
                response_lines.extend(plain_status)

        if not response_lines:
            response_lines.append("未找到平原状态信息")

        if response_lines and response_lines[-1] == "":
            response_lines.pop()

        return "\n".join(response_lines).strip()

    def _calculate_plain_status(
        self, 
        plain_info: Dict, 
        current_utc: float,
        day_states: tuple,
        warm_states: tuple
    ) -> List[str]:
        """计算单个平原状态"""
        try:
            time_delta = current_utc - plain_info["start"]
            cycle_pos = time_delta % plain_info["length"]

            if plain_info["day_start"] <= cycle_pos < plain_info["day_end"]:
                current_state = day_states[0]
                next_state = day_states[1]
                remaining_sec = plain_info["day_end"] - cycle_pos
            else:
                current_state = day_states[1]
                next_state = day_states[0]
                if cycle_pos < plain_info["day_start"]:
                    remaining_sec = plain_info["day_start"] - cycle_pos
                else:
                    remaining_sec = plain_info["length"] - cycle_pos

            remaining_min = int(remaining_sec // 60)
            remaining_sec_format = int(remaining_sec % 60)
            remaining_time = f"{remaining_min}分{remaining_sec_format:02d}秒"

            next_switch_utc = datetime.utcfromtimestamp(current_utc + remaining_sec)
            next_switch_cn = next_switch_utc + timedelta(hours=8)
            next_switch_time = next_switch_cn.strftime("%Y-%m-%d %H:%M:%S")

            return [
                f"• 当前状态: {current_state}",
                f"• 剩余时间: {remaining_time}",
                f"• 下次切换: {next_state}",
                f"• 切换时间: {next_switch_time}"
            ]
        except Exception as e:
            logger.error(f"计算平原状态失败: {e}")
            return [f"• 错误: 无法计算状态"]

    async def get_all_status(self) -> str:
        """获取所有游戏状态"""
        responses = []

        alerts = await self.get_alerts()
        sorties = await self.get_sorties()
        fissures = await self.get_void_fissures()
        plains = await self.get_plains_status()

        for res in [alerts, sorties, fissures, plains]:
            if res and res.strip():
                responses.append(res)

        responses.append(f"\n数据更新时间: {get_current_beijing_hour_minute()} (北京时间)")

        return "\n\n".join(responses)

    async def close(self):
        """清理资源"""
        await world_state_client.close()


# 全局游戏状态管理器实例
game_status_manager = GameStatusManager()
