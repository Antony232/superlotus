"""
市场数据管理器 - 负责每天一次抓取和缓存市场数据
"""
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any
from analyze_price_statistics import PrimeMarketReport
from dataclasses import asdict

logger = logging.getLogger(__name__)


class MarketDataManager:
    """市场数据管理器 - 每天24小时缓存一次数据"""

    CACHE_FILE: str = "data/market_report_cache.json"
    CACHE_DURATION: timedelta = timedelta(hours=24)  # 24小时缓存

    def __init__(self):
        self._cache_data: Optional[Dict[str, Any]] = None
        self._cache_time: Optional[datetime] = None
        self._fetch_lock = asyncio.Lock()

    def _load_cache_from_file(self) -> tuple[Optional[Dict[str, Any]], Optional[datetime]]:
        """从文件加载缓存"""
        try:
            cache_file = Path(self.CACHE_FILE)
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cached_time_str = data.get('cached_time', '2000-01-01T00:00:00')
                    cached_time = datetime.fromisoformat(cached_time_str)
                    return data, cached_time
        except Exception as e:
            logger.warning(f"加载缓存文件失败: {e}")
        return None, None

    def _save_cache_to_file(self, data: Dict[str, Any]) -> None:
        """保存缓存到文件"""
        try:
            data['cached_time'] = datetime.now().isoformat()
            Path(self.CACHE_FILE).parent.mkdir(parents=True, exist_ok=True)
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"市场数据缓存已保存: {self.CACHE_FILE}")
        except Exception as e:
            logger.error(f"保存缓存文件失败: {e}")

    def is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if self._cache_time is None:
            return False
        return datetime.now() - self._cache_time < self.CACHE_DURATION

    async def get_market_report(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        获取市场报告数据
        
        Args:
            force_refresh: 是否强制刷新
            
        Returns:
            市场报告数据（四维排名）
        """
        # 1. 尝试从内存缓存获取 (快速路径)
        if not force_refresh and self._cache_data is not None and self.is_cache_valid():
            logger.info("使用内存缓存的市场数据")
            return self._cache_data.get('rankings')

        # 2. 尝试从文件缓存获取
        if not force_refresh:
            file_cache, cache_time = self._load_cache_from_file()
            if file_cache and cache_time and (datetime.now() - cache_time < self.CACHE_DURATION):
                self._cache_data = file_cache
                self._cache_time = cache_time
                logger.info(f"使用文件缓存的市场数据 (缓存于: {cache_time})")
                return file_cache.get('rankings')

        # 3. 需要刷新数据 (加锁防止并发刷新)
        async with self._fetch_lock:
            # 双重检查锁：再次检查内存缓存，防止其他协程已经刷新完成
            if not force_refresh and self._cache_data is not None and self.is_cache_valid():
                logger.info("使用刚刚刷新好的内存缓存数据")
                return self._cache_data.get('rankings')

            return await self._refresh_data()

    async def _refresh_data(self) -> Optional[Dict[str, Any]]:
        """从API刷新数据"""
        try:
            logger.info("开始抓取市场数据...")
            async with PrimeMarketReport() as analyzer:
                results = await analyzer.analyze_all()

                if not results:
                    logger.error("市场数据抓取失败: 无有效数据")
                    return None

                logger.info(f"成功分析 {len(results)} 个物品")
                rankings = analyzer.generate_rankings(results)

                # 将PrimeItemData对象转换为字典（用于JSON序列化）
                export_dict: Dict[str, Any] = {}
                for dim, types in rankings.items():
                    export_dict[dim] = {}
                    for type_name, items in types.items():
                        export_dict[dim][type_name] = [asdict(item) for item in items]

                # 保存到内存和文件
                self._cache_data = {'rankings': export_dict}
                self._cache_time = datetime.now()
                self._save_cache_to_file(self._cache_data)

                logger.info("市场数据刷新完成")
                return export_dict  # 返回转换后的字典

        except Exception as e:
            logger.error(f"抓取市场数据异常: {e}", exc_info=True)
            # 如果有旧缓存，继续使用
            if self._cache_data:
                logger.warning("使用旧的缓存数据")
                return self._cache_data.get('rankings')
            return None

    async def ensure_data_ready(self):
        """确保数据已准备就绪（用于启动时预加载）"""
        logger.info("预加载市场数据...")
        await self.get_market_report()


# 全局单例
market_data_manager = MarketDataManager()
