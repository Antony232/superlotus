# zariman_bounty_monitor.py - 扎里曼赏金任务监控器
import asyncio
import logging
import json
import os
from typing import List, Set
from managers.bounty_manager import bounty_manager
from nonebot import get_bot

logger = logging.getLogger(__name__)


class ZarimanBountyMonitor:
    """扎里曼赏金任务监控器"""

    def __init__(self):
        self.is_running = False
        self.check_interval = 300  # 5分钟检查一次（秒）
        self.bot = None
        self.notified_bounties: Set[str] = set()  # 记录已通知的赏金任务哈希，避免重复通知
        self.current_expiry = None  # 当前赏金轮换的过期时间，用于检测轮换更新

        # 持久化文件路径
        self.cache_file = os.path.join(os.path.dirname(__file__), '..', 'cache', 'zariman_bounty_cache.json')

        # 目标群聊列表（只在这些群聊中通知）
        self.target_groups = [813532268]

        # 目标节点
        self.target_node = "SolNode231"

        # 目标挑战列表（包含翻译键和challenge路径）
        self.target_challenges = [
            # 翻译键
            "/Lotus/Types/Challenges/Zariman/ZarimanExterminateFastCompleteChallenge",
            # challenge路径
            "/Lotus/Types/Challenges/Zariman/ZarimanUseVoidRiftsChallenge",
            "/Lotus/Types/Challenges/Zariman/ZarimanUseVoidRiftsEasyChallenge",
            "/Lotus/Types/Challenges/Zariman/ZarimanUseVoidRiftsHardChallenge",
            "/Lotus/Types/Challenges/Zariman/ZarimanDefeatVoidAngelChallenge"
        ]

        # 启动时加载缓存
        self._load_cache()

    def _load_cache(self):
        """从文件加载缓存"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.notified_bounties = set(data.get('notified_bounties', []))
                    self.current_expiry = data.get('current_expiry')
                    logger.info(f"📦 加载赏金通知缓存: {len(self.notified_bounties)} 条记录, 当前轮换: {self.current_expiry}")
        except Exception as e:
            logger.warning(f"加载赏金通知缓存失败: {e}")
            self.notified_bounties = set()
            self.current_expiry = None

    def _save_cache(self):
        """保存缓存到文件"""
        try:
            # 确保目录存在
            cache_dir = os.path.dirname(self.cache_file)
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)

            data = {
                'notified_bounties': list(self.notified_bounties),
                'current_expiry': self.current_expiry
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"💾 保存赏金通知缓存: {len(self.notified_bounties)} 条记录")
        except Exception as e:
            logger.warning(f"保存赏金通知缓存失败: {e}")

    def set_bot(self, bot):
        """设置bot实例"""
        self.bot = bot
        logger.debug(f"✅ 扎里曼赏金监控器已设置bot实例: {bot}")

    async def start(self):
        """启动监控"""
        if self.is_running:
            return

        self.is_running = True
        logger.debug("🚀 扎里曼赏金监控已启动")

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
        # 清除缓存，确保获取最新数据
        bounty_manager.clear_bounty_cache()

        # 获取赏金任务数据
        bounty_data = await bounty_manager.fetch_bounty_cycles()
        if not bounty_data:
            logger.warning("⚠️ 获取赏金任务失败")
            return

        # 检查赏金轮换是否更新
        new_expiry = bounty_data.get('expiry')
        if new_expiry != self.current_expiry:
            if self.current_expiry is not None:
                # 轮换已更新，清空已通知记录
                logger.info(f"🔄 赏金轮换已更新，清空通知记录 (旧: {self.current_expiry}, 新: {new_expiry})")
                self.notified_bounties.clear()
            else:
                # 首次加载（可能是重启后），使用缓存的记录
                logger.info(f"🚀 加载赏金数据，当前轮换过期时间: {new_expiry}")
            self.current_expiry = new_expiry
            self._save_cache()  # 保存轮换更新

        bounties = bounty_data.get('bounties', {})
        zariman_bounties = bounties.get('ZarimanSyndicate', [])

        if not zariman_bounties:
            logger.debug("📭 扎里曼暂无赏金任务")
            return

        logger.debug(f"🔍 检查扎里曼赏金任务（共{len(zariman_bounties)}个）")

        # 遍历所有赏金任务，检查每个是否符合条件
        notification_count = 0
        for index, bounty in enumerate(zariman_bounties):
            task_number = index + 1  # 任务序号（从1开始）

            node = bounty.get('node', '')
            challenge_path = bounty.get('challenge', '')

            # 检查是否匹配目标节点
            if node != self.target_node:
                logger.debug(f"🔍 第{task_number}个赏金节点不是目标: {node}")
                continue

            # 获取challenge的翻译键
            translation_key = bounty_manager._get_translation_key(challenge_path)

            # 检查是否匹配目标挑战
            is_target_challenge = (
                challenge_path in self.target_challenges or
                translation_key in self.target_challenges
            )

            if not is_target_challenge:
                logger.debug(f"🔍 第{task_number}个赏金挑战不是目标: {challenge_path}")
                continue

            # 生成唯一标识符用于去重
            bounty_hash = self._generate_bounty_hash(bounty)

            # 如果已经通知过，跳过
            if bounty_hash in self.notified_bounties:
                logger.debug(f"📭 第{task_number}个赏金任务已通知过: {bounty_hash}")
                continue

            # 构建通知消息（包含任务序号）
            notification = self._build_notification(bounty, task_number)

            # 发送通知到所有群聊
            await self._notify_groups(notification)

            # 记录已通知
            self.notified_bounties.add(bounty_hash)
            notification_count += 1
            logger.info(f"✅ 已发送扎里曼赏金任务通知: 第{task_number}个任务 ({bounty_hash})")

        # 如果有新通知，保存缓存
        if notification_count > 0:
            self._save_cache()

        if notification_count == 0:
            logger.debug("📭 本次检查未发现新的符合条件的赏金任务")

    def _generate_bounty_hash(self, bounty: dict) -> str:
        """生成赏金任务哈希值用于去重"""
        import hashlib
        node = bounty.get('node', '')
        challenge = bounty.get('challenge', '')
        # 使用节点和挑战路径生成唯一标识
        hash_str = f"{node}:{challenge}"
        return hashlib.md5(hash_str.encode()).hexdigest()

    def _build_notification(self, bounty: dict, task_number: int) -> str:
        """构建通知消息"""
        node = bounty.get('node', '')
        challenge_path = bounty.get('challenge', '')
        ally_path = bounty.get('ally', '')

        # 翻译节点名称
        node_name = bounty_manager._translate_node(node)

        # 获取挑战信息
        challenge_info = bounty_manager._get_challenge_info(challenge_path, ally_path)
        challenge_name = challenge_info.get('name', challenge_path)
        challenge_desc = challenge_info.get('description', '')

        # 构建通知消息（包含任务序号）
        notification = (
            f"🎉 扎里曼优质赏金提醒！（赏金{task_number}）\n"
            "================\n"
            f"📍 节点: {node_name}\n"
            f"🎯 任务: {challenge_name}\n"
            f"📝 描述: {challenge_desc}\n"
            "================\n"
            "💡 这是优质的哈拉科防线歼灭任务，建议速刷！"
        )

        return notification

    async def _notify_groups(self, message: str):
        """发送通知到指定群聊"""
        try:
            # 使用缓存的bot实例，如果为空则尝试获取
            if not self.bot:
                try:
                    self.bot = get_bot()
                except ValueError:
                    logger.warning("⚠️ 无法获取bot实例，bot可能尚未连接")
                    return

            if not self.bot:
                logger.warning("⚠️ bot实例为空")
                return

            # 发送到目标群聊
            success_count = 0
            fail_count = 0

            for group_id in self.target_groups:
                try:
                    await self.bot.send_group_msg(group_id=group_id, message=message)
                    success_count += 1
                    logger.info(f"✅ 已发送到群 {group_id}")
                except Exception as e:
                    fail_count += 1
                    logger.error(f"❌ 发送到群 {group_id} 失败: {e}")

            logger.info(f"📊 通知发送完成: 成功{success_count}个群, 失败{fail_count}个群")

        except Exception as e:
            logger.error(f"❌ 发送群通知异常: {e}", exc_info=True)


# 全局监控器实例
zariman_bounty_monitor = ZarimanBountyMonitor()
