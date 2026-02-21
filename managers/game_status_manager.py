# managers/game_status_manager.py
import requests
import asyncio
import time
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from config import config
from utils.game_status_config import game_status_config
from managers.translation_manager import translator  # 使用统一的翻译管理器
import logging

logger = logging.getLogger(__name__)


class GameStatusManager:
    def __init__(self):
        self.last_fetch_time = 0
        self.cache_duration = 300  # 5分钟缓存
        self.cached_data = {}

        # 世界状态API
        self.worldstate_url = "https://api.warframe.com/cdn/worldState.php"
        self.headers = {
            'User-Agent': 'Warframe-Status-Checker/1.0'
        }

        # 加载平原计算配置
        self.plain_config = game_status_config.plain_calculation_config

    async def fetch_world_state(self) -> Optional[Dict]:
        """获取世界状态数据 - 使用requests同步请求，通过线程池避免阻塞"""
        # 检查缓存
        now = time.time()
        if now - self.last_fetch_time < self.cache_duration and self.cached_data:
            return self.cached_data

        try:
            # 使用run_in_executor在线程池中执行同步的requests请求
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(self.worldstate_url, headers=self.headers, timeout=10)
            )

            if response.status_code == 200:
                # Warframe API返回的是text/html，但内容是JSON格式
                data = response.json()
                self.cached_data = data
                self.last_fetch_time = now
                return data
            else:
                logger.error(f"获取世界状态失败: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"获取世界状态异常: {e}")
            return self.cached_data if self.cached_data else None

    def convert_to_beijing(self, time_input) -> str:
        """将时间戳或ISO字符串转换为北京时间"""
        if not time_input:
            return "未知时间"

        try:
            dt_utc = None

            # 处理毫秒时间戳（数字、字符串、或字典格式）
            if isinstance(time_input, (int, float)):
                dt_utc = datetime.utcfromtimestamp(time_input / 1000)
            elif isinstance(time_input, dict) and '$numberLong' in time_input:
                timestamp = int(time_input['$numberLong'])
                dt_utc = datetime.utcfromtimestamp(timestamp / 1000)
            elif isinstance(time_input, str):
                # 处理ISO格式时间字符串
                if 'T' in time_input:
                    dt_utc = datetime.fromisoformat(time_input.replace('Z', '+00:00'))
                    # 转换为UTC
                    beijing_tz = timezone(timedelta(hours=8))
                    dt_beijing = dt_utc.astimezone(beijing_tz)
                    return dt_beijing.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    # 处理纯数字字符串
                    dt_utc = datetime.utcfromtimestamp(int(time_input) / 1000)

            dt_beijing = dt_utc + timedelta(hours=8)
            return dt_beijing.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.error(f"时间转换错误: {e}, 输入: {time_input}")
            return "时间解析错误"

    def calculate_time_left(self, time_input) -> str:
        """通用时间计算函数 - 支持毫秒时间戳和ISO字符串"""
        if not time_input:
            return "未知"

        try:
            expiry_utc = None

            # 处理毫秒时间戳（数字、字符串、或字典格式）
            if isinstance(time_input, (int, float)):
                expiry_utc = datetime.utcfromtimestamp(time_input / 1000)
            elif isinstance(time_input, dict) and '$numberLong' in time_input:
                timestamp = int(time_input['$numberLong'])
                expiry_utc = datetime.utcfromtimestamp(timestamp / 1000)
            elif isinstance(time_input, str):
                # 处理ISO格式时间字符串
                if 'T' in time_input:
                    expiry_utc = datetime.fromisoformat(time_input.replace('Z', '+00:00'))
                    now_utc = datetime.now(timezone.utc)
                else:
                    # 处理纯数字字符串
                    expiry_utc = datetime.utcfromtimestamp(int(time_input) / 1000)
                    now_utc = datetime.utcnow()

            # 根据输入类型决定当前时间
            if isinstance(time_input, str) and 'T' in time_input:
                now_utc = datetime.now(timezone.utc)
            else:
                now_utc = datetime.utcnow()

            time_left = expiry_utc - now_utc

            if time_left.total_seconds() < 0:
                return "已过期"

            total_seconds = int(time_left.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            if hours > 0:
                return f"{hours}小时{minutes}分"
            else:
                return f"{minutes}分{seconds}秒"
        except Exception as e:
            logger.error(f"时间计算错误: {e}, 输入: {time_input}")
            return "计算错误"

    def convert_iso_to_beijing(self, iso_time_str: str) -> str:
        """将ISO格式时间字符串转换为北京时间"""
        return self.convert_to_beijing(iso_time_str)

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

        for i, alert in enumerate(alerts[:5], 1):  # 只显示前5个
            mission_info = alert.get('MissionInfo', {})
            mission_type = mission_info.get('missionType', '未知类型')
            location = mission_info.get('location', '未知地点')
            faction = mission_info.get('faction', '未知派系')

            # 使用翻译器翻译节点和任务类型
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
                boss = sortie.get('Boss', '未知Boss')
                expiry = sortie.get('Expiry', {}).get('$date', {}).get('$numberLong')
                remaining_time = self.calculate_time_left(expiry)

                # 添加普通突击标题
                response_lines.append("\n【普通突击】")
                response_lines.append(f"剩余时间: {remaining_time}")

                variants = sortie.get('Variants', [])
                for j, variant in enumerate(variants, 1):
                    node = variant.get('node', '未知节点')
                    mission_type = variant.get('missionType', '未知类型')

                    # 翻译任务类型和节点（包含星球名）
                    node_name = translator.translate_node(node)
                    mission_type_translated = translator.translate_mission_type(mission_type)

                    # 提取星球名（从节点翻译结果中拆分，若未包含则补充）
                    planet_map = {
                        '地球': '地球', '金星': '金星', '水星': '水星', '火星': '火星',
                        '火卫二': '火卫二', '谷神星': '穀神星', '木星': '木星', '木卫二': '木卫二',
                        '土星': '土星', '天王星': '天王星', '海王星': '海王星', '冥王星': '冥王星',
                        '阋神星': '阋神星', '虚空': '虚空', '赤毒要塞': 'Kuva 要塞', '月球': '月球',
                        '扎里曼': '扎里曼'
                    }
                    planet_name = ""
                    for planet_cn, planet_display in planet_map.items():
                        if planet_cn in node_name:
                            planet_name = planet_display
                            break
                    if planet_name:
                        node_display = f"{node_name} ({planet_name})"
                    else:
                        node_display = node_name

                    response_lines.append(f"阶段{j}: {mission_type_translated} @ {node_display}")

        # 处理执行官猎杀（Archon突击）
        if lite_sorties:
            for lite_sortie in lite_sorties:
                boss = lite_sortie.get('Boss', '未知Boss')
                expiry = lite_sortie.get('Expiry', {}).get('$date', {}).get('$numberLong')
                remaining_time = self.calculate_time_left(expiry)

                # 添加执行官猎杀标题
                response_lines.append("\n【执行官猎杀】")
                response_lines.append(f"剩余时间: {remaining_time}")

                missions = lite_sortie.get('Missions', [])
                for j, mission in enumerate(missions, 1):
                    node = mission.get('node', '未知节点')
                    mission_type = mission.get('missionType', '未知类型')

                    # 翻译任务类型和节点（包含星球名）
                    node_name = translator.translate_node(node)
                    mission_type_translated = translator.translate_mission_type(mission_type)

                    # 提取星球名
                    planet_map = {
                        '地球': '地球', '金星': '金星', '水星': '水星', '火星': '火星',
                        '火卫二': '火卫二', '谷神星': '穀神星', '木星': '木星', '木卫二': '木卫二',
                        '土星': '土星', '天王星': '天王星', '海王星': '海王星', '冥王星': '冥王星',
                        '阋神星': '阋神星', '虚空': '虚空', '赤毒要塞': 'Kuva 要塞', '月球': '月球',
                        '扎里曼': '扎里曼'
                    }
                    planet_name = ""
                    for planet_cn, planet_display in planet_map.items():
                        if planet_cn in node_name:
                            planet_name = planet_display
                            break
                    if planet_name:
                        node_display = f"{node_name} ({planet_name})"
                    else:
                        node_display = node_name

                    response_lines.append(f"阶段{j}: {mission_type_translated} @ {node_display}")

        return "\n".join(response_lines)

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
        tier_order = ['VoidT1', 'VoidT2', 'VoidT3', 'VoidT4', 'VoidT5', 'VoidT6']
        for tier in tier_order:
            if tier in fissures_by_tier:
                tier_fissures = fissures_by_tier[tier]
                tier_name = game_status_config.fissure_tiers.get(tier, tier.replace('VoidT', 'T'))

                # 添加等级标题（与平原标题同级）
                response_lines.append(f"【{tier_name}裂缝】")

                # 显示所有裂缝，不限制数量
                for fissure in tier_fissures:
                    node = fissure.get('Node', '未知节点')
                    mission_type = fissure.get('MissionType', '未知类型')
                    expiry = fissure.get('Expiry', {}).get('$date', {}).get('$numberLong')
                    is_hard = fissure.get('Hard', False)

                    # 使用翻译器翻译节点和任务类型
                    node_name = translator.translate_node(node)
                    mission_type_translated = translator.translate_mission_type(mission_type)

                    # 新格式：一行显示，【钢铁】或【普通】使用不同颜色
                    difficulty_prefix = "【钢铁】" if is_hard else "【普通】"
                    
                    # 构建单行显示
                    line = f"{difficulty_prefix} {mission_type_translated} @ {node_name} 剩余：{self.calculate_time_left(expiry)}"
                    response_lines.append(line)

                # 每组之间添加空行分隔
                response_lines.append("")

        # 移除最后一个空行
        if response_lines and response_lines[-1] == "":
            response_lines.pop()

        return "\n".join(response_lines).strip()

    async def get_plains_status(self) -> str:
        """计算并返回所有平原的昼夜状态（去除emoji、小贴士、标题行和分割线）"""
        response_lines = []
        
        # 获取当前时间
        current_utc = time.time()

        # 1. 希图斯（夜灵平野）
        cetus_info = self.plain_config.get("cetus", {})
        if cetus_info:
            try:
                time_delta = current_utc - cetus_info["start"]
                cycle_pos = time_delta % cetus_info["length"]
                
                # 判断当前状态
                if cetus_info["day_start"] <= cycle_pos < cetus_info["day_end"]:
                    current_state = "白天"
                    next_state = "夜晚"
                    remaining_sec = cetus_info["day_end"] - cycle_pos
                else:
                    current_state = "夜晚"
                    next_state = "白天"
                    if cycle_pos < cetus_info["day_start"]:
                        remaining_sec = cetus_info["day_start"] - cycle_pos
                    else:
                        remaining_sec = cetus_info["length"] - cycle_pos
                
                # 格式化时间
                remaining_min = int(remaining_sec // 60)
                remaining_sec_format = int(remaining_sec % 60)
                remaining_time = f"{remaining_min}分{remaining_sec_format:02d}秒"
                
                # 计算切换时间
                next_switch_utc = datetime.utcfromtimestamp(current_utc + remaining_sec)
                next_switch_cn = next_switch_utc + timedelta(hours=8)
                next_switch_time = next_switch_cn.strftime("%Y-%m-%d %H:%M:%S")
                
                # 添加到回复（去除标题行和分割线）
                response_lines.append(f"【{cetus_info['name']}】")
                response_lines.append(f"• 当前状态: {current_state}")
                response_lines.append(f"• 剩余时间: {remaining_time}")
                response_lines.append(f"• 下次切换: {next_state}")
                response_lines.append(f"• 切换时间: {next_switch_time}")
                response_lines.append("")
            except Exception as e:
                response_lines.append(f"【{cetus_info.get('name', '夜灵平野')}】")
                response_lines.append(f"• 错误: 无法计算状态")
                response_lines.append("")

        # 2. 福尔图娜（奥布山谷）
        fortuna_info = self.plain_config.get("fortuna", {})
        if fortuna_info:
            try:
                time_delta = current_utc - fortuna_info["start"]
                cycle_pos = time_delta % fortuna_info["length"]
                
                # 判断当前状态
                if fortuna_info["day_start"] <= cycle_pos < fortuna_info["day_end"]:
                    current_state = "温暖期"
                    next_state = "寒冷期"
                    remaining_sec = fortuna_info["day_end"] - cycle_pos
                else:
                    current_state = "寒冷期"
                    next_state = "温暖期"
                    if cycle_pos < fortuna_info["day_start"]:
                        remaining_sec = fortuna_info["day_start"] - cycle_pos
                    else:
                        remaining_sec = fortuna_info["length"] - cycle_pos
                
                # 格式化时间
                remaining_min = int(remaining_sec // 60)
                remaining_sec_format = int(remaining_sec % 60)
                remaining_time = f"{remaining_min}分{remaining_sec_format:02d}秒"
                
                # 计算切换时间
                next_switch_utc = datetime.utcfromtimestamp(current_utc + remaining_sec)
                next_switch_cn = next_switch_utc + timedelta(hours=8)
                next_switch_time = next_switch_cn.strftime("%Y-%m-%d %H:%M:%S")
                
                # 添加到回复（去除标题行和分割线）
                response_lines.append(f"【{fortuna_info['name']}】")
                response_lines.append(f"• 当前状态: {current_state}")
                response_lines.append(f"• 剩余时间: {remaining_time}")
                response_lines.append(f"• 下次切换: {next_state}")
                response_lines.append(f"• 切换时间: {next_switch_time}")
                response_lines.append("")
            except Exception as e:
                response_lines.append(f"【{fortuna_info.get('name', '奥布山谷')}】")
                response_lines.append(f"• 错误: 无法计算状态")
                response_lines.append("")

        # 3. 魔胎之境（双衍王境）
        deimos_info = self.plain_config.get("deimos", {})
        if deimos_info:
            try:
                # 魔胎之境同步希图斯的循环
                cetus_data = self.plain_config.get("cetus", {})
                if cetus_data:
                    time_delta = current_utc - cetus_data["start"]
                    cycle_pos = time_delta % cetus_data["length"]
                    
                    # 判断状态
                    is_day = cetus_data["day_start"] <= cycle_pos < cetus_data["day_end"]
                    
                    # 计算剩余时间
                    if is_day:
                        current_state = "Fass（活跃期）"
                        next_state = "Vome（平静期）"
                        remaining_sec = cetus_data["day_end"] - cycle_pos
                    else:
                        current_state = "Vome（平静期）"
                        next_state = "Fass（活跃期）"
                        if cycle_pos < cetus_data["day_start"]:
                            remaining_sec = cetus_data["day_start"] - cycle_pos
                        else:
                            remaining_sec = cetus_data["length"] - cycle_pos
                    
                    # 格式化时间
                    remaining_min = int(remaining_sec // 60)
                    remaining_sec_format = int(remaining_sec % 60)
                    remaining_time = f"{remaining_min}分{remaining_sec_format:02d}秒"
                    
                    # 计算切换时间
                    next_switch_utc = datetime.utcfromtimestamp(current_utc + remaining_sec)
                    next_switch_cn = next_switch_utc + timedelta(hours=8)
                    next_switch_time = next_switch_cn.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 添加到回复（去除标题行和分割线）
                    response_lines.append(f"【{deimos_info['name']}】")
                    response_lines.append(f"• 当前状态: {current_state}")
                    response_lines.append(f"• 剩余时间: {remaining_time}")
                    response_lines.append(f"• 下次切换: {next_state}")
                    response_lines.append(f"• 切换时间: {next_switch_time}")
                else:
                    response_lines.append(f"【{deimos_info['name']}】")
                    response_lines.append(f"• 当前状态: 未知")
                    response_lines.append(f"• 剩余时间: 未知")
                    response_lines.append(f"• 下次切换: 未知")
                    response_lines.append(f"• 切换时间: 未知")
                response_lines.append("")
            except Exception as e:
                response_lines.append(f"【{deimos_info.get('name', '魔胎之境')}】")
                response_lines.append(f"• 错误: 无法计算状态")
                response_lines.append("")

        # 如果没有任何平原信息，添加提示
        if not response_lines:
            response_lines.append("未找到平原状态信息")

        # 去除最后一个空行（如果有）
        if response_lines and response_lines[-1] == "":
            response_lines.pop()
        
        return "\n".join(response_lines).strip()

    async def get_all_status(self) -> str:
        """获取所有游戏状态（去除emoji）"""
        responses = []

        # 获取各模块状态
        alerts = await self.get_alerts()
        sorties = await self.get_sorties()
        fissures = await self.get_void_fissures()
        plains = await self.get_plains_status()

        # 收集非空状态
        for res in [alerts, sorties, fissures, plains]:
            if res and res.strip():
                responses.append(res)

        # 添加数据更新时间（去除emoji）
        now_beijing = datetime.utcnow() + timedelta(hours=8)
        responses.append(f"\n数据更新时间: {now_beijing.strftime('%H:%M')} (北京时间)")

        return "\n\n".join(responses)

    async def close(self):
        """清理资源"""
        pass


# 全局游戏状态管理器实例（必须在类外定义）
game_status_manager = GameStatusManager()