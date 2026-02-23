"""
输入清理工具 - 防止注入攻击和异常输入
"""

import re
from typing import Optional


def sanitize_input(text: str, max_length: int = 100) -> str:
    """
    清理用户输入，移除危险字符
    
    Args:
        text: 用户输入文本
        max_length: 最大允许长度
    
    Returns:
        清理后的安全文本
    """
    if not text:
        return ""
    
    # 移除控制字符（保留换行和制表符）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # 移除潜在的 HTML/JS 标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 移除多余的空白字符
    text = ' '.join(text.split())
    
    # 限制长度
    return text[:max_length].strip()


def sanitize_item_name(name: str, max_length: int = 50) -> str:
    """
    清理物品名称
    
    Args:
        name: 物品名称
        max_length: 最大允许长度
    
    Returns:
        清理后的物品名称
    """
    if not name:
        return ""
    
    # 只保留字母、数字、中文、空格和常用符号
    name = re.sub(r'[^\w\s\u4e00-\u9fff\-\'\.\(\)primePrime]', '', name)
    
    # 移除多余的空白字符
    name = ' '.join(name.split())
    
    return name[:max_length].strip()


def sanitize_command(text: str, max_length: int = 50) -> str:
    """
    清理命令输入
    
    Args:
        text: 命令文本
        max_length: 最大允许长度
    
    Returns:
        清理后的命令文本
    """
    if not text:
        return ""
    
    # 移除控制字符和特殊符号
    text = re.sub(r'[^\w\s\u4e00-\u9fff\-]', '', text)
    
    # 移除多余的空白字符
    text = ' '.join(text.split())
    
    return text[:max_length].strip().lower()


def is_valid_qq_number(qq: str) -> bool:
    """
    验证 QQ 号格式
    
    Args:
        qq: QQ 号字符串
    
    Returns:
        是否有效
    """
    if not qq:
        return False
    
    # QQ 号应该是 5-11 位数字
    return bool(re.match(r'^\d{5,11}$', qq))


def is_valid_group_id(group_id: str) -> bool:
    """
    验证群号格式
    
    Args:
        group_id: 群号字符串
    
    Returns:
        是否有效
    """
    if not group_id:
        return False
    
    # 群号应该是数字
    return bool(re.match(r'^\d+$', group_id))
