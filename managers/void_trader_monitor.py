# void_trader_monitor.py - 虚空商人监控器 - 重构版
"""
虚空商人监控器 - 使用统一的 WorldStateClient 和 time_utils
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict

from nonebot import get_bot

from core.world_state_client import world_state_client
from core.constants import Defaults, TimeZones
from utils.time_utils import parse_mongodb_timestamp, to_beijing_time

logger = logging.getLogger(__name__)


class VoidTraderMonitor:
    """虚空商人监控器"""

    def __init__(self):
        self.is_running = False
        self.check_interval = Defaults.REQUEST_TIMEOUT * 30  # 5分钟
        self.bot = None

        # 目标群聊列表
        self.target_groups = [Defaults.TARGET_GROUP]

        # 记录当前虚空商人的激活时间
        self.current_activation = None

        # 记录已通知的时间点
        self.notified_times_1day = False
        self.notified_times_12hours = False
        self.notified_times_30mins = False

    async def start(self):
        """启动监控"""
        if self.is_running:
            return

        self.is_running = True
        logger.info("🚀 虚空商人监控已启动")

        while self.is_running:
            try:
                await self.check_and_notify()
            except Exception as e:
                logger.error(f"❌ 检查虚空商人异常: {e}", exc_info=True)

            await asyncio.sleep(self.check_interval)

    async def stop(self):
        """停止监控"""
        self.is_running = False
        logger.info("🛑 虚空商人监控已停止")

    async def check_and_notify(self):
        """检查并发送虚空商人提醒"""
        # 使用统一的 WorldStateClient
        world_data = await world_state_client.fetch()
        if not world_data:
            logger.warning("⚠️ 获取世界状态失败")
            return

        void_traders = world_data.get('VoidTraders', [])
        if not void_traders:
            logger.debug("📭 暂无虚空商人数据")
            return

        trader = void_traders[0]

        # 使用统一的时间解析（返回UTC时间）
        activation_time_utc = parse_mongodb_timestamp(trader.get('Activation', {}))
        expiry_time_utc = parse_mongodb_timestamp(trader.get('Expiry', {}))

        if not activation_time_utc:
            logger.debug("📭 无法解析虚空商人激活时间")
            return

        # 转换为北京时间
        activation_time = to_beijing_time(activation_time_utc)
        activation_str = activation_time.strftime("%Y-%m-%d %H:%M:%S")

        # 检测是否为新的虚空商人到来
        if activation_str != self.current_activation:
            if self.current_activation is not None:
                logger.info(f"🔄 检测到新的虚空商人，清空通知记录")
            else:
                logger.debug(f"🚀 首次加载虚空商人数据，到达时间: {activation_str}")

            self.current_activation = activation_str
            self.notified_times_1day = False
            self.notified_times_12hours = False
            self.notified_times_30mins = False

        # 使用北京时间进行比较
        from datetime import timezone, timedelta
        beijing_tz = timezone(timedelta(hours=8))
        now_beijing = datetime.now(beijing_tz).replace(tzinfo=None)
        time_to_arrival = activation_time - now_beijing
        minutes_to_arrival = int(time_to_arrival.total_seconds() / 60)

        character = trader.get('Character', '虚空商人')
        node = trader.get('Node', '未知节点')
        node_name = self._translate_node(node)

        logger.debug(f"🔍 虚空商人检查: 距离到达还有 {minutes_to_arrival} 分钟")

        # 检查各个通知时间点
        await self._check_notification_point(
            minutes_to_arrival, 1440, 'notified_times_1day',
            character, node_name, activation_time, "1天"
        )

        await self._check_notification_point(
            minutes_to_arrival, 720, 'notified_times_12hours',
            character, node_name, activation_time, "12小时"
        )

        await self._check_notification_point(
            minutes_to_arrival, 30, 'notified_times_30mins',
            character, node_name, activation_time, "30分钟"
        )

    async def _check_notification_point(
        self,
        minutes_to_arrival: int,
        target_minutes: int,
        notified_attr: str,
        character: str,
        node_name: str,
        activation_time: datetime,
        time_desc: str
    ):
        """检查特定时间点并通知"""
        if abs(minutes_to_arrival - target_minutes) <= 5:
            if getattr(self, notified_attr):
                return

            activation_time_str = activation_time.strftime("%Y-%m-%d %H:%M:%S")
            notification = (
                f"🎫 虚空商人即将到来！\n"
                f"================\n"
                f"👤 商人: {character}\n"
                f"📍 地点: {node_name}\n"
                f"⏰ 到达时间: {activation_time_str} (北京时间)\n"
                f"⏳ 倒计时: {time_desc}\n"
                f"================\n"
                f"💡 准备好你的虚空币和遗产！"
            )

            await self._notify_groups(notification)
            setattr(self, notified_attr, True)
            logger.info(f"✅ 已发送虚空商人{time_desc}通知")

    def _translate_node(self, node: str) -> str:
        """翻译节点名称"""
        node_map = {
            "MercuryHUB": "水星中继站",
            "VenusHUB": "金星中继站",
            "EarthHUB": "地球中继站",
            "MarsHUB": "火星中继站",
            "JupiterHUB": "木星中继站",
            "SaturnHUB": "土星中继站",
            "UranusHUB": "天王星中继站",
            "NeptuneHUB": "海王星中继站",
            "PlutoHUB": "冥王星中继站",
            "CeresHUB": "谷神星中继站",
            "ErisHUB": "阋神星中继站",
            "SednaHUB": "赛德娜中继站",
            "EuropaHUB": "欧罗巴中继站",
            "PhobosHUB": "火卫一中继站",
            "VoidHUB": "虚空中继站",
        }
        return node_map.get(node, node)

    async def _notify_groups(self, message: str):
        """发送通知到指定群聊"""
        try:
            bot = get_bot()
            if not bot:
                logger.warning("⚠️ 无法获取bot实例")
                return

            success_count = 0
            for group_id in self.target_groups:
                try:
                    await bot.send_group_msg(group_id=group_id, message=message)
                    success_count += 1
                    logger.info(f"✅ 已发送到群 {group_id}")
                except Exception as e:
                    logger.error(f"❌ 发送到群 {group_id} 失败: {e}")

        except Exception as e:
            logger.error(f"❌ 发送群通知异常: {e}", exc_info=True)


# 全局监控器实例
void_trader_monitor = VoidTraderMonitor()
