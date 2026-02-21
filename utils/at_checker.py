# utils/at_checker.py - 修复@消息检查器
import re
from nonebot.adapters.onebot.v11 import Event, Message, MessageSegment
from config import config


def is_at_me(event: Event) -> bool:
    """检查是否@了机器人"""
    # 首先检查to_me属性（OneBot V11适配器会自动设置）
    if hasattr(event, 'to_me') and event.to_me:
        return True
    
    # 获取机器人的QQ号
    bot_qq = config.get_bot_qq_number()
    
    # 检查原始消息字符串
    raw_message = event.get_plaintext() if hasattr(event, 'get_plaintext') else str(event.message)
    
    # 使用正则表达式匹配CQ码格式的@
    # 格式: [CQ:at,qq=2093845106]
    at_pattern_cq = rf'\[CQ:at,qq={bot_qq}\]'
    if re.search(at_pattern_cq, raw_message):
        return True
    
    # 检查消息段中的@
    if hasattr(event, 'message'):
        for segment in event.message:
            if segment.type == "at":
                # 检查是否是@机器人
                qq_value = segment.data.get("qq", "")
                if str(qq_value) == bot_qq or str(qq_value) == str(event.self_id):
                    return True
    
    return False


def extract_message_without_at(event: Event) -> str:
    """提取消息中去除@机器人的部分"""
    if not hasattr(event, 'message'):
        return event.get_plaintext() if hasattr(event, 'get_plaintext') else ""
    
    bot_qq = config.get_bot_qq_number()
    message_parts = []
    
    for segment in event.message:
        if segment.type == "text":
            # 处理文本，移除可能的@QQ号
            text = segment.data.get("text", "")
            message_parts.append(text)
    
    # 合并所有文本部分
    full_text = "".join(message_parts).strip()
    
    # 移除可能的@机器人文本
    full_text = re.sub(rf'@{bot_qq}\s*', '', full_text)
    full_text = re.sub(rf'＠{bot_qq}\s*', '', full_text)
    
    return full_text


def is_pure_at(event: Event) -> bool:
    """检查是否只是@机器人而没有其他内容"""
    if not is_at_me(event):
        return False
    
    message_without_at = extract_message_without_at(event)
    return not bool(message_without_at.strip())