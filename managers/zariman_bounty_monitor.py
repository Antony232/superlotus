# zariman_bounty_monitor.py - 扎里曼赏金任务监控器 - 重构版
"""
扎里曼赏金任务监控器 - 使用统一的 WorldStateClient
"""
import asyncio
import logging
import json
import hashlib
import os
from typing import Set

from nonebot import get_bot

from core.constants import Defaults
from managers.bounty_manager import bounty_manager

logger = logging.getLogger(__name__)


class ZarimanBountyMonitor:
    """扎里曼赏金任务监控器"""

    def __init__(self):
        self.is_running = False
        self.check_interval = Defaults.REQUEST_TIMEOUT * 30  # 5分钟
        self.bot = None
        self.notified_bounties: Set[str] = set()
        self.current_expiry = None

        # 持久化文件路径
        self.cache_file = os.path.join(
            os.path.dirname(__file__), '..', 'cache', 'zariman_bounty_cache.json'
        )

        # 目标群聊列表
        self.target_groups = [Defaults.TARGET_GROUP]

        # 目标节点
        self.target_node = "SolNode231"

        # 目标挑战列表
        self.target_challenges = [
            "/Lotus/Types/Challenges/Zariman/ZarimanExterminateFastCompleteChallenge",
            "/Lotus/Types/Challenges/Zariman/ZarimanUseVoidRiftsChallenge",
            "/Lotus/Types/Challenges/Zariman/ZarimanUseVoidRiftsEasyChallenge",
            "/Lotus/Types/Challenges/Zariman/ZarimanUseVoidRiftsHardChallenge",
            "/Lotus/Types/Challenges/Zariman/ZarimanDefeatVoidAngelChallenge"
        ]

        self._load_cache()

    def _load_cache(self):
        """从文件加载缓存"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.notified_bounties = set(data.get('notified_bounties', []))
                    self.current_expiry = data.get('current_expiry')
                    logger.debug(f"📦 加载赏金通知缓存: {len(self.notified_bounties)} 条记录")
        except Exception as e:
            logger.warning(f"加载赏金通知缓存失败: {e}")
            self.notified_bounties = set()
            self.current_expiry = None

    def _save_cache(self):
        """保存缓存到文件"""
        try:
            cache_dir = os.path.dirname(self.cache_file)
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)

            data = {
                'notified_bounties': list(self.notified_bounties),
                'current_expiry': self.current_expiry
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存赏金通知缓存失败: {e}")

    def set_bot(self, bot):
        """设置bot实例"""
        self.bot = bot

    async def start(self):
        """启动监控"""
        if self.is_running:
            return

        self.is_running = True
        logger.info("🚀 扎里曼赏金监控已启动")

        while self.is_running:
            try:
                await self.check_and_notify()
            except Exception as e:
                logger.error(f"❌ 检查扎里曼赏金任务异常: {e}", exc_info=True)

            await asyncio.sleep(self.check_interval)

    async def stop(self):
        """停止监控"""
        self.is_running = False
        logger.info("🛑 扎里曼赏金监控已停止")

    async def check_and_notify(self):
        """检查并通知符合条件的赏金任务"""
        bounty_manager.clear_bounty_cache()
        bounty_data = await bounty_manager.fetch_bounty_cycles()
        
        if not bounty_data:
            logger.warning("⚠️ 获取赏金任务失败")
            return

        new_expiry = bounty_data.get('expiry')
        if new_expiry != self.current_expiry:
            if self.current_expiry is not None:
                logger.info(f"🔄 赏金轮换已更新，清空通知记录")
                self.notified_bounties.clear()
            self.current_expiry = new_expiry
            self._save_cache()

        bounties = bounty_data.get('bounties', {})
        zariman_bounties = bounties.get('ZarimanSyndicate', [])

        if not zariman_bounties:
            return

        notification_count = 0
        for index, bounty in enumerate(zariman_bounties):
            task_number = index + 1
            node = bounty.get('node', '')
            challenge_path = bounty.get('challenge', '')

            if node != self.target_node:
                continue

            translation_key = bounty_manager._get_translation_key(challenge_path)
            is_target_challenge = (
                challenge_path in self.target_challenges or
                translation_key in self.target_challenges
            )

            if not is_target_challenge:
                continue

            bounty_hash = self._generate_bounty_hash(bounty)
            if bounty_hash in self.notified_bounties:
                continue

            notification = self._build_notification(bounty, task_number)
            await self._notify_groups(notification)

            self.notified_bounties.add(bounty_hash)
            notification_count += 1
            logger.info(f"✅ 已发送扎里曼赏金任务通知: 第{task_number}个任务")

        if notification_count > 0:
            self._save_cache()

    def _generate_bounty_hash(self, bounty: dict) -> str:
        """生成赏金任务哈希值"""
        node = bounty.get('node', '')
        challenge = bounty.get('challenge', '')
        hash_str = f"{node}:{challenge}"
        return hashlib.md5(hash_str.encode()).hexdigest()

    def _build_notification(self, bounty: dict, task_number: int) -> str:
        """构建通知消息"""
        node = bounty.get('node', '')
        challenge_path = bounty.get('challenge', '')
        ally_path = bounty.get('ally', '')

        node_name = bounty_manager._translate_node(node)
        challenge_info = bounty_manager._get_challenge_info(challenge_path, ally_path)
        challenge_name = challenge_info.get('name', challenge_path)
        challenge_desc = challenge_info.get('description', '')

        return (
            f"🎉 扎里曼优质赏金提醒！（赏金{task_number}）\n"
            "================\n"
            f"📍 节点: {node_name}\n"
            f"🎯 任务: {challenge_name}\n"
            f"📝 描述: {challenge_desc}\n"
            "================\n"
            "💡 这是优质的哈拉科防线歼灭任务，建议速刷！"
        )

    async def _notify_groups(self, message: str):
        """发送通知到指定群聊"""
        try:
            if not self.bot:
                try:
                    self.bot = get_bot()
                except ValueError:
                    logger.warning("⚠️ 无法获取bot实例")
                    return

            for group_id in self.target_groups:
                try:
                    await self.bot.send_group_msg(group_id=group_id, message=message)
                    logger.info(f"✅ 已发送到群 {group_id}")
                except Exception as e:
                    logger.error(f"❌ 发送到群 {group_id} 失败: {e}")

        except Exception as e:
            logger.error(f"❌ 发送群通知异常: {e}", exc_info=True)


# 全局监控器实例
zariman_bounty_monitor = ZarimanBountyMonitor()
