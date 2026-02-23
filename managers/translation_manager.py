# translation_manager.py - 翻译管理器（统一别名配置+游戏状态翻译）
import json
import re
import os
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from utils.aliases_config import WARFRAME_PART_ALIASES, WEAPON_PART_ALIASES  # 导入统一别名

# 导入模糊匹配器（保持原有逻辑）
try:
    from utils.fuzzy_matcher import fuzzy_matcher
    FUZZY_MATCHER_AVAILABLE = True
except ImportError:
    FUZZY_MATCHER_AVAILABLE = False
    logging.getLogger(__name__).warning("⚠️ 模糊匹配器未找到，将禁用模糊匹配功能")

# ===================== 精准部件关键词定义 =====================
# 提取所有中文部件关键词（去重）
PART_KEYWORDS = []
# 提取战甲部件中文关键词
for aliases in WARFRAME_PART_ALIASES.values():
    for alias in aliases:
        if re.search(r'[\u4e00-\u9fff]', alias):
            PART_KEYWORDS.append(alias)
# 提取武器部件中文关键词
for aliases in WEAPON_PART_ALIASES.values():
    for alias in aliases:
        if re.search(r'[\u4e00-\u9fff]', alias):
            PART_KEYWORDS.append(alias)
# 去重并排序
PART_KEYWORDS = list(set(PART_KEYWORDS))
PART_KEYWORDS.sort()


class TranslationManager:
    """翻译管理器 - 修复Set slug匹配优先级问题"""

    def __init__(self, translation_file: str = "data/translations/item_translations.json"):
        self.translation_file = Path(translation_file)
        self.translations: Dict[str, str] = {}  # 中文别名→英文slug
        self.reverse_translations: Dict[str, List[str]] = {}  # 英文slug→中文别名列表
        self.set_slugs: List[str] = []  # 所有_set类型的slug
        self.non_set_slugs: List[str] = []  # 非_set类型的slug
        self.initialized = False
        self.logger = logging.getLogger(__name__)  # 使用实例logger
        # 确保文件存在
        if not self.translation_file.exists():
            self._create_default_translation_file()

    def _create_default_translation_file(self):
        """创建默认翻译文件（兼容席瓦神盾示例）"""
        default_data = {
            "silva_and_aegis_prime_set": [
                "席瓦 & 神盾 Prime 一套",
                "席瓦神盾Prime一套",
                "席瓦 & 神盾 P 一套",
                "席瓦神盾P一套",
                "席瓦 & 神盾 Prime",
                "席瓦 & 神盾 P"
            ],
            "silva_and_aegis_prime_guard": [
                "席瓦 & 神盾 Prime 护手",
                "席瓦神盾Prime护手",
                "席瓦 & 神盾 P 护手",
                "席瓦神盾P护手"
            ],
            "glaive_prime_set": [
                "战刃 Prime 一套",
                "战刃Prime一套",
                "战刃 P 一套",
                "战刃P一套",
                "战刃 Prime",
                "战刃 P"
            ],
            "glaive_prime_blade": [
                "战刃 Prime 刀刃",
                "战刃Prime刀刃",
                "战刃 P 刀刃",
                "战刃P刀刃"
            ]
        }
        with open(self.translation_file, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"创建默认翻译文件: {self.translation_file}")

    def load_translations(self) -> bool:
        """加载翻译文件 - 拆分set/non-set slug"""
        try:
            if not self.translation_file.exists():
                self.logger.error(f"翻译文件不存在: {self.translation_file}")
                return False
            with open(self.translation_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 清空原有数据
            self.translations.clear()
            self.reverse_translations.clear()
            self.set_slugs.clear()
            self.non_set_slugs.clear()
            # 遍历所有slug，拆分set/non-set
            for english_slug, chinese_list in data.items():
                # 分类slug
                if english_slug.endswith('_set'):
                    self.set_slugs.append(english_slug)
                else:
                    self.non_set_slugs.append(english_slug)
                # 构建反向映射（英文→中文列表）
                if isinstance(chinese_list, list):
                    self.reverse_translations[english_slug] = chinese_list
                else:
                    self.reverse_translations[english_slug] = [chinese_list]
                # 构建正向映射（中文别名→英文slug）
                for chinese_name in self.reverse_translations[english_slug]:
                    normalized_key = self._normalize_query(chinese_name)
                    self.translations[normalized_key] = english_slug.lower()
            self.initialized = True
            self.logger.debug(f"✅ 加载翻译完成：{len(self.translations)}项")
            return True
        except Exception as e:
            self.logger.error(f"加载翻译文件失败: {e}")
            return False

    def translate(self, query: str) -> Tuple[Optional[str], bool]:
        """翻译核心逻辑 - 修复：当查询不包含部件关键词时，优先匹配最短的Set别名"""
        if not self.initialized:
            self.load_translations()
        original_query = query.strip()
        normalized_query = self._normalize_query(original_query)
        self.logger.debug(f"开始翻译: 原始='{original_query}', 标准化='{normalized_query}'")

        # 步骤1：判断是否包含部件关键词（精准匹配）
        has_part_keyword = any(keyword in original_query for keyword in PART_KEYWORDS)
        self.logger.debug(f"是否包含部件关键词: {has_part_keyword}")
        
        # 步骤2：如果不包含部件关键词，优先匹配Set slug（按别名长度排序，短的优先）
        if not has_part_keyword:
            set_match = self._match_set_slugs_best_fit(normalized_query, original_query)
            if set_match:
                self.logger.info(f"✅ 优先匹配Set slug: '{original_query}' -> '{set_match}'")
                return set_match.lower(), True

        # 步骤3：如果包含部件关键词或没有Set匹配，匹配非Set slug
        non_set_match = self._match_non_set_slugs(normalized_query, original_query)
        if non_set_match:
            self.logger.info(f"✅ 匹配非Set slug: '{original_query}' -> '{non_set_match}'")
            return non_set_match.lower(), True

        # 步骤4：模糊匹配/英文转换（原有兜底逻辑）
        if FUZZY_MATCHER_AVAILABLE:
            fuzzy_slug, fuzzy_matched = fuzzy_matcher.match(original_query)
            if fuzzy_matched:
                self.logger.info(f"✅ 模糊匹配: '{original_query}' -> '{fuzzy_slug}'")
                return fuzzy_slug, True

        # 步骤5：英文格式转换
        if self._is_english_format(original_query):
            slug = self._convert_english_to_slug(original_query)
            self.logger.info(f"📌 英文转换: '{original_query}' -> '{slug}'")
            return slug, False

        # 无匹配结果
        self.logger.warning(f"❌ 未找到匹配: '{original_query}'")
        return None, False

    def _match_set_slugs_best_fit(self, normalized_query: str, original_query: str) -> Optional[str]:
        """专门匹配Set slug，按别名长度排序，最短的优先（提高精确度）"""
        # 收集所有可能的Set匹配
        possible_matches = []

        for set_slug in self.set_slugs:
            set_aliases = self.reverse_translations.get(set_slug, [])
            for alias in set_aliases:
                normalized_alias = self._normalize_query(alias)

                # 1. 完全匹配（最高优先级）
                if normalized_query == normalized_alias:
                    self.logger.debug(f"完全匹配Set slug: '{normalized_query}' == '{normalized_alias}' -> '{set_slug}'")
                    return set_slug

                # 2. 查询包含别名或别名包含查询
                if normalized_query in normalized_alias or normalized_alias in normalized_query:
                    # 记录匹配度（别名长度越短，匹配度越高）
                    match_info = {
                        'slug': set_slug,
                        'alias_length': len(alias),
                        'normalized_alias': normalized_alias
                    }
                    possible_matches.append(match_info)

        # 如果有多个可能的匹配，按别名长度排序（最短的优先）
        if possible_matches:
            possible_matches.sort(key=lambda x: x['alias_length'])
            best_match = possible_matches[0]['slug']
            self.logger.debug(f"从{len(possible_matches)}个Set匹配中选择最短别名: '{best_match}'")
            return best_match

        return None

    def _match_non_set_slugs(self, normalized_query: str, original_query: str) -> Optional[str]:
        """匹配非Set slug - 修复匹配逻辑，优先完全匹配"""
        # 1. 首先尝试完全匹配
        for non_set_slug in self.non_set_slugs:
            non_set_aliases = self.reverse_translations.get(non_set_slug, [])
            for alias in non_set_aliases:
                normalized_alias = self._normalize_query(alias)
                if normalized_query == normalized_alias:
                    self.logger.debug(f"完全匹配非Set slug: '{normalized_query}' == '{normalized_alias}' -> '{non_set_slug}'")
                    return non_set_slug

        # 2. 如果没有完全匹配，再尝试部分匹配
        for non_set_slug in self.non_set_slugs:
            non_set_aliases = self.reverse_translations.get(non_set_slug, [])
            for alias in non_set_aliases:
                normalized_alias = self._normalize_query(alias)
                if normalized_query in normalized_alias or normalized_alias in normalized_query:
                    # 检查是否包含部件关键词，确保匹配正确
                    if any(keyword in original_query for keyword in PART_KEYWORDS):
                        return non_set_slug

        return None

    # 工具方法（保持原有逻辑）
    def _normalize_query(self, query: str) -> str:
        """标准化查询词：去空格、小写、统一P/Prime"""
        return query.replace(' ', '').replace('_', '').lower().replace('prime', 'p')

    def _is_english_format(self, text: str) -> bool:
        """判断是否为英文输入"""
        return not bool(re.search(r'[\u4e00-\u9fff]', text)) and bool(re.search(r'[a-zA-Z]', text))

    def _convert_english_to_slug(self, query: str) -> str:
        """将英文转换为slug格式"""
        query_lower = query.lower()
        query_clean = re.sub(r'[^\w\s]', ' ', query_lower)
        query_clean = re.sub(r'\s+', ' ', query_clean).strip()
        return query_clean.replace(' ', '_')

    def get_chinese_names(self, english_slug: str) -> List[str]:
        """获取英文slug对应的中文别名列表"""
        return self.reverse_translations.get(english_slug, [])

    def list_part_keywords(self) -> List[str]:
        """返回所有部件关键词列表（用于调试）"""
        return PART_KEYWORDS


# ===================== 游戏状态翻译器（合并自 game_status_translator.py）=====================
class GameStatusTranslator:
    """游戏状态翻译器 - 翻译节点、任务类型、派系等游戏数据"""
    def __init__(self):
        self.sol_nodes: Dict = {}
        self.languages: Dict = {}
        self.loaded = False
        self.logger = logging.getLogger(__name__)

    def load_translations(self):
        """加载翻译文件"""
        try:
            # 尝试多种可能的路径查找文件
            possible_paths = [
                'data/game_data/solNodes.json',  # 新路径
                'solNodes.json',  # 当前目录
                './solNodes.json',
                '../solNodes.json',
                './game_status_data/solNodes.json',
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'solNodes.json'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'solNodes.json'),
            ]

            sol_nodes_found = False
            languages_found = False

            # 加载节点数据
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        self.sol_nodes = json.load(f)
                    self.logger.info(f"✅ 成功从 {path} 加载节点数据")
                    sol_nodes_found = True
                    break

            if not sol_nodes_found:
                self.logger.warning("⚠️  未找到solNodes.json文件，节点翻译功能将受限")
                self.sol_nodes = {}

            # 加载语言数据
            for path in possible_paths:
                path_lang = path.replace('solNodes.json', 'zh.json')
                path_lang = path_lang.replace('game_data', 'translations')  # 修正zh.json的路径
                if os.path.exists(path_lang):
                    with open(path_lang, 'r', encoding='utf-8') as f:
                        self.languages = json.load(f)
                    self.logger.info(f"✅ 成功从 {path_lang} 加载语言数据")
                    languages_found = True
                    break

            if not languages_found:
                self.logger.warning("⚠️  未找到languages.json文件，部分翻译功能将受限")
                self.languages = {}

            self.loaded = True
            return True
        except Exception as e:
            self.logger.error(f"❌ 加载翻译文件失败: {e}")
            self.sol_nodes = {}
            self.languages = {}
            self.loaded = True
            return False

    def translate_node(self, node_path: str) -> str:
        """翻译节点路径为中文名称"""
        if not self.loaded or not self.sol_nodes:
            return node_path

        # 1. 如果节点路径是完整的URL路径
        if '/' in node_path:
            parts = node_path.split('/')
            node_key = parts[-1]
            if node_key in self.sol_nodes:
                english_name = self.sol_nodes[node_key].get('value', node_key)
                return self._translate_text(english_name)

        # 2. 如果节点路径就是节点ID (如 SolNode100)
        if node_path in self.sol_nodes:
            english_name = self.sol_nodes[node_path].get('value', node_path)
            return self._translate_text(english_name)

        # 3. 尝试从路径中提取节点ID
        match = re.search(r'(SolNode\d+)', node_path)
        if match and match.group(1) in self.sol_nodes:
            node_key = match.group(1)
            english_name = self.sol_nodes[node_key].get('value', node_path)
            return self._translate_text(english_name)

        # 4. 直接翻译整个路径
        return self._translate_text(node_path)

    def translate_mission_type(self, mission_type: str) -> str:
        """翻译任务类型"""
        if not self.loaded:
            return mission_type

        mission_translations = {
            'MT_EXTERMINATION': '歼灭',
            'MT_SURVIVAL': '生存',
            'MT_DEFENSE': '防御',
            'MT_MOBILE_DEFENSE': '移动防御',
            'MT_CAPTURE': '捕获',
            'MT_RESCUE': '救援',
            'MT_SPY': '间谍',
            'MT_SABOTAGE': '破坏',
            'MT_ASSASSINATION': '刺杀',
            'MT_INTEL': '间谍',
            'MT_TERRITORY': '拦截',
            'MT_ALCHEMY': '元素转换',
            'MT_ARTIFACT': '中断',
            'MT_EXCAVATE': '挖掘',
            'MT_VOID_CASCADE': '虚空覆涌',
            'MT_RETRIEVAL': '劫持',
            'MT_HIVE':'清巢',
            'MT_CORRUPTION':'虚空洪流',
            'MT_ASSAULT':'强袭',
            'MT_ENDLESS_CAPTURE': '传承种收割'
        }

        if mission_type in mission_translations:
            return mission_translations[mission_type]

        return self._translate_text(mission_type)

    def translate_faction(self, faction: str) -> str:
        """翻译派系"""
        if not self.loaded:
            return faction

        faction_translations = {
            'FC_GRINEER': 'Grineer',
            'FC_CORPUS': 'Corpus',
            'FC_INFESTATION': 'Infested',
            'FC_OROKIN': 'Orokin',
            'FC_CORRUPTED': '堕落者'
        }

        if faction in faction_translations:
            return faction_translations[faction]

        return self._translate_text(faction)

    def _translate_text(self, english_text: str) -> str:
        """从languages.json获取中文翻译"""
        if not english_text or not self.languages:
            return english_text

        # 尝试直接匹配
        if english_text in self.languages:
            translation_data = self.languages[english_text]
            if isinstance(translation_data, dict):
                return translation_data.get('zh', english_text)
            elif isinstance(translation_data, str):
                return translation_data

        # 如果没有直接匹配，尝试在值中搜索
        for key, value in self.languages.items():
            if isinstance(value, dict) and value.get('en') == english_text:
                return value.get('zh', english_text)

        # 简单的星球名称映射
        planet_map = {
            'Earth': '地球', 'Venus': '金星', 'Mercury': '水星',
            'Mars': '火星', 'Deimos': '火卫二', 'Phobos': '火卫一',
            'Ceres': '谷神星', 'Jupiter': '木星', 'Europa': '木卫二',
            'Saturn': '土星', 'Uranus': '天王星', 'Neptune': '海王星',
            'Pluto': '冥王星', 'Sedna': '赛德娜', 'Eris': '阋神星',
            'Void': '虚空', 'Kuva Fortress': '赤毒要塞',
            'Lua': '月球', 'Zariman': '扎里曼'
        }

        for eng, chi in planet_map.items():
            if english_text.startswith(eng):
                return english_text.replace(eng, chi)

        return english_text

    def translate_syndicate(self, syndicate_tag: str) -> str:
        """翻译派系标签"""
        syndicate_map = {
            'CetusSyndicate': '夜灵平野',
            'SolarisSyndicate': '奥布山谷',
            'EntratiSyndicate': '魔胎之境'
        }
        return syndicate_map.get(syndicate_tag, syndicate_tag)

    def translate_text(self, english_text: str) -> str:
        """通用翻译文本（兼容之前的调用）"""
        return self._translate_text(english_text)


# ===================== 全局实例 =====================
# 物品翻译管理器
translation_manager = TranslationManager()

# 游戏状态翻译器
game_translator = GameStatusTranslator()
translator = game_translator  # 兼容旧代码别名


# 调试用：打印部件关键词
if __name__ == "__main__":
    print("=== 部件关键词列表 ===")
    for idx, keyword in enumerate(translation_manager.list_part_keywords(), 1):
        print(f"{idx}. {keyword}")