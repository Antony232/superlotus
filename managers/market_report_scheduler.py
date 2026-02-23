"""
市场报告定时调度器 - 使用APScheduler实现精确调度
每周一10点自动发送市场报告
"""
import asyncio
import logging
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from services.market_report_service import market_report_service
from config import config

logger = logging.getLogger(__name__)

# 北京时区
BEIJING_TZ = timezone('Asia/Shanghai')


class MarketReportScheduler:
    """市场报告定时调度器 - 使用APScheduler实现精确调度"""

    def __init__(self):
        self.bot: Optional[object] = None
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.target_group: int = config.get_market_report_target_group()
        self._is_running: bool = False

    def set_bot(self, bot: object) -> None:
        """设置bot实例"""
        self.bot = bot
        logger.info(f"市场报告调度器已绑定bot，目标群: {self.target_group}")

    async def _send_weekly_report(self) -> None:
        """发送周报任务"""
        if not self.bot:
            logger.error("无法发送市场报告：bot实例未设置")
            return

        try:
            logger.info(f"开始发送PRIME市场周报到群 {self.target_group}")

            # 使用Service层获取完整报告（含图片）
            full_report = await market_report_service.get_report_with_images(force_refresh=True)

            if not full_report:
                logger.error("无法获取市场报告数据，取消发送")
                return

            # 发送图片
            from nonebot.adapters.onebot.v11 import Message, MessageSegment

            messages = [Message("📊 PRIME市场周报")]

            for idx, (title, image_path) in enumerate(full_report['images'], 1):
                msg = Message(f"图片{idx}/4: {title}")
                msg += MessageSegment.image(image_path.read_bytes())
                messages.append(msg)

            # 发送消息
            for msg in messages:
                await self.bot.call_api("send_group_msg", group_id=self.target_group, message=msg)
                await asyncio.sleep(0.5)  # 避免发送过快

            logger.info(f"PRIME市场周报发送成功到群 {self.target_group}")

        except Exception as e:
            logger.error(f"发送市场报告失败: {e}", exc_info=True)

    def start(self) -> None:
        """启动调度器"""
        if self._is_running:
            logger.warning("调度器已在运行")
            return

        if not config.is_auto_push_enabled():
            logger.info("市场报告自动推送已禁用，跳过启动调度器")
            return

        try:
            # 创建调度器
            self.scheduler = AsyncIOScheduler()

            # 配置cron触发器（每周一10:00）
            day_of_week = config.market_report_settings.get('schedule_day', 0)  # 0=周一, 1=周二, ..., 6=周日
            hour = config.market_report_settings.get('schedule_hour', 10)
            minute = config.market_report_settings.get('schedule_minute', 0)

            trigger = CronTrigger(
                day_of_week=day_of_week, 
                hour=hour, 
                minute=minute,
                timezone=BEIJING_TZ  # 使用北京时间
            )

            # 添加任务
            self.scheduler.add_job(
                self._send_weekly_report,
                trigger=trigger,
                id='market_weekly_report',
                name='PRIME市场周报',
                replace_existing=True
            )

            # 启动调度器
            self.scheduler.start()
            self._is_running = True

            # 将数字转换为中文星期几
            weekdays = ['一', '二', '三', '四', '五', '六', '日']
            weekday_str = weekdays[day_of_week] if 0 <= day_of_week <= 6 else f'未知({day_of_week})'
            logger.info(f"市场报告调度器已启动（每周{weekday_str} {hour:02d}:{minute:02d} 北京时间）")

        except Exception as e:
            logger.error(f"启动调度器失败: {e}", exc_info=True)

    def stop(self) -> None:
        """停止调度器"""
        if not self._is_running:
            return

        try:
            if self.scheduler:
                self.scheduler.shutdown()
                self.scheduler = None

            self._is_running = False
            logger.info("市场报告调度器已停止")

        except Exception as e:
            logger.error(f"停止调度器失败: {e}", exc_info=True)

    def is_running(self) -> bool:
        """检查调度器是否正在运行"""
        return self._is_running


# 全局调度器实例
market_report_scheduler = MarketReportScheduler()
