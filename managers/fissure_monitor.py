# fissure_monitor.py - 裂缝监控器
import asyncio
import time
from typing import List, Dict
from nonebot import get_bot
from managers.game_status_manager import game_status_manager
from managers.subscription_manager import subscription_manager, FissureSubscription
from managers.translation_manager import translator  # 使用统一的翻译管理器
from utils.game_status_config import game_status_config
import logging

logger = logging.getLogger(__name__)


class FissureMonitor:
    """裂缝监控器"""
    
    def __init__(self, check_interval: int = 300):  # 默认5分钟检查一次
        self.check_interval = check_interval
        self.running = False
        self.last_fissures = []  # 上次检查的裂缝列表
    
    async def start(self):
        """启动监控"""
        if self.running:
            return

        self.running = True
        logger.debug("🚀 启动裂缝订阅监控...")
        
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
            # 获取世界状态数据
            data = await game_status_manager.fetch_world_state()
            if not data:
                return
            
            # 获取裂缝列表
            fissures = data.get('ActiveMissions', [])
            current_fissures = []
            
            # 处理裂缝数据
            for fissure in fissures:
                fissure_id = subscription_manager.generate_fissure_id(fissure)
                current_fissures.append((fissure_id, fissure))
            
            # 找出新出现的裂缝
            new_fissures = []
            current_ids = {fid for fid, _ in current_fissures}
            last_ids = {fid for fid, _ in self.last_fissures}
            
            new_ids = current_ids - last_ids
            
            for fissure_id, fissure in current_fissures:
                if fissure_id in new_ids:
                    new_fissures.append((fissure_id, fissure))
            
            # 检查新裂缝是否匹配订阅
            for fissure_id, fissure in new_fissures:
                # 检查是否已通知过
                if subscription_manager.is_fissure_notified(fissure_id):
                    continue
                
                # 匹配订阅
                await self.match_and_notify(fissure_id, fissure)
            
            # 更新上次裂缝列表
            self.last_fissures = current_fissures
            
        except Exception as e:
            logger.error(f"❌ 检查裂缝失败: {e}")
    
    async def match_and_notify(self, fissure_id: str, fissure: dict):
        """匹配订阅并发送通知"""
        try:
            # 提取裂缝信息
            node = fissure.get('Node', '未知节点')
            mission_type = fissure.get('MissionType', '未知类型')
            is_hard = fissure.get('Hard', False)
            tier = fissure.get('Modifier', '未知等级')
            expiry = fissure.get('Expiry', {}).get('$date', {}).get('$numberLong')
            
            # 获取翻译 - 使用游戏状态翻译器
            node_name = translator.translate_node(node)
            mission_type_translated = translator.translate_mission_type(mission_type)
            
            # 提取星球信息
            planet = self._extract_planet(node_name)
            
            # 转换等级名称
            tier_name = game_status_config.fissure_tiers.get(tier, tier.replace('VoidT', 'T'))
            
            # 计算剩余时间
            time_left = game_status_manager.calculate_time_left(expiry)
            
            # 准备通知消息
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
            
            # 查找匹配的订阅
            matched_subs = []
            for sub in subscription_manager.subscriptions:
                if self._match_subscription(sub, fissure_info):
                    matched_subs.append(sub)
            
            # 发送通知
            if matched_subs:
                await self.send_notifications(fissure_info, matched_subs)
                subscription_manager.mark_fissure_as_notified(fissure_id)
                
                # 更新订阅的最后通知时间
                for sub in matched_subs:
                    sub.last_notified_time = time.time()
                subscription_manager.save_subscriptions()
                
                logger.info(f"📢 发送裂缝通知: {mission_type_translated} @ {node_name} ({planet})，匹配 {len(matched_subs)} 个订阅")
    
        except Exception as e:
            logger.error(f"❌ 匹配裂缝通知失败: {e}")
    
    def _match_subscription(self, sub: FissureSubscription, fissure_info: dict) -> bool:
        """检查裂缝是否匹配订阅条件"""
        # 匹配任务类型
        mission_match = (sub.mission_type == fissure_info['mission_type'] or
                        sub.mission_type == fissure_info['mission_type_en'])

        # 匹配难度
        difficulty_match = False
        if sub.difficulty == 'both':
            difficulty_match = True
        elif sub.difficulty == 'steel':
            difficulty_match = (fissure_info['difficulty'] == 'steel')
        elif sub.difficulty == 'normal':
            difficulty_match = (fissure_info['difficulty'] == 'normal')

        # 匹配等级
        tier_match = False
        if sub.tier == 'all':
            tier_match = True
        else:
            tier_match = (sub.tier == fissure_info['tier'] or
                         sub.tier == fissure_info['tier_en'])

        # 匹配星球
        planet_match = False
        if sub.planet == 'all':
            planet_match = True
        else:
            planet_match = (sub.planet == fissure_info['planet'])

        # 匹配具体节点
        node_match = True
        if sub.node_filter:
            # 检查节点路径是否包含过滤词
            node_match = (sub.node_filter in fissure_info['node_path'] or
                         sub.node_filter.lower() in fissure_info['node'].lower() or
                         sub.node_filter in fissure_info['node'])

        return mission_match and difficulty_match and tier_match and planet_match and node_match

    def _extract_planet(self, node_name: str) -> str:
        """从节点名称中提取星球名称"""
        # 使用配置文件中的星球列表
        for planet in game_status_config.planets_cn + game_status_config.planets_en:
            if planet in node_name:
                return planet

        # 尝试使用翻译器
        translated = translator.translate_text(node_name)
        for planet in game_status_config.planets_cn:
            if planet in translated:
                return planet

        return "未知星球"
    
    async def send_notifications(self, fissure_info: dict,
                                subscriptions: List[FissureSubscription]):
        """发送通知给订阅者"""
        try:
            bot = get_bot()

            # 按群组分组订阅
            subs_by_group = {}
            for sub in subscriptions:
                if sub.group_id not in subs_by_group:
                    subs_by_group[sub.group_id] = []
                subs_by_group[sub.group_id].append(sub)

            # 为每个群组发送通知
            for group_id, group_subs in subs_by_group.items():
                # 提取用户ID
                user_ids = [sub.user_id for sub in group_subs]

                # 构建消息
                if fissure_info['difficulty'] == 'steel':
                    difficulty_text = "钢铁"
                else:
                    difficulty_text = "普通"

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

                # 添加@用户
                at_users = " ".join([f"[CQ:at,qq={uid}]" for uid in user_ids])
                full_message = at_users + "\n" + message

                # 发送消息
                await bot.send_group_msg(group_id=int(group_id), message=full_message)

                # 避免发送频率过高
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"❌ 发送通知失败: {e}")
    
    def force_check(self):
        """强制立即检查裂缝"""
        asyncio.create_task(self.check_fissures())


# 全局裂缝监控器实例
fissure_monitor = FissureMonitor()
