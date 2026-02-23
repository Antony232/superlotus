"""
统一世界状态客户端 - 单例模式
解决多个管理器重复请求同一 API 的性能问题
"""
import asyncio
import time
import logging
from typing import Dict, Optional, Callable, List, Any
from datetime import datetime, timedelta, timezone

import aiohttp

from core.constants import APIUrls, CacheTTL, Defaults

logger = logging.getLogger(__name__)


class WorldStateClient:
    """
    世界状态客户端（单例模式）
    
    功能：
    1. 统一获取世界状态数据
    2. 自动缓存管理
    3. 订阅者通知机制
    4. 异步请求优化
    """
    
    _instance: Optional['WorldStateClient'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._cache: Optional[Dict] = None
        self._cache_time: float = 0
        self._cache_ttl: int = CacheTTL.WORLD_STATE
        self._subscribers: List[Callable] = []
        self._session: Optional[aiohttp.ClientSession] = None
        self._fetch_lock = asyncio.Lock()
        self._initialized = True
        
        self._url = APIUrls.WORLD_STATE
        self._headers = {
            'User-Agent': 'Warframe-Status-Checker/1.0',
            'Accept': 'application/json'
        }
    
    @classmethod
    def get_instance(cls) -> 'WorldStateClient':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """确保 aiohttp session 可用"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=Defaults.REQUEST_TIMEOUT)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """关闭连接"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if self._cache is None:
            return False
        return (time.time() - self._cache_time) < self._cache_ttl
    
    async def fetch(self, force_refresh: bool = False) -> Optional[Dict]:
        """
        获取世界状态数据（带缓存）
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            世界状态数据字典，失败返回 None
        """
        # 检查缓存
        if not force_refresh and self._is_cache_valid():
            logger.debug("✅ 返回缓存的世界状态数据")
            return self._cache
        
        # 使用锁防止并发请求
        async with self._fetch_lock:
            # 双重检查
            if not force_refresh and self._is_cache_valid():
                return self._cache
            
            import json
            
            try:
                session = await self._ensure_session()
                
                logger.info("🌐 获取最新世界状态...")
                async with session.get(self._url, headers=self._headers) as response:
                    if response.status == 200:
                        # Warframe API 返回 text/html Content-Type，需要手动解析
                        text = await response.text()
                        data = json.loads(text)
                        self._cache = data
                        self._cache_time = time.time()
                        
                        # 通知所有订阅者
                        await self._notify_subscribers(data)
                        
                        logger.info("✅ 世界状态更新成功")
                        return data
                    else:
                        logger.error(f"❌ 获取世界状态失败: HTTP {response.status}")
                        # 返回过期缓存（如果有）
                        return self._cache
                        
            except aiohttp.ClientError as e:
                logger.error(f"❌ 网络错误: {e}")
                return self._cache
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON解析错误: {e}")
                return self._cache
            except asyncio.TimeoutError:
                logger.error("❌ 请求超时")
                return self._cache
            except Exception as e:
                logger.error(f"❌ 未知错误: {e}")
                return self._cache
    
    def subscribe(self, callback: Callable[[Dict], Any]) -> None:
        """
        订阅世界状态更新
        
        Args:
            callback: 回调函数，接收世界状态数据
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable) -> None:
        """取消订阅"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    async def _notify_subscribers(self, data: Dict) -> None:
        """通知所有订阅者"""
        for callback in self._subscribers:
            try:
                result = callback(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"❌ 订阅者回调错误: {e}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return {
            "has_cache": self._cache is not None,
            "cache_age": time.time() - self._cache_time if self._cache_time else 0,
            "cache_ttl": self._cache_ttl,
            "is_valid": self._is_cache_valid(),
            "subscriber_count": len(self._subscribers)
        }
    
    async def invalidate_cache(self) -> None:
        """使缓存失效"""
        async with self._fetch_lock:
            self._cache = None
            self._cache_time = 0


# 全局单例实例
world_state_client = WorldStateClient.get_instance()


# 便捷函数，兼容现有代码
async def fetch_world_state() -> Optional[Dict]:
    """
    获取世界状态数据（便捷函数）
    
    用于替换各管理器中独立的 fetch_world_state 方法
    """
    return await world_state_client.fetch()
