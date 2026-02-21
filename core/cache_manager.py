# cache_manager.py - 启用缓存（物品详情+订单数据）
import json
import hashlib
import os
import time
from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, cache_dir: str = "./cache") -> None:
        self.cache_dir: Path = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.item_details_ttl: int = 3600  # 物品详情缓存1小时（长期不变）
        self.orders_ttl: int = 300  # 订单数据缓存5分钟（实时性要求高）

    def _get_cache_key(self, key_prefix: str, *args, **kwargs) -> str:
        """生成唯一缓存键（避免冲突）"""
        key_parts: list = [key_prefix] + [str(arg) for arg in args]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        key_str: str = "_".join(key_parts)
        # MD5加密确保键名简洁
        return hashlib.md5(key_str.encode()).hexdigest() + ".json"

    async def get(self, key_prefix: str, *args, **kwargs) -> Optional:
        """获取缓存数据"""
        cache_file: Path = self.cache_dir / self._get_cache_key(key_prefix, *args, **kwargs)
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            # 检查缓存是否过期
            if time.time() - cache_data["timestamp"] > self._get_ttl(key_prefix):
                os.remove(cache_file)  # 删除过期缓存
                return None
            return cache_data["content"]
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
            return None

    async def set(self, key_prefix: str, data, *args, **kwargs) -> None:
        """写入缓存数据"""
        if not data:  # 空数据不缓存
            return
        cache_file: Path = self.cache_dir / self._get_cache_key(key_prefix, *args, **kwargs)
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": time.time(),
                    "content": data
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"写入缓存失败: {e}")

    def _get_ttl(self, key_prefix: str) -> int:
        """根据key前缀获取对应过期时间"""
        if key_prefix == "item_details":
            return self.item_details_ttl
        elif key_prefix == "item_orders":
            return self.orders_ttl
        return 300  # 默认5分钟

    async def clear_expired(self) -> None:
        """清理所有过期缓存（启动/关闭时执行）"""
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                # 超过1小时的缓存强制清理
                if time.time() - cache_data["timestamp"] > 3600:
                    cache_file.unlink()
            except Exception:
                cache_file.unlink()  # 损坏缓存直接删除

# 全局缓存实例
cache = CacheManager()