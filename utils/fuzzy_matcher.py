# fuzzy_matcher.py - 模糊匹配器（统一别名配置）
import re
from typing import Dict, Optional, Tuple, List
from utils.aliases_config import WARFRAME_PART_ALIASES, WEAPON_PART_ALIASES, SET_KEYWORDS, PRIME_KEYWORDS  # 导入统一配置
import logging

logger = logging.getLogger(__name__)

class FuzzyMatcher:
    """模糊匹配器 - 修复战甲Prime版本问题"""
    # 战甲别名映射 (中文别名 -> 英文标准名)
    WARFRAME_ALIASES = {
        "banshee": ["音妈", "音甲", "音P"],
        "baruuk": ["武僧"],
        "caliban": ["卡利班"],
        "chroma": ["龙甲"],
        "ember": ["火鸡"],
        "equinox": ["扶她", "阴阳"],
        "frost": ["冰队", "冰男", "冰甲", "冰P"],
        "gara": ["玻璃"],
        "garuda": ["血妈", "血甲"],
        "gauss": ["高斯", "跑男", "招生办主任", "高主任"],
        "grendel": ["肥宅"],
        "gyre": ["电妹"],
        "harrow": ["主教"],
        "hildryn": ["母牛"],
        "hydroid": ["水男", "水男P"],
        "inaros": ["沙p", "沙甲", "老沙", "沙P"],
        "ivara": ["弓妹"],
        "khora": ["猫p", "猫甲", "猫P"],
        "lavos": ["药水哥"],
        "limbo": ["李明博", "李明博P", "神秘高帽男"],
        "loki": ["洛基", "洛基P"],
        "mag": ["磁妹"],
        "mesa": ["女枪", "女枪P"],
        "mirage": ["小丑", "小丑P"],
        "nekros": ["摸p", "摸甲", "摸P", "摸尸"],
        "nezha": ["哪吒", "哪吒P"],
        "nidus": ["蛆p", "蛆P", "蛆甲"],
        "nova": ["诺娃", "诺娃P"],
        "nyx": ["脑溢血", "脑溢血P"],
        "oberon": ["龙王", "奶爸", "龙王P", "奶爸P"],
        "octavia": ["DJ", "DJP", "音乐甲", "音乐"],
        "protea": ["茶p", "茶妹", "茶妹P"],
        "revenant": ["夜灵", "夜灵甲", "夜灵P"],
        "rhino": ["牛p", "牛P", "牛甲", "牛牛"],
        "saryn": ["毒妈", "毒妈P"],
        "sevagoth": ["鬼甲", "鬼P", "鬼甲P"],
        "titania": ["蝶妹", "蝶p", "蝶甲"],
        "trinity": ["奶妈"],
        "valkyr": ["瓦喵"],
        "vauban": ["工程"],
        "volt": ["电男", "电男P"],
        "wisp": ["花妈", "花甲"],
        "wukong": ["悟空", "猴p", "猴P"],
        "xaku": ["骨甲"],
        "yareli": ["水妹", "鸭梨"],
        "zephyr": ["鸟p", "鸟姐", "鸟P"],
    }

    # 武器别名映射 (中文 -> 英文)
    WEAPON_ALIASES = {
        "拉特昂亡魂": ["latron wraith"],
    }

    @classmethod
    def normalize_query(cls, query: str) -> str:
        """规范化查询字符串"""
        normalized = query.strip().lower()
        normalized = re.sub(r'[^\w\u4e00-\u9fff\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized

    @classmethod
    def extract_prime_keyword(cls, query: str) -> Tuple[str, bool]:
        """提取Prime关键词，返回处理后的查询和是否包含Prime"""
        normalized = query.lower()
        is_prime = False
        for keyword in PRIME_KEYWORDS:
            pattern = rf'\b{re.escape(keyword)}\b'
            if re.search(pattern, normalized):
                is_prime = True
                normalized = re.sub(pattern, '', normalized)
                break
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized, is_prime

    @classmethod
    def is_warframe_query(cls, query: str) -> bool:
        """判断是否是战甲查询"""
        normalized = cls.normalize_query(query)
        for eng_name, aliases in cls.WARFRAME_ALIASES.items():
            if eng_name in normalized:
                return True
            for alias in aliases:
                if alias.lower() in normalized:
                    return True
        for part_eng, part_aliases in WARFRAME_PART_ALIASES.items():
            for alias in part_aliases:
                if alias.lower() in normalized:
                    return True
        return False

    @classmethod
    def is_weapon_query(cls, query: str) -> bool:
        """判断是否是武器查询"""
        normalized = cls.normalize_query(query)
        for chinese_name, english_names in cls.WEAPON_ALIASES.items():
            if chinese_name in normalized:
                return True
            for english_name in english_names:
                if english_name.lower() in normalized:
                    return True
        for part_eng, part_aliases in WEAPON_PART_ALIASES.items():
            for alias in part_aliases:
                if alias.lower() in normalized:
                    return True
        return False

    @classmethod
    def parse_warframe_query(cls, query: str) -> Tuple[Optional[str], Optional[str], bool, bool]:
        """解析战甲查询"""
        normalized = cls.normalize_query(query)
        logger.debug(f"解析战甲查询: '{query}' -> 规范化: '{normalized}'")
        normalized, has_prime_keyword = cls.extract_prime_keyword(normalized)
        warframe_name = None
        part_name = None
        is_set = False

        # 检查套装关键词
        for keyword in SET_KEYWORDS:
            if keyword in normalized:
                is_set = True
                normalized = normalized.replace(keyword, '').strip()
                logger.debug(f"检测到套装关键词: '{keyword}'")
                break

        # 匹配战甲名称
        for eng_name, aliases in cls.WARFRAME_ALIASES.items():
            if eng_name in normalized:
                warframe_name = eng_name
                normalized = normalized.replace(eng_name, '').strip()
                break
            for alias in aliases:
                if alias.lower() in normalized:
                    warframe_name = eng_name
                    normalized = normalized.replace(alias.lower(), '').strip()
                    break
            if warframe_name:
                break

        # 补充匹配
        if not warframe_name and normalized:
            for eng_name, aliases in cls.WARFRAME_ALIASES.items():
                if normalized == eng_name or any(normalized == alias.lower() for alias in aliases):
                    warframe_name = eng_name
                    break

        # 匹配部件
        if not is_set and warframe_name:
            for part_eng, part_aliases in WARFRAME_PART_ALIASES.items():
                for alias in part_aliases:
                    if alias.lower() in normalized:
                        part_name = part_eng
                        break
                if part_name:
                    break

        is_prime = True  # 战甲默认Prime版本
        logger.debug(
            f"战甲解析结果: warframe='{warframe_name}', part='{part_name}', is_set={is_set}, is_prime={is_prime}")
        return warframe_name, part_name, is_set, is_prime

    @classmethod
    def parse_weapon_query(cls, query: str) -> Tuple[Optional[str], Optional[str], bool, bool]:
        """解析武器查询"""
        normalized = cls.normalize_query(query)
        logger.debug(f"解析武器查询: '{query}' -> 规范化: '{normalized}'")
        normalized, has_prime_keyword = cls.extract_prime_keyword(normalized)
        weapon_name = None
        part_name = None
        is_set = False

        # 检查套装关键词
        for keyword in SET_KEYWORDS:
            if keyword in normalized:
                is_set = True
                normalized = normalized.replace(keyword, '').strip()
                break

        # 匹配武器名称
        for chinese_name, english_names in cls.WEAPON_ALIASES.items():
            if chinese_name in normalized:
                weapon_name = english_names[0]
                normalized = normalized.replace(chinese_name, '').strip()
                break
            for english_name in english_names:
                if english_name.lower() in normalized:
                    weapon_name = english_name
                    normalized = normalized.replace(english_name.lower(), '').strip()
                    break
            if weapon_name:
                break

        # 匹配部件
        if not is_set and weapon_name:
            for part_eng, part_aliases in WEAPON_PART_ALIASES.items():
                for alias in part_aliases:
                    if alias.lower() in normalized:
                        part_name = part_eng
                        break
                if part_name:
                    break

        is_prime = has_prime_keyword
        logger.debug(f"武器解析结果: weapon='{weapon_name}', part='{part_name}', is_set={is_set}, is_prime={is_prime}")
        return weapon_name, part_name, is_set, is_prime

    @classmethod
    def generate_warframe_slug(cls, warframe_name: str, part_name: Optional[str] = None, is_set: bool = False,
                               is_prime: bool = True) -> str:
        """生成战甲API slug"""
        prime_suffix = "_prime" if is_prime else ""
        if is_set:
            slug = f"{warframe_name}{prime_suffix}_set"
        elif part_name:
            if part_name == "blueprint":
                slug = f"{warframe_name}{prime_suffix}_blueprint"
            else:
                slug = f"{warframe_name}{prime_suffix}_{part_name}_blueprint"
        else:
            slug = f"{warframe_name}{prime_suffix}_set"
        logger.debug(f"生成战甲slug: '{slug}'")
        return slug

    @classmethod
    def generate_weapon_slug(cls, weapon_name: str, part_name: Optional[str] = None, is_set: bool = False,
                             is_prime: bool = False) -> str:
        """生成武器API slug"""
        prime_suffix = "_prime" if is_prime else ""
        weapon_slug = weapon_name.replace(' ', '_')
        if is_set:
            slug = f"{weapon_slug}{prime_suffix}_set"
        elif part_name:
            slug = f"{weapon_slug}{prime_suffix}_{part_name}"
        else:
            slug = f"{weapon_slug}{prime_suffix}_blueprint"
        logger.debug(f"生成武器slug: '{slug}'")
        return slug

    @classmethod
    def match(cls, query: str) -> Tuple[Optional[str], bool]:
        """模糊匹配查询"""
        logger.debug(f"开始匹配查询: '{query}'")
        if cls.is_weapon_query(query):
            logger.debug("判断为武器查询")
            weapon_name, part_name, is_set, is_prime = cls.parse_weapon_query(query)
            if not weapon_name:
                logger.debug(f"未匹配到武器: '{query}'")
                return cls._try_warframe_match(query)
            slug = cls.generate_weapon_slug(weapon_name, part_name, is_set, is_prime)
            logger.info(f"✅ 武器模糊匹配成功: '{query}' -> '{slug}'")
            return slug, True
        elif cls.is_warframe_query(query):
            logger.debug("判断为战甲查询")
            return cls._try_warframe_match(query)
        else:
            logger.debug(f"无法识别查询类型: '{query}'")
            return None, False

    @classmethod
    def _try_warframe_match(cls, query: str) -> Tuple[Optional[str], bool]:
        """尝试战甲匹配"""
        warframe_name, part_name, is_set, is_prime = cls.parse_warframe_query(query)
        if not warframe_name:
            logger.debug(f"未匹配到战甲: '{query}'")
            return None, False
        slug = cls.generate_warframe_slug(warframe_name, part_name, is_set, is_prime)
        logger.info(f"✅ 战甲模糊匹配成功: '{query}' -> '{slug}'")
        return slug, True

    @classmethod
    def get_statistics(cls) -> Dict[str, int]:
        """获取统计信息"""
        warframe_count = len(cls.WARFRAME_ALIASES)
        warframe_alias_count = sum(len(aliases) for aliases in cls.WARFRAME_ALIASES.values())
        weapon_count = len(cls.WEAPON_ALIASES)
        weapon_alias_count = sum(len(aliases) for aliases in cls.WEAPON_ALIASES.values())
        warframe_part_count = len(WARFRAME_PART_ALIASES)
        weapon_part_count = len(WEAPON_PART_ALIASES)
        return {
            "warframe_count": warframe_count,
            "warframe_alias_count": warframe_alias_count,
            "weapon_count": weapon_count,
            "weapon_alias_count": weapon_alias_count,
            "warframe_part_count": warframe_part_count,
            "weapon_part_count": weapon_part_count,
            "total_items": warframe_count + weapon_count,
            "total_aliases": warframe_alias_count + weapon_alias_count,
        }

# 全局模糊匹配器实例
fuzzy_matcher = FuzzyMatcher()