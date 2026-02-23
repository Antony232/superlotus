# fissure_monitor.py - 裂缝监控器 - 重构版
"""
裂缝监控器 - 使用统一的 WorldStateClient
"""
import asyncio
import time
from typing import List, Dict

from nonebot import get_bot

from core.world_state_client import world_state_client
from core.constants import Defaults
from managers.subscription_manager import subscription_manager, FissureSubscription
from managers.translation_manager import translator
from utils.time_utils import calculate_time_left
from utils.game_status_config import game_status_config
import logging

logger = logging.getLogger(__name__)


class FissureMonitor:
    """裂缝监控器"""
    
    def __init__(self, check_interval: int = Defaults.REQUEST_TIMEOUT * 30):  # 默认5分钟
        self.check_interval = check_interval
        self.running = False
        self.last_fissures = []
    
    async def start(self):
        """启动监控"""
        if self.running:
            return

        self.running = True
        logger.info("🚀 启动裂缝订阅监控...")
        
        try:
            while self.running:
                await self.check_fissures()
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            logger.info("🛑 裂缝监控被取消")
        except Exception as e:
            logger.error(f"❌ 裂缝监控异常: {e}")
        finally:
            self.running = False
    
    async def stop(self):
        """停止监控"""
        self.running = False
    
    async def check_fissures(self):
        """检查裂缝并发送通知"""
        try:
            # 使用统一的 WorldStateClient
            data = await world_state_client.fetch()
            if not data:
                return
            
            fissures = data.get('ActiveMissions', [])
            current_fissures = []
            
            for fissure in fissures:
                fissure_id = subscription_manager.generate_fissure_id(fissure)
                current_fissures.append((fissure_id, fissure))
            
            # 找出新出现的裂缝
            current_ids = {fid for fid, _ in current_fissures}
            last_ids = {fid for fid, _ in self.last_fissures}
            new_ids = current_ids - last_ids
            
            for fissure_id, fissure in current_fissures:
                if fissure_id in new_ids:
                    if not subscription_manager.is_fissure_notified(fissure_id):
                        await self.match_and_notify(fissure_id, fissure)
            
            self.last_fissures = current_fissures
            
        except Exception as e:
            logger.error(f"❌ 检查裂缝失败: {e}")
    
    async def match_and_notify(self, fissure_id: str, fissure: dict):
        """匹配订阅并发送通知"""
        try:
            node = fissure.get('Node', '未知节点')
            mission_type = fissure.get('MissionType', '未知类型')
            is_hard = fissure.get('Hard', False)
            tier = fissure.get('Modifier', '未知等级')
            expiry = fissure.get('Expiry', {}).get('$date', {}).get('$numberLong')
            
            node_name = translator.translate_node(node)
            mission_type_translated = translator.translate_mission_type(mission_type)
            planet = self._extract_planet(node_name)
            tier_name = game_status_config.fissure_tiers.get(tier, tier.replace('VoidT', 'T'))
            time_left = calculate_time_left(expiry)
            
            fissure_info = {
                'node': node_name,
                'node_path': node,
                'mission_type': mission_type_translated,
                'difficulty': 'steel' if is_hard else 'normal',
                'tier': tier_name,
                'planet': planet,
                'time_left': time_left,
                'mission_type_en': mission_type,
                'tier_en': tier
            }
            
            matched_subs = [sub for sub in subscription_manager.subscriptions 
                           if self._match_subscription(sub, fissure_info)]
            
            if matched_subs:
                await self.send_notifications(fissure_info, matched_subs)
                subscription_manager.mark_fissure_as_notified(fissure_id)
                
                for sub in matched_subs:
                    sub.last_notified_time = time.time()
                subscription_manager.save_subscriptions()
                
                logger.info(f"📢 发送裂缝通知: {mission_type_translated} @ {node_name}")
    
        except Exception as e:
            logger.error(f"❌ 匹配裂缝通知失败: {e}")
    
    def _match_subscription(self, sub: FissureSubscription, fissure_info: dict) -> bool:
        """检查裂缝是否匹配订阅条件"""
        mission_match = (sub.mission_type == fissure_info['mission_type'] or
                        sub.mission_type == fissure_info['mission_type_en'])

        difficulty_match = (
            sub.difficulty == 'both' or
            sub.difficulty == fissure_info['difficulty']
        )

        tier_match = (
            sub.tier == 'all' or
            sub.tier == fissure_info['tier'] or
            sub.tier == fissure_info['tier_en']
        )

        planet_match = sub.planet == 'all' or sub.planet == fissure_info['planet']

        node_match = True
        if sub.node_filter:
            node_match = (sub.node_filter in fissure_info['node_path'] or
                         sub.node_filter.lower() in fissure_info['node'].lower())

        return mission_match and difficulty_match and tier_match and planet_match and node_match

    def _extract_planet(self, node_name: str) -> str:
        """从节点名称中提取星球名称"""
        for planet in game_status_config.planets_cn + game_status_config.planets_en:
            if planet in node_name:
                return planet
        return "未知星球"
    
    async def send_notifications(self, fissure_info: dict, subscriptions: List[FissureSubscription]):
        """发送通知给订阅者"""
        try:
            bot = get_bot()

            subs_by_group = {}
            for sub in subscriptions:
                if sub.group_id not in subs_by_group:
                    subs_by_group[sub.group_id] = []
                subs_by_group[sub.group_id].append(sub)

            for group_id, group_subs in subs_by_group.items():
                user_ids = [sub.user_id for sub in group_subs]
                difficulty_text = "钢铁" if fissure_info['difficulty'] == 'steel' else "普通"

                message = (
                    f"📢 裂缝订阅通知！\n"
                    f"================\n"
                    f"🔔 您订阅的裂缝出现啦！\n"
                    f"• 任务类型: {fissure_info['mission_type']}\n"
                    f"• 难度: {difficulty_text}\n"
                    f"• 等级: {fissure_info['tier']}\n"
                    f"• 地点: {fissure_info['node']}\n"
                    f"• 剩余时间: {fissure_info['time_left']}"
                )

                at_users = " ".join([f"[CQ:at,qq={uid}]" for uid in user_ids])
                full_message = at_users + "\n" + message

                await bot.send_group_msg(group_id=int(group_id), message=full_message)
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"❌ 发送通知失败: {e}")
    
    def force_check(self):
        """强制立即检查裂缝"""
        asyncio.create_task(self.check_fissures())


# 全局裂缝监控器实例
fissure_monitor = FissureMonitor()
