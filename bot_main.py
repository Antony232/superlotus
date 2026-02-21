# bot_main.py - Warframe机器人主入口
import os
import nonebot
from nonebot import get_driver
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

# 设置当前工作目录到项目根目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 统一日志配置
from core.logger_config import setup_logger
logger = setup_logger()

# 导入配置和基础管理器（不初始化NoneBot）
from config import config
from core.cache_manager import cache
from core.api_manager import api_manager
from managers.translation_manager import translation_manager, translator
from managers.game_status_manager import game_status_manager
from managers.fissure_monitor import fissure_monitor
from managers.bounty_manager import bounty_manager
from managers.zariman_bounty_monitor import zariman_bounty_monitor
from managers.void_trader_monitor import void_trader_monitor

# 初始化NoneBot
nonebot.init()
driver = get_driver()
driver.register_adapter(OneBotV11Adapter)  # type: ignore[arg-type]

# 加载翻译数据
_ = translation_manager.load_translations()
_ = translator.load_translations()

# 导入命令处理器
import handlers.interaction.help_handler  # noqa: F401
import handlers.price.wm_handler  # noqa: F401
import handlers.price.market_report_handler  # noqa: F401
import handlers.interaction.at_handler  # noqa: F401
import handlers.game_status.game_status_handler  # noqa: F401
import handlers.game_status.endless_road_handler  # noqa: F401
import handlers.game_status.nightwave_handler  # noqa: F401
import handlers.subscription.fissure_subscription_handler  # noqa: F401
import handlers.subscription.bounty_handler  # noqa: F401
import handlers.archimedea.archimedea_handler  # noqa: F401
import handlers.temporal_archimedea.temporal_archimedea_handler  # noqa: F401
import handlers.research.research_handler  # noqa: F401
import handlers.game_status.calendar_handler  # noqa: F401
import handlers.game_status.void_trader_handler  # noqa: F401

# 启动任务
@driver.on_startup
async def startup() -> None:
    """启动时初始化"""
    _ = bounty_manager.load_data()
    import asyncio
    _ = asyncio.create_task(fissure_monitor.start())
    _ = asyncio.create_task(zariman_bounty_monitor.start())
    _ = asyncio.create_task(void_trader_monitor.start())
    logger.info("🚀 所有监控器已启动")


# 市场报告调度器（在bot初始化完成后启动）
@driver.on_bot_connect
async def on_bot_connect(bot) -> None:
    """当bot连接成功后初始化市场报告调度器"""
    from managers.market_report_scheduler import market_report_scheduler

    # 设置扎里曼赏金监控器的bot实例
    zariman_bounty_monitor.set_bot(bot)
    logger.info("✅ 扎里曼赏金监控器已设置bot实例")

    if not config.is_market_report_enabled():
        logger.info("市场报告功能已禁用")
        return

    market_report_scheduler.set_bot(bot)
    market_report_scheduler.start()
    logger.info("📊 市场报告调度器已启动")

# 清理任务
@driver.on_shutdown
async def shutdown() -> None:
    """关闭时清理资源"""
    await fissure_monitor.stop()
    await zariman_bounty_monitor.stop()
    await void_trader_monitor.stop()
    await api_manager.close()
    await game_status_manager.close()
    await cache.clear_expired()
    logger.info("🐱 超级小莲已安全退出")

# 启动
if __name__ == "__main__":
    bot_name: str = config.personality.get('name', '超级小莲')
    platform: str = config.wfm_api.get('platform', 'pc')
    bot_qq = config.get_bot_qq_number()

    logger.info(f"🐱 {bot_name} 启动中...")
    logger.info(f"✨ 版本: 猫娘@回应版 v8.0 (游戏状态查询整合+裂缝订阅)")
    logger.info(f"📞 QQ: {bot_qq} | 🌐 API: {config.wfm_api.get('base_url')} | 🔧 平台: {platform}")
    logger.info("=" * 60)

    nonebot.run(host="0.0.0.0", port=8080)
