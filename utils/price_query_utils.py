# utils/price_query_utils.py
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field
from core.api_manager import api_manager
from managers.translation_manager import translation_manager
import logging

logger = logging.getLogger(__name__)

@dataclass
class PriceQueryResult:
    """价格查询结果封装"""
    english_slug: Optional[str] = None
    orders: List[Dict] = field(default_factory=list)  # 普通物品订单或赋能0级订单
    max_rank_orders: List[Dict] = field(default_factory=list)  # 赋能满级订单
    is_arcane: bool = False
    max_rank: int = 5
    success: bool = False

async def query_item_price(original_query: str) -> PriceQueryResult:
    """
    公共价格查询逻辑
    返回：PriceQueryResult 对象
    """
    result = PriceQueryResult()
    
    # 翻译查询词
    english_slug, is_translated = translation_manager.translate(original_query)
    if not english_slug:
        logger.warning(f"无法识别物品名称: {original_query}")
        return result

    result.english_slug = english_slug

    # 判断是否为赋能
    item_details = await api_manager.get_item_details(english_slug)
    result.max_rank = 5
    
    if item_details:
        tags = item_details.get('tags', [])
        result.is_arcane = any("arcane" in tag.lower() for tag in tags)
        result.max_rank = item_details.get('maxRank', 5)

    # 获取订单数据
    if result.is_arcane:
        result.orders = await api_manager.get_item_orders(english_slug, rank=0) or []
        result.max_rank_orders = await api_manager.get_item_orders(english_slug, rank=result.max_rank) or []
        
        # 兜底逻辑
        if not result.max_rank_orders:
            fallback_ranks = [3, 5] if result.max_rank not in [3, 5] else []
            for fallback_rank in fallback_ranks:
                max_rank_orders = await api_manager.get_item_orders(english_slug, rank=fallback_rank)
                if max_rank_orders:
                    result.max_rank = fallback_rank
                    result.max_rank_orders = max_rank_orders
                    break
        
        result.success = True
        return result
    else:
        # 普通物品/套装
        sell_orders = await api_manager.get_item_orders(english_slug)
        
        # 尝试添加后缀
        if not sell_orders:
            if english_slug.endswith('_blueprint'):
                base_slug = english_slug[:-10]
                sell_orders = await api_manager.get_item_orders(base_slug)
                if sell_orders:
                    result.english_slug = base_slug
                    english_slug = base_slug
            
            if not sell_orders and not english_slug.endswith('_set'):
                new_slug, new_orders = await _try_with_suffix(english_slug, '_set')
                if new_orders:
                    result.english_slug = new_slug
                    sell_orders = new_orders

        result.orders = sell_orders or []
        result.success = bool(result.orders)
        return result

async def _try_with_suffix(original_slug: str, suffix: str) -> Tuple[str, List[Dict]]:
    """尝试添加后缀查询（复用原有逻辑）"""
    new_slug = f"{original_slug}{suffix}"
    logger.info(f"尝试添加{suffix}后缀: '{new_slug}'")
    orders = await api_manager.get_item_orders(new_slug)
    return new_slug, orders