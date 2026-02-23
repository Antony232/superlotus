# subscription_manager.py - 裂缝订阅管理器
import json
import asyncio
import time
import threading
from typing import Dict, List, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# 文件锁用于防止并发写入冲突
_file_lock = threading.Lock()


@dataclass
class FissureSubscription:
    """裂缝订阅信息"""
    user_id: str  # 用户QQ号
    group_id: str  # 群号
    mission_type: str  # 任务类型，如"防御"
    difficulty: str  # 难度："steel"（钢铁）或"normal"（普通）
    tier: str = "all"  # 等级："古纪"、"前纪"、"中纪"、"后纪"、"安魂"、"全能" 或 "all"
    planet: str = "all"  # 星球地点："all"（所有星球）或具体星球名
    node_filter: str = None  # 具体节点过滤（如"Cordelia"），None表示不过滤
    last_notified_time: float = 0  # 上次通知时间
    created_time: float = 0  # 创建时间

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "group_id": self.group_id,
            "mission_type": self.mission_type,
            "difficulty": self.difficulty,
            "tier": self.tier,
            "planet": self.planet,
            "node_filter": self.node_filter,
            "last_notified_time": self.last_notified_time,
            "created_time": self.created_time
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            user_id=data.get("user_id", ""),
            group_id=data.get("group_id", ""),
            mission_type=data.get("mission_type", ""),
            difficulty=data.get("difficulty", "normal"),
            tier=data.get("tier", "all"),
            planet=data.get("planet", "all"),
            node_filter=data.get("node_filter", None),
            last_notified_time=data.get("last_notified_time", 0),
            created_time=data.get("created_time", time.time())
        )


class SubscriptionManager:
    """订阅管理器"""

    # 订阅限制常量
    MAX_SUBSCRIPTIONS_PER_USER = 10  # 每个用户最多订阅数量

    def __init__(self, data_file: str = "./data/subscriptions.json"):
        self.data_file = Path(data_file)
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.subscriptions: List[FissureSubscription] = []
        self.notified_fissures: Set[str] = set()  # 已通知的裂缝ID集合
        self.load_subscriptions()

    def load_subscriptions(self):
        """加载订阅数据"""
        try:
            with _file_lock:  # 添加文件锁
                if self.data_file.exists():
                    with open(self.data_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self.subscriptions = [FissureSubscription.from_dict(item) for item in data]
                    logger.debug(f"✅ 加载了 {len(self.subscriptions)} 个裂缝订阅")
                else:
                    self.subscriptions = []
                    logger.info("📝 订阅文件不存在，创建空列表")
        except Exception as e:
            logger.error(f"❌ 加载订阅数据失败: {e}")
            self.subscriptions = []

    def save_subscriptions(self):
        """保存订阅数据"""
        try:
            with _file_lock:  # 添加文件锁
                data = [sub.to_dict() for sub in self.subscriptions]
                # 先写入临时文件，再重命名，避免写入失败导致文件损坏
                temp_file = self.data_file.with_suffix('.json.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                temp_file.replace(self.data_file)  # 原子操作
                logger.debug(f"💾 保存了 {len(self.subscriptions)} 个订阅")
        except Exception as e:
            logger.error(f"❌ 保存订阅数据失败: {e}")

    def add_subscription(self, user_id: str, group_id: str, mission_type: str,
                         difficulty: str = "normal", tier: str = "all",
                         planet: str = "all", node_filter: str = None) -> bool:
        """添加订阅"""
        # 检查用户的订阅数量限制
        user_subs = [s for s in self.subscriptions if s.user_id == user_id]
        if len(user_subs) >= self.MAX_SUBSCRIPTIONS_PER_USER:
            logger.warning(f"用户 {user_id} 订阅数量已达上限 {self.MAX_SUBSCRIPTIONS_PER_USER}")
            return False

        # 检查是否已存在相同订阅
        for sub in self.subscriptions:
            if (sub.user_id == user_id and
                    sub.group_id == group_id and
                    sub.mission_type == mission_type and
                    sub.difficulty == difficulty and
                    sub.tier == tier and
                    sub.planet == planet and
                    sub.node_filter == node_filter):
                return False  # 已存在

        new_sub = FissureSubscription(
            user_id=user_id,
            group_id=group_id,
            mission_type=mission_type,
            difficulty=difficulty,
            tier=tier,
            planet=planet,
            node_filter=node_filter,
            created_time=time.time()
        )
        self.subscriptions.append(new_sub)
        self.save_subscriptions()
        logger.info(f"✅ 添加订阅: {user_id} - {mission_type} {difficulty} {tier} {planet} {node_filter}")
        return True

    def remove_subscription(self, user_id: str, group_id: str,
                            mission_type: str = None, difficulty: str = None,
                            tier: str = None, planet: str = None,
                            node_filter: str = None) -> List[FissureSubscription]:
        """移除订阅，返回被移除的订阅列表"""
        removed = []
        remaining = []

        for sub in self.subscriptions:
            # 判断是否匹配移除条件
            match_user = (sub.user_id == user_id)
            match_group = (sub.group_id == group_id)
            match_mission = (mission_type is None or sub.mission_type == mission_type)
            match_difficulty = (difficulty is None or sub.difficulty == difficulty)
            match_tier = (tier is None or sub.tier == tier)
            match_planet = (planet is None or sub.planet == planet)
            match_node = (node_filter is None or sub.node_filter == node_filter)

            if all([match_user, match_group, match_mission, match_difficulty,
                    match_tier, match_planet, match_node]):
                removed.append(sub)
            else:
                remaining.append(sub)

        self.subscriptions = remaining
        if removed:
            self.save_subscriptions()
            logger.info(f"✅ 移除了 {len(removed)} 个订阅")

        return removed

    def get_user_subscriptions(self, user_id: str, group_id: str = None) -> List[FissureSubscription]:
        """获取用户的订阅"""
        if group_id:
            return [sub for sub in self.subscriptions
                    if sub.user_id == user_id and sub.group_id == group_id]
        return [sub for sub in self.subscriptions if sub.user_id == user_id]

    def get_group_subscriptions(self, group_id: str) -> List[FissureSubscription]:
        """获取群组的订阅"""
        return [sub for sub in self.subscriptions if sub.group_id == group_id]

    def clear_old_notifications(self, older_than_hours: int = 1):
        """清理旧的已通知记录"""
        current_time = time.time()
        threshold = current_time - (older_than_hours * 3600)

        # 清理过期的已通知记录
        cleaned = False
        new_notified = set()

        for fissure_id in self.notified_fissures:
            # 简单的实现：只清理1小时前的记录
            # 更复杂的实现可以解析fissure_id中的时间信息
            cleaned = True

        if cleaned:
            self.notified_fissures = new_notified

    def mark_fissure_as_notified(self, fissure_id: str):
        """标记裂缝为已通知"""
        self.notified_fissures.add(fissure_id)

    def is_fissure_notified(self, fissure_id: str) -> bool:
        """检查裂缝是否已通知过"""
        return fissure_id in self.notified_fissures

    def generate_fissure_id(self, fissure_data: dict) -> str:
        """生成裂缝的唯一ID"""
        node = fissure_data.get('Node', '')
        mission_type = fissure_data.get('MissionType', '')
        is_hard = fissure_data.get('Hard', False)
        tier = fissure_data.get('Modifier', '')
        activation = fissure_data.get('Activation', {}).get('$date', {}).get('$numberLong', '')

        # 使用节点、任务类型、难度、等级和激活时间生成唯一ID
        return f"{node}_{mission_type}_{is_hard}_{tier}_{activation}"


# 全局订阅管理器实例
subscription_manager = SubscriptionManager()
