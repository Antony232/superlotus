"""
虚空商人商品翻译器
使用 warframe_exports 文件夹中的 JSON 文件进行翻译
"""

import json
import os
from typing import Dict, Optional, List, Any
import logging

logger = logging.getLogger(__name__)


class VoidTraderTranslator:
    """虚空商人商品翻译器 - 使用所有 export 文件"""
    
    def __init__(self, export_dir: str = 'warframe_exports'):
        self._export_dir = export_dir
        # 存储 uniqueName -> name 的映射
        self._name_map: Dict[str, str] = {}
        self._loaded = False
        
        # 所有可能的 JSON 根键名
        self._json_keys = [
            'ExportUpgrades', 'ExportWeapons', 'ExportResources', 'ExportCustoms',
            'ExportFlavour', 'ExportGear', 'ExportWarframes', 'ExportSentinels',
            'ExportRelicArcane', 'ExportRegions', 'ExportDrones', 'ExportFusionBundles',
            'ExportKeys', 'ExportOther'
        ]
    
    def _extract_keyword(self, item_type: str) -> str:
        """从 ItemType 提取关键词（最后部分）"""
        parts = item_type.split('/')
        return parts[-1] if parts else item_type
    
    def load_data(self) -> None:
        """加载所有 export 文件数据"""
        if self._loaded:
            return
            
        # 获取所有 JSON 文件
        try:
            json_files = [f for f in os.listdir(self._export_dir) if f.endswith('.json')]
        except FileNotFoundError:
            logger.error(f"导出目录不存在: {self._export_dir}")
            return
        
        logger.info(f"找到 {len(json_files)} 个 JSON 文件")
        
        total_items = 0
        for json_file in json_files:
            file_path = os.path.join(self._export_dir, json_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 尝试所有可能的键名
                file_items = 0
                for key in self._json_keys:
                    items = data.get(key, [])
                    if isinstance(items, list):
                        for item in items:
                            unique_name = item.get('uniqueName', '')
                            name = item.get('name', '')
                            if unique_name and name:
                                self._name_map[unique_name] = name
                                file_items += 1
                
                if file_items > 0:
                    total_items += file_items
                    
            except Exception as e:
                logger.error(f"加载文件失败 {json_file}: {e}")
        
        self._loaded = True
        logger.info(f"总计加载 {total_items} 条翻译记录")
    
    def _convert_store_item_type(self, item_type: str) -> str:
        """
        将 ItemType 转换为 uniqueName 格式
        /Lotus/StoreItems/... -> /Lotus/...
        """
        if '/StoreItems/' in item_type:
            return item_type.replace('/StoreItems/', '/')
        return item_type
    
    def _generate_search_variants(self, keyword: str) -> List[str]:
        """生成搜索变体：去掉常见后缀"""
        variants = [keyword]
        
        # 去掉常见后缀
        suffixes = ['Weapon', 'Gun', 'Item', 'Mod', 'StoreItem', 'MeleeTree', 'Blueprint']
        for suffix in suffixes:
            if keyword.endswith(suffix):
                variants.append(keyword[:-len(suffix)])
        
        return variants
    
    def translate_item(self, item_type: str) -> Optional[str]:
        """
        翻译单个物品
        
        策略：
        1. 直接匹配转换后的 uniqueName
        2. 用关键词在 uniqueName 中搜索
        """
        if not self._loaded:
            self.load_data()
        
        # 策略 1: 直接匹配 uniqueName
        unique_name = self._convert_store_item_type(item_type)
        if unique_name in self._name_map:
            return self._name_map[unique_name]
        
        # 策略 2: 关键词搜索
        keyword = self._extract_keyword(item_type)
        search_variants = self._generate_search_variants(keyword)
        
        for variant in search_variants:
            # 精确匹配: uniqueName 以 /variant 结尾
            for uid, name in self._name_map.items():
                if uid.endswith('/' + variant):
                    return name
            
            # 模糊匹配: variant 在 uniqueName 中
            for uid, name in self._name_map.items():
                if variant in uid:
                    return name
        
        return None
    
    def translate_manifest(self, manifest: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """翻译商品列表"""
        if not self._loaded:
            self.load_data()
        
        results = []
        for item in manifest:
            item_type = item.get('ItemType', '')
            keyword = self._extract_keyword(item_type)
            name_zh = self.translate_item(item_type)
            
            results.append({
                'ItemType': item_type,
                'keyword': keyword,
                'name_zh': name_zh,
                'primePrice': item.get('PrimePrice', 0),
                'regularPrice': item.get('RegularPrice', 0),
                'found': name_zh is not None
            })
        
        return results


# 全局翻译器实例
void_trader_translator = VoidTraderTranslator()
