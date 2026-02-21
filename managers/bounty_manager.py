# bounty_manager.py - 赏金任务管理器
import json
import aiohttp
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import logging
from core.translators.challenge_translator import ChallengeTranslator

logger = logging.getLogger(__name__)


class BountyManager:
    """赏金任务管理器 - 管理扎里曼、英择谛、1999的赏金任务"""

    def __init__(self):
        self.bounty_api_url = "https://oracle.browse.wf/bounty-cycle"

        # 数据文件路径
        self.data_dir = Path("./")
        self.export_challenges_file = self.data_dir / "data/game_data/ExportChallenges.json"
        self.zh_file = self.data_dir / "data/translations/zh.json"
        self.sol_nodes_file = Path("data/game_data/solNodes.json")

        # 挑战翻译器（仅用于午夜电波翻译，赏金任务保持原有逻辑）
        self.translator = ChallengeTranslator()

        # 缓存数据
        self.export_challenges: Dict = {}
        self.zh_translations: Dict = {}
        self.sol_nodes: Dict = {}

        # 赏金任务API数据缓存
        self.bounty_cache = None
        self.bounty_cache_time = None
        self.bounty_cache_expire_seconds = 300  # 缓存5分钟

        # 数据已加载标记
        self.data_loaded = False

    def load_data(self):
        """加载本地数据文件"""
        try:
            # 初始化挑战翻译器
            self.translator.load_data()
            logger.debug("✅ 挑战翻译器已初始化")

            # 加载 ExportChallenges.json
            if self.export_challenges_file.exists():
                with open(self.export_challenges_file, 'r', encoding='utf-8') as f:
                    self.export_challenges = json.load(f)
                logger.debug(f"✅ 加载 ExportChallenges.json: {len(self.export_challenges)} 条")
            else:
                logger.warning(f"⚠️ 未找到 ExportChallenges.json")

            # 加载 zh.json
            if self.zh_file.exists():
                with open(self.zh_file, 'r', encoding='utf-8') as f:
                    self.zh_translations = json.load(f)
                logger.debug(f"✅ 加载 zh.json: {len(self.zh_translations)} 条")
            else:
                logger.warning(f"⚠️ 未找到 zh.json")

            # 加载 solNodes.json
            if self.sol_nodes_file.exists():
                with open(self.sol_nodes_file, 'r', encoding='utf-8') as f:
                    self.sol_nodes = json.load(f)
                logger.debug(f"✅ 加载 solNodes.json: {len(self.sol_nodes)} 条")
            else:
                logger.warning(f"⚠️ 未找到 solNodes.json")

            self.data_loaded = True
            return True

        except Exception as e:
            logger.error(f"❌ 加载数据文件失败: {e}")
            return False

    def _normalize_challenge_key(self, challenge_path: str) -> str:
        """
        标准化challenge键，用于匹配ExportChallenges.json
        例如：/Lotus/Types/Challenges/Zariman/ZarimanUseVoidRiftsEasyChallenge
        保持原样，不去除Easy等后缀
        """
        return challenge_path

    def _get_translation_key(self, challenge_path: str) -> str:
        """
        获取翻译键，用于匹配zh.json
        例如：
        输入：/Lotus/Types/Challenges/Zariman/ZarimanUseVoidRiftsEasyChallenge
        输出：/Lotus/Language/Challenges/Challenge_ZarimanUseVoidRiftsChallenge_Desc

        规则：
        1. 将 /Types/ 改为 /Language/
        2. 在路径前加 Challenge_
        3. 去除Easy/Medium/Hard等难度后缀（如果有）
        4. 在末尾添加 _Desc 后缀
        """
        parts = challenge_path.split('/')
        filename = parts[-1]  # 最后部分：ZarimanUseVoidRiftsEasyChallenge

        # 去除难度后缀
        difficulty_suffixes = ['Easy', 'Medium', 'Hard', 'VeryHard', 'Normal', 'Tier1', 'Tier2', 'Tier3']
        for suffix in difficulty_suffixes:
            if filename.endswith(suffix):
                filename = filename[:-len(suffix)]
                break

        # 转换为翻译键格式
        translation_key = f"/Lotus/Language/Challenges/Challenge_{filename}_Desc"
        return translation_key

    def _translate_node(self, node_path: str) -> str:
        """从solNodes.json翻译节点名称"""
        if not self.sol_nodes:
            return node_path

        # 提取节点ID（如 SolNode100）
        if '/' in node_path:
            parts = node_path.split('/')
            for part in reversed(parts):  # 从后往前找
                if part.startswith('SolNode'):
                    node_key = part
                    break
            else:
                return node_path
        else:
            node_key = node_path

        # 查找节点
        if node_key in self.sol_nodes:
            node_data = self.sol_nodes[node_key]
            node_name = node_data.get('value', node_key)
            return node_name

        # 如果找不到节点，检查是否是1999地区的节点
        if node_key.startswith('SolNode85'):
            return f"1999区域({node_key})"

        return node_path

    async def fetch_bounty_cycles(self) -> Optional[List]:
        """从API获取赏金任务循环数据（带缓存）"""
        # 检查缓存是否有效
        import time
        current_time = time.time()
        if self.bounty_cache is not None and self.bounty_cache_time is not None:
            cache_age = current_time - self.bounty_cache_time
            if cache_age < self.bounty_cache_expire_seconds:
                logger.debug(f"📦 使用缓存数据（缓存{int(cache_age)}秒）")
                return self.bounty_cache

        # 缓存无效，从API获取新数据
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.bounty_api_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.error(f"❌ 获取赏金任务失败: HTTP {response.status}")
                        return None

                    data = await response.json()
                    logger.info(f"✅ 获取到 {len(data)} 个赏金任务")
                    # 更新缓存
                    self.bounty_cache = data
                    self.bounty_cache_time = current_time
                    return data

        except Exception as e:
            logger.error(f"❌ 获取赏金任务异常: {e}")
            # 如果获取失败但有缓存，返回缓存数据
            if self.bounty_cache is not None:
                logger.warning(f"⚠️ API请求失败，使用过期缓存数据")
                return self.bounty_cache
            return None

    def clear_bounty_cache(self):
        """清除赏金任务缓存"""
        self.bounty_cache = None
        self.bounty_cache_time = None
        logger.debug("🗑️ 赏金任务缓存已清除")

    def _extract_ally_name(self, ally_path: str) -> str:
        """从盟友路径中提取盟友名称"""
        if not ally_path or 'AllyAgent' not in ally_path:
            return '盟友'

        # 提取名称，如 EleanorAllyAgent -> Eleanor
        parts = ally_path.split('/')
        filename = parts[-1]  # EleanorAllyAgent
        if 'AllyAgent' in filename:
            name = filename.replace('AllyAgent', '')
            # 常见盟友名称映射
            ally_map = {
                'Eleanor': '埃莉诺',
                'Lettie': '莱媞',
                'Arthur': '亚瑟',
                'Amir': '埃米尔',
                'Quincy': '昆西',
                'Aoi': '阿雅',
                'Jenna': '珍娜',
                'Dante': '但丁'
            }
            return ally_map.get(name, name)

        return '盟友'

    def _clean_description(self, description: str, ally_name: str | None = None) -> str:
        """清理描述中的特殊标记"""
        if not description:
            return description

        # 移除颜色标记
        description = description.replace('|OPEN_COLOR|', '').replace('|CLOSE_COLOR|', '')

        # 替换盟友名称
        if ally_name and '|ALLY|' in description:
            description = description.replace('|ALLY|', ally_name)

        return description

    def _filter_description(self, description: str, ally_name: str | None = None) -> str:
        """过滤描述中的冗余信息，如"XXX的赏金任务"""
        if not description:
            return description

        # 如果描述是"XXX的赏金任务"格式，则返回空字符串
        # 匹配模式：中文/英文名称 + "的赏金任务"
        import re
        pattern = r'^.+的赏金任务$'
        if re.match(pattern, description):
            return ""

        return description

    def _get_challenge_info(self, challenge_path: str, ally_path: str | None = None) -> Dict:
        """获取challenge的完整信息（包含requiredCount和翻译）"""
        result = {
            'path': challenge_path,
            'requiredCount': 0,
            'name': challenge_path,
            'description': challenge_path
        }

        # 提取盟友名称
        ally_name = self._extract_ally_name(ally_path)

        # 1. 首先尝试使用挑战翻译器（新方法）- 但 ChallengeTranslator 只支持午夜电波
        # 赏金任务使用原始逻辑，所以这里跳过翻译器
        pass  # 跳过翻译器，直接使用原始逻辑

        # 2. 如果翻译器失败，使用原始逻辑作为回退
        logger.debug(f"使用原始逻辑翻译 {challenge_path}")

        # 2.1 获取 requiredCount
        export_key = self._normalize_challenge_key(challenge_path)
        if export_key in self.export_challenges:
            challenge_data = self.export_challenges[export_key]
            result['requiredCount'] = challenge_data.get('requiredCount', 0)

            # ExportChallenges.json中的值可能是翻译键，需要进一步解析
            for key, value in challenge_data.items():
                if key in ['name', 'description', 'flavour']:
                    translation_key = value
                    if translation_key in self.zh_translations:
                        translation_data = self.zh_translations[translation_key]
                        if isinstance(translation_data, dict):
                            result[key] = translation_data.get('value', translation_key)
                        elif isinstance(translation_data, str):
                            result[key] = translation_data

        # 2.2 如果ExportChallenges.json没有提供翻译，直接使用translation_key查询zh.json
        if result['name'] == challenge_path or result['description'] == challenge_path:
            translation_key = self._get_translation_key(challenge_path)
            if translation_key in self.zh_translations:
                translation_data = self.zh_translations[translation_key]
                if isinstance(translation_data, dict):
                    result['name'] = translation_data.get('name', challenge_path)
                    result['description'] = translation_data.get('description', '')
                    result['flavour'] = translation_data.get('flavour', '')
                elif isinstance(translation_data, str):
                    result['description'] = translation_data

        # 2.3 替换description中的|COUNT|为requiredCount，并清理特殊标记
        if result['description']:
            if result['requiredCount'] > 0:
                result['description'] = result['description'].replace('|COUNT|', str(result['requiredCount']))
            # 清理颜色标记和盟友标记
            result['description'] = self._clean_description(result['description'], ally_name)

        return result

    def _format_remaining_time(self, expiry_timestamp: Optional[float]) -> str:
        """格式化剩余时间"""
        if not expiry_timestamp:
            return ""

        try:
            # expiry_timestamp 可能是毫秒级时间戳
            # 如果数值大于 2e10（2024年的毫秒时间戳），则除以1000
            timestamp = expiry_timestamp
            if timestamp > 2_000_000_000:  # 大约2024年的毫秒时间戳
                timestamp = timestamp / 1000

            expiry_time = datetime.fromtimestamp(timestamp)
            now = datetime.now()
            remaining = expiry_time - now

            # 计算剩余时间
            total_seconds = int(remaining.total_seconds())

            if total_seconds <= 0:
                return " (即将刷新)"

            # 转换为小时和分钟
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60

            if hours > 0:
                return f" (剩余{hours}小时{minutes}分钟)"
            else:
                return f" (剩余{minutes}分钟)"
        except Exception as e:
            logger.warning(f"计算剩余时间失败: {e}, timestamp={expiry_timestamp}")
            return ""

    def format_bounty_cycles(self, bounty_data: Dict) -> str:
        """格式化赏金任务列表为中文"""
        if not bounty_data:
            return "暂无赏金任务"

        response_lines = []

        bounties = bounty_data.get('bounties', {})

        # 获取整个赏金任务的过期时间（通常在bounty_data顶层）
        expiry = bounty_data.get('expiry')

        # 格式化剩余时间
        remaining_time = self._format_remaining_time(expiry)

        # 遍历各个区域的赏金任务
        syndicate_order = ['ZarimanSyndicate', 'EntratiLabSyndicate', 'HexSyndicate']
        for idx, syndicate_name in enumerate(syndicate_order):
            if syndicate_name not in bounties:
                continue

            cycles = bounties[syndicate_name]

            # 翻译派系名称
            syndicate_map = {
                'ZarimanSyndicate': '扎里曼',
                'EntratiLabSyndicate': '英择谛',
                'HexSyndicate': '1999'
            }
            syndicate_display = syndicate_map.get(syndicate_name, syndicate_name)

            if not cycles:
                continue

            # 在英择谛和1999前加空行（扎里曼是第一个，不需要空行）
            if idx > 0:
                response_lines.append("")

            # 添加派系标题（带剩余时间）
            response_lines.append(f"【{syndicate_display}】{remaining_time}")

            # 遍历该派系下的所有赏金任务
            for cycle_idx, cycle in enumerate(cycles, 1):
                node = cycle.get('node', '')
                challenge_path = cycle.get('challenge', '')
                ally_path = cycle.get('ally', '')

                # 翻译节点名称
                node_name = self._translate_node(node)

                # 获取challenge信息（传入ally_path以处理盟友相关标记）
                info = self._get_challenge_info(challenge_path, ally_path)
                description = info['description']
                required_count = info['requiredCount']

                # 提取盟友名称（仅1999需要）
                ally_name = self._extract_ally_name(ally_path)

                # 根据不同区域格式化显示
                if syndicate_name == 'HexSyndicate':
                    # 1999区域格式：序号.地点-任务类型:H-序号 盟友
                    # 检查节点是否在sol_nodes中（1999节点应该包含类型）
                    if node in self.sol_nodes:
                        node_data = self.sol_nodes[node]
                        node_value = node_data.get('value', node_name)
                        # 节点值格式通常是 "霍瓦尼亚-刺杀: H-09 坦克"
                        # 按照示例格式：序号.地点-任务类型:H-序号
                        response_lines.append(f"{cycle_idx}.{node_value}")
                    else:
                        # 降级处理
                        response_lines.append(f"{cycle_idx}.{node_name}")
                    # 1999也保留任务描述，但过滤掉"XXX的赏金任务"
                    if description:
                        filtered_desc = self._filter_description(description, ally_name)
                        if filtered_desc:
                            response_lines.append(filtered_desc)
                else:
                    # 扎里曼和英择谛区域
                    # 为扎里曼和英择谛的节点添加任务类型
                    display_name = node_name
                    if syndicate_name in ['ZarimanSyndicate', 'EntratiLabSyndicate']:
                        # 检查节点是否在sol_nodes中
                        if node in self.sol_nodes:
                            node_data = self.sol_nodes[node]
                            node_type = node_data.get('type', '')
                            if node_type and node_type != 'Unknown':
                                display_name = f"{node_name}-{node_type}"

                    # 格式化赏金任务为一个整体（同一区域内任务间不加空行）
                    response_lines.append(f"{cycle_idx}.{display_name}")
                    # 扎里曼和英择谛保留任务描述
                    if description:
                        response_lines.append(description)

        return "\n".join(response_lines).strip()

    def get_bounty_structured(self, bounty_data: Dict) -> List[Dict]:
        """
        格式化赏金任务列表为结构化数据
        
        Args:
            bounty_data: API返回的赏金数据
            
        Returns:
            结构化内容列表，每项为 {"type": "T1-T4", "text": "内容", "align": "left/center"}
        """
        if not bounty_data:
            return [{"type": "T4", "text": "暂无赏金任务"}]

        content = []

        # T1: 大标题
        content.append({"type": "T1", "text": "赏金任务查询", "align": "center"})

        bounties = bounty_data.get('bounties', {})
        expiry = bounty_data.get('expiry')
        remaining_time = self._format_remaining_time(expiry)

        # 遍历各个区域的赏金任务
        syndicate_order = ['ZarimanSyndicate', 'EntratiLabSyndicate', 'HexSyndicate']
        for idx, syndicate_name in enumerate(syndicate_order):
            if syndicate_name not in bounties:
                continue

            cycles = bounties[syndicate_name]

            # 翻译派系名称
            syndicate_map = {
                'ZarimanSyndicate': '扎里曼',
                'EntratiLabSyndicate': '英择谛',
                'HexSyndicate': '1999'
            }
            syndicate_display = syndicate_map.get(syndicate_name, syndicate_name)

            if not cycles:
                continue

            # T2: 派系标题
            content.append({"type": "T2", "text": f"【{syndicate_display}】{remaining_time}"})

            # 遍历该派系下的所有赏金任务
            for cycle_idx, cycle in enumerate(cycles, 1):
                node = cycle.get('node', '')
                challenge_path = cycle.get('challenge', '')
                ally_path = cycle.get('ally', '')

                # 翻译节点名称
                node_name = self._translate_node(node)

                # 获取challenge信息
                info = self._get_challenge_info(challenge_path, ally_path)
                description = info['description']
                ally_name = self._extract_ally_name(ally_path)

                # T3: 任务行
                if syndicate_name == 'HexSyndicate':
                    # 1999区域格式
                    if node in self.sol_nodes:
                        node_data = self.sol_nodes[node]
                        node_value = node_data.get('value', node_name)
                        content.append({"type": "T3", "text": f"{cycle_idx}.{node_value}"})
                    else:
                        content.append({"type": "T3", "text": f"{cycle_idx}.{node_name}"})
                    # T4: 描述行（1999可能有多行描述，需要拆分）
                    if description:
                        filtered_desc = self._filter_description(description, ally_name)
                        if filtered_desc:
                            # 将多行描述拆分为多个 T4 项
                            for desc_line in filtered_desc.split('\n'):
                                desc_line = desc_line.strip()
                                if desc_line:
                                    content.append({"type": "T4", "text": desc_line})
                else:
                    # 扎里曼和英择谛区域
                    display_name = node_name
                    if syndicate_name in ['ZarimanSyndicate', 'EntratiLabSyndicate']:
                        if node in self.sol_nodes:
                            node_data = self.sol_nodes[node]
                            node_type = node_data.get('type', '')
                            if node_type and node_type != 'Unknown':
                                display_name = f"{node_name}-{node_type}"

                    content.append({"type": "T3", "text": f"{cycle_idx}.{display_name}"})
                    # T4: 描述行
                    if description:
                        content.append({"type": "T4", "text": description})

        return content


# 全局赏金任务管理器实例
bounty_manager = BountyManager()
