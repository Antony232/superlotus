# core/api_manager.py
import aiohttp
import asyncio
import time
import random
from typing import Dict, List, Optional, Any
from config import config
from core.cache_manager import cache  # 导入缓存实例
import logging

logger = logging.getLogger(__name__)

class APIManager:
    def __init__(self) -> None:
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_lock: asyncio.Lock = asyncio.Lock()
        self.last_request_time: float = 0
        self.min_request_interval: float = 1.0 / config.wfm_api.get('rate_limit', 3)
        self.base_url: str = config.wfm_api.get('base_url', 'https://api.warframe.market/v2')
        self.headers: Dict[str, str] = {
            'User-Agent': 'WFM-Bot/1.0',
            'Platform': config.wfm_api.get('platform', 'pc'),
            'Crossplay': str(config.wfm_api.get('crossplay', True)).lower(),
            'Language': config.wfm_api.get('language', 'en'),
            'Accept': 'application/json'
        }

    async def ensure_session(self) -> None:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    async def rate_limit(self) -> None:
        """速率限制控制"""
        async with self.rate_limit_lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.min_request_interval:
                wait_time = self.min_request_interval - elapsed + random.uniform(0.1, 0.3)
                await asyncio.sleep(wait_time)
            self.last_request_time = time.time()

    async def request(self, method: str, endpoint: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
        """基础请求方法（保持原有逻辑）"""
        await self.rate_limit()
        await self.ensure_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            request_headers = self.headers.copy()
            if 'headers' in kwargs:
                request_headers.update(kwargs['headers'])
                del kwargs['headers']
            async with self.session.request(method, url, headers=request_headers, **kwargs) as response:
                if response.status == 429:
                    logger.warning("⚠️ 触发速率限制，等待5秒...")
                    await asyncio.sleep(5)
                    return await self.request(method, endpoint, **kwargs)
                if response.status == 509:
                    logger.warning("⚠️ 触发带宽限制，等待10秒...")
                    await asyncio.sleep(10)
                    return await self.request(method, endpoint, **kwargs)
                if response.status != 200:
                    logger.error(f"❌ API错误: {response.status}")
                    return None
                data = await response.json()
                if not isinstance(data, dict) or 'apiVersion' not in data:
                    logger.error("❌ 无效的API响应结构")
                    return None
                if data.get('error'):
                    logger.error(f"❌ API返回错误: {data['error']}")
                    return None
                return data.get('data')
        except aiohttp.ClientError as e:
            logger.error(f"❌ 网络错误: {e}")
            return None
        except asyncio.TimeoutError:
            logger.error("❌ 请求超时")
            return None
        except Exception as e:
            logger.error(f"❌ 请求异常: {e}")
            return None

    async def get_item_details(self, slug: str) -> Optional[Dict[str, Any]]:
        """获取物品详细信息（带缓存）"""
        # 先查询缓存
        cached_data = await cache.get("item_details", slug)
        if cached_data:
            logger.debug(f"✅ 从缓存获取物品详情: {slug}")
            return cached_data
        # 缓存未命中，调用API
        endpoint = f'/items/{slug}'
        response_data = await self.request('GET', endpoint)
        if response_data:
            await cache.set("item_details", response_data, slug)  # 写入缓存
        return response_data

    async def get_item_orders(self, slug: str, rank: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """获取物品订单（带缓存，支持等级参数）"""
        # 先查询缓存（rank作为缓存键一部分）
        cached_data = await cache.get("item_orders", slug, rank=rank)
        if cached_data:
            logger.debug(f"✅ 从缓存获取订单: {slug} (等级{rank})")
            return cached_data
        # 缓存未命中，调用API
        endpoint = f'/orders/item/{slug}/top'
        params: Dict[str, Any] = {}
        if rank is not None:
            params['rank'] = rank
        response_data = await self.request('GET', endpoint, params=params)
        if not response_data:
            return None
        sell_orders = response_data.get('sell', [])
        if sell_orders:
            rank_info = f" (等级{rank})" if rank is not None else ""
            logger.info(f"✅ 获取到 {len(sell_orders)} 个卖出订单{rank_info}")
            await cache.set("item_orders", sell_orders, slug, rank=rank)  # 写入缓存
        return sell_orders

# 全局API管理器实例
api_manager = APIManager()