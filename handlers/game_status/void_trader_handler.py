"""
虚空商人命令处理器
处理 /商人 和 /虚空商人 命令
"""

import json
from typing import Optional, Dict, List, Any
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from managers.game_status_manager import game_status_manager
from core.translators.void_trader_translator import void_trader_translator
from utils.text_to_image import text_to_image
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

# 注册命令处理器
void_trader_handler = on_command(
    "商人",
    aliases={"虚空商人"},
    priority=15,
    block=True
)

# ==================== 缓存管理 ====================

class VoidTraderCache:
    """虚空商人缓存管理器"""
    
    def __init__(self):
        # 缓存结构: {activation_timestamp: {info: {}, items: []}}
        self._cache: Dict[str, Dict[str, Any]] = {}
        # 当前激活的缓存键
        self._current_activation: Optional[str] = None
    
    def get_cache(self, activation_ts: str) -> Optional[Dict[str, Any]]:
        """获取缓存"""
        return self._cache.get(activation_ts)
    
    def set_cache(self, activation_ts: str, data: Dict[str, Any]) -> None:
        """设置缓存"""
        self._cache[activation_ts] = data
        self._current_activation = activation_ts
        logger.info(f"虚空商人缓存已更新: {activation_ts}")
    
    def clear_expired_cache(self, current_activation: str) -> None:
        """清除过期缓存"""
        # 清除非当前商人的缓存
        keys_to_remove = [k for k in self._cache.keys() if k != current_activation]
        for key in keys_to_remove:
            del self._cache[key]
            logger.info(f"已清除过期缓存: {key}")
        
        self._current_activation = current_activation


# 全局缓存实例
_void_trader_cache = VoidTraderCache()

# ==================== 节点翻译 ====================

_node_translations: dict = None


def load_node_translations() -> dict:
    """加载节点翻译数据"""
    global _node_translations
    if _node_translations is not None:
        return _node_translations
    
    try:
        with open('data/game_data/solNodes.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        _node_translations = {}
        for key, value in data.items():
            if isinstance(value, dict) and 'value' in value:
                _node_translations[key] = value['value']
        return _node_translations
    except Exception as e:
        logger.error(f"加载节点翻译数据失败: {e}")
        return {}


def translate_node(node: str) -> str:
    """翻译节点名称"""
    translations = load_node_translations()
    return translations.get(node, node)

# ==================== 时间处理 ====================


def parse_timestamp(ts_data: dict) -> Optional[datetime]:
    """解析MongoDB时间戳"""
    try:
        date_data = ts_data.get('$date', {})
        timestamp_ms = date_data.get('$numberLong')
        if timestamp_ms:
            return datetime.utcfromtimestamp(int(timestamp_ms) / 1000)
    except:
        pass
    return None


def format_time_remaining(expiry_utc: datetime) -> str:
    """计算并格式化剩余时间"""
    now_utc = datetime.utcnow()
    time_diff = expiry_utc - now_utc
    
    if time_diff.total_seconds() <= 0:
        return "已离开"
    
    total_seconds = int(time_diff.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    
    if days > 0:
        return f"{days}天{hours}小时"
    elif hours > 0:
        return f"{hours}小时{minutes}分钟"
    else:
        return f"{minutes}分钟"


def format_arrival_time(activation_utc: datetime) -> tuple[str, str]:
    """格式化到达时间和倒计时"""
    beijing_tz = timezone(timedelta(hours=8))
    activation_beijing = activation_utc.replace(tzinfo=timezone.utc).astimezone(beijing_tz)
    time_str = activation_beijing.strftime("%Y-%m-%d %H:%M:%S")
    
    now_utc = datetime.utcnow()
    time_diff = activation_utc - now_utc
    
    if time_diff.total_seconds() <= 0:
        countdown = "已到达"
    else:
        total_seconds = int(time_diff.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        if days > 0:
            countdown = f"{days}天{hours}小时"
        elif hours > 0:
            countdown = f"{hours}小时{minutes}分钟"
        else:
            countdown = f"{minutes}分钟"
    
    return time_str, countdown

# ==================== 数据处理 ====================


def build_trader_info(trader: dict) -> Dict[str, Any]:
    """构建商人基础信息"""
    character = trader.get('Character', '虚空商人')
    node = trader.get('Node', '未知节点')
    node_name = translate_node(node)
    activation = parse_timestamp(trader.get('Activation', {}))
    expiry = parse_timestamp(trader.get('Expiry', {}))
    
    return {
        'character': character,
        'node': node_name,
        'activation': activation,
        'expiry': expiry,
        'is_active': activation and datetime.utcnow() >= activation if activation else False
    }


def translate_manifest(manifest: List[dict]) -> List[Dict[str, Any]]:
    """翻译商品列表"""
    void_trader_translator.load_data()
    translated_items = void_trader_translator.translate_manifest(manifest)
    
    result = []
    for item in translated_items:
        name = item['name_zh'] if item['name_zh'] else item['keyword']
        result.append({
            'name': name,
            'ducat': item['primePrice'],
            'credit': item['regularPrice']
        })
    
    return result

# ==================== 响应格式化 ====================


def get_display_width(s: str) -> int:
    """计算字符串的显示宽度（中文字符算2，英文/数字算1）"""
    width = 0
    for char in s:
        # 中文字符和全角字符的 Unicode 范围
        if '\u4e00' <= char <= '\u9fff' or '\u3000' <= char <= '\u303f' or '\uff00' <= char <= '\uffef':
            width += 2
        else:
            width += 1
    return width


def pad_to_width(s: str, width: int, align: str = 'left') -> str:
    """将字符串填充到指定显示宽度"""
    current_width = get_display_width(s)
    padding = width - current_width
    
    if padding <= 0:
        return s
    
    if align == 'right':
        return ' ' * padding + s
    else:  # left
        return s + ' ' * padding


def format_response(info: Dict[str, Any], items: Optional[List[Dict[str, Any]]] = None) -> str:
    """格式化响应文本 - 结构化输出"""
    lines = []
    
    # T1: 标题
    lines.append("【虚空商人】")
    lines.append("=" * 40)
    
    # T2: 商人信息
    lines.append(f"  商人: {info['character']}")
    lines.append(f"  节点: {info['node']}")
    
    if info['is_active']:
        # 商人已到达
        remaining = format_time_remaining(info['expiry']) if info['expiry'] else "未知"
        lines.append(f"  剩余时间: {remaining}")
        
        # T3: 商品列表
        if items:
            lines.append("")
            lines.append(f"【商品列表】(共{len(items)}件)")
            
            # T4: 商品信息表头
            lines.append("-" * 40)
            # 表头对齐
            header_name = pad_to_width("名称", 24)
            header_ducat = pad_to_width("杜卡德金币", 8, 'right')
            header_credit = pad_to_width("现金", 10, 'right')
            lines.append(f"    {header_name} {header_ducat} {header_credit}")
            lines.append("-" * 40)
            
            for item in items:
                name = item['name']
                # 截断过长的名称
                while get_display_width(name) > 22:
                    name = name[:-1]
                if get_display_width(item['name']) > 22:
                    name = name[:-2] + ".."
                
                # 对齐各列
                padded_name = pad_to_width(name, 24)
                padded_ducat = pad_to_width(str(item['ducat']), 8, 'right')
                padded_credit = pad_to_width(str(item['credit']), 10, 'right')
                
                lines.append(f"    {padded_name} {padded_ducat} {padded_credit}")
    else:
        # 商人未到达
        if info['activation']:
            arrival_time, countdown = format_arrival_time(info['activation'])
            lines.append(f"  到达时间: {arrival_time}")
            lines.append(f"  倒计时: {countdown}")
        else:
            lines.append("  状态: 即将到来")
    
    return "\n".join(lines)

# ==================== 命令处理 ====================


@void_trader_handler.handle()
async def handle_void_trader(bot: Bot, event: Event):
    """处理虚空商人查询命令"""
    try:
        await bot.send(event, Message("正在查询虚空商人信息..."))
        
        # 获取世界状态数据
        world_data = await game_status_manager.fetch_world_state()
        if not world_data:
            await bot.send(event, Message("获取世界状态失败，请稍后重试"))
            return
        
        # 获取虚空商人数据
        void_traders = world_data.get('VoidTraders', [])
        if not void_traders:
            await bot.send(event, Message("当前没有虚空商人数据"))
            return
        
        # 处理第一个虚空商人
        trader = void_traders[0]
        
        # 解析激活时间戳作为缓存键
        activation_ts = trader.get('Activation', {}).get('$date', {}).get('$numberLong', '')
        expiry_ts = trader.get('Expiry', {}).get('$date', {}).get('$numberLong', '')
        
        # 检查商人是否已离开
        if expiry_ts:
            expiry_time = datetime.utcfromtimestamp(int(expiry_ts) / 1000)
            if datetime.utcnow() > expiry_time:
                # 商人已离开，清除缓存
                _void_trader_cache.clear_expired_cache('')
                await bot.send(event, Message("虚空商人已离开，请等待下次到来"))
                return
        
        # 清除过期缓存
        _void_trader_cache.clear_expired_cache(activation_ts)
        
        # 尝试获取缓存
        cached = _void_trader_cache.get_cache(activation_ts)
        
        if cached:
            # 使用缓存数据
            logger.info(f"使用缓存数据: {activation_ts}")
            info = cached['info']
            items = cached['items']
        else:
            # 构建新数据
            info = build_trader_info(trader)
            
            # 商人已到达时翻译商品
            items = None
            if info['is_active'] and trader.get('Manifest'):
                items = translate_manifest(trader['Manifest'])
                # 按杜卡德金币价格从高到低排序
                items.sort(key=lambda x: x['ducat'], reverse=True)
            
            # 缓存数据（只在商人到达时缓存）
            if info['is_active']:
                _void_trader_cache.set_cache(activation_ts, {
                    'info': info,
                    'items': items
                })
        
        # 格式化响应
        response_text = format_response(info, items)
        
        # 生成图片
        img_byte_io = text_to_image.convert_simple(
            text=response_text,
            title="虚空商人查询结果",
            max_width=520
        )
        
        await bot.send(event, MessageSegment.image(img_byte_io))
        
    except Exception as e:
        logger.error(f"查询虚空商人异常: {e}", exc_info=True)
        await bot.send(event, Message("查询虚空商人信息失败，请稍后重试"))
