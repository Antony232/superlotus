# prime_market_report_v2.py - Prime 市场分析报告（前10名版本）

import json
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class PrimeItemData:
    """Prime 物品数据"""
    url_name: str
    chinese_name: str
    item_type: str
    avg_price_90d: float
    avg_price_7d: float
    avg_price_48h: float
    price_change_7d_pct: float
    price_change_48h_pct: float
    total_volume_90d: int
    current_lowest_sell: float
    current_avg_sell: float
    last_updated: str


class PrimeMarketReport:
    """Prime 市场报告生成器"""
    
    API_BASE = "https://api.warframe.market/v1"
    RATE_LIMIT = 0.35
    CACHE_FILE = "prime_set_cache.json"
    
    # 排除的武器列表
    EXCLUDED_ITEMS = {
        'burston_prime_set',
        'braton_prime_set',
        'paris_prime_set',
        'orthos_prime_set',
        'lex_prime_set',
    }
    
    def __init__(self, translations_file: str = "data/translations/item_translations.json"):
        self.translations = self._load_translations(translations_file)
        self.target_items = self._filter_target_items()
        self.cache: Dict[str, dict] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
    def _load_translations(self, file_path: str) -> Dict[str, List[str]]:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _filter_target_items(self) -> Dict[str, Dict]:
        targets = {}
        
        warframe_primes = {
            'ash', 'atlas', 'banshee', 'baruuk', 'caliban', 'chroma', 'ember', 'equinox',
            'excalibur', 'frost', 'gara', 'garuda', 'gauss', 'grendel', 'gyre',
            'harrow', 'hildryn', 'hydroid', 'inaros', 'ivara', 'khora', 'lavos',
            'limbo', 'loki', 'mag', 'mesa', 'mirage', 'nekros', 'nezha', 'nidus',
            'nova', 'nyx', 'oberon', 'octavia', 'protea', 'revenant', 'rhino',
            'saryn', 'sevagoth', 'titania', 'trinity', 'valkyr', 'vauban', 'volt',
            'wisp', 'wukong', 'xaku', 'yareli', 'zephyr'
        }
        
        for url_name, chinese_names in self.translations.items():
            if url_name in self.EXCLUDED_ITEMS:
                continue
            
            name_lower = url_name.lower()
            chinese_name = chinese_names[0] if chinese_names else url_name
            
            if name_lower.startswith('primed_'):
                targets[url_name] = {'name': chinese_name, 'type': 'mod'}
                continue
            
            if name_lower.endswith('_prime_set'):
                base_name = name_lower.replace('_prime_set', '')
                item_type = 'warframe' if base_name in warframe_primes else 'weapon'
                targets[url_name] = {'name': chinese_name, 'type': item_type}
        
        stats = {}
        for item in targets.values():
            stats[item['type']] = stats.get(item['type'], 0) + 1
        
        print(f"✅ 筛选完成: 共 {len(targets)} 个目标物品")
        print(f"   • 🎭 Prime 战甲: {stats.get('warframe', 0)} 个")
        print(f"   • ⚔️ Prime 武器: {stats.get('weapon', 0)} 个")
        print(f"   • 🧩 Prime MOD: {stats.get('mod', 0)} 个")
        print(f"   • ⛔ 已排除5个物品")
        
        return targets
    
    def _clean_name(self, name: str) -> str:
        return name.replace(' 一套', '').replace('一套', '').strip()
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"Platform": "pc", "Accept": "application/json"}
        )
        self._load_cache()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        self._save_cache()
    
    def _load_cache(self):
        if Path(self.CACHE_FILE).exists():
            try:
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                print(f"📦 已加载缓存: {len(self.cache)} 个物品")
            except:
                self.cache = {}
    
    def _save_cache(self):
        with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    async def fetch_statistics(self, url_name: str) -> Optional[dict]:
        if url_name in self.cache:
            cached_time = datetime.fromisoformat(self.cache[url_name].get('time', '2000-01-01'))
            if datetime.now() - cached_time < timedelta(hours=4):
                return self.cache[url_name]['data']
        
        await asyncio.sleep(self.RATE_LIMIT)
        url = f"{self.API_BASE}/items/{url_name}/statistics"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.cache[url_name] = {
                        'time': datetime.now().isoformat(),
                        'data': data
                    }
                    return data
                elif response.status == 429:
                    await asyncio.sleep(3)
                    return await self.fetch_statistics(url_name)
        except Exception as e:
            print(f"❌ {url_name}: {e}")
            return None
    
    def _analyze(self, url_name: str, data: dict) -> Optional[PrimeItemData]:
        try:
            payload = data.get('payload', {})
            item_info = self.target_items[url_name]
            
            closed = payload.get('statistics_closed', {})
            closed_90d = closed.get('90days', [])
            closed_48h = closed.get('48hours', [])
            
            if not closed_90d:
                return None
            
            vol_90d = sum(d['volume'] for d in closed_90d)
            avg_90d = sum(d['avg_price'] * d['volume'] for d in closed_90d) / vol_90d
            
            closed_7d = closed_90d[-7:] if len(closed_90d) >= 7 else closed_90d
            avg_7d = sum(d['avg_price'] for d in closed_7d) / len(closed_7d)
            avg_48h = sum(d['avg_price'] for d in closed_48h) / len(closed_48h) if closed_48h else 0
            
            if len(closed_90d) >= 14:
                prev_7d = closed_90d[-14:-7]
                prev_avg = sum(d['avg_price'] for d in prev_7d) / len(prev_7d)
                change_7d = ((avg_7d - prev_avg) / prev_avg) * 100
            else:
                change_7d = 0
            
            if len(closed_48h) >= 4:
                mid = len(closed_48h) // 2
                first_half = sum(d['avg_price'] for d in closed_48h[:mid]) / mid
                second_half = sum(d['avg_price'] for d in closed_48h[mid:]) / (len(closed_48h) - mid)
                change_48h = ((second_half - first_half) / first_half) * 100
            else:
                change_48h = 0
            
            live = payload.get('statistics_live', {})
            live_48h = live.get('48hours', [])
            sell_orders = [d for d in live_48h if d.get('order_type') == 'sell']
            
            curr_low = min((d['min_price'] for d in sell_orders), default=0)
            curr_avg = sum(d['avg_price'] for d in sell_orders) / len(sell_orders) if sell_orders else 0
            
            return PrimeItemData(
                url_name=url_name,
                chinese_name=item_info['name'],
                item_type=item_info['type'],
                avg_price_90d=avg_90d,
                avg_price_7d=avg_7d,
                avg_price_48h=avg_48h,
                price_change_7d_pct=change_7d,
                price_change_48h_pct=change_48h,
                total_volume_90d=vol_90d,
                current_lowest_sell=curr_low,
                current_avg_sell=curr_avg,
                last_updated=datetime.now().isoformat()
            )
        except Exception as e:
            return None
    
    async def analyze_all(self):
        results = []
        items = list(self.target_items.keys())
        
        print(f"\n🔍 分析 {len(items)} 个物品...")
        print(f"⏱️ 预计耗时: ~{len(items) * self.RATE_LIMIT / 60:.1f} 分钟\n")
        
        for i, url_name in enumerate(items, 1):
            data = await self.fetch_statistics(url_name)
            if data:
                analysis = self._analyze(url_name, data)
                if analysis:
                    results.append(analysis)
            
            if i % 10 == 0 or i == len(items):
                print(f"   {i}/{len(items)} ({i/len(items)*100:.0f}%) - 成功: {len(results)}")
        
        return results
    
    def generate_rankings(self, results: List[PrimeItemData]) -> dict:
        """生成三维分类排名 - 只取前10名"""
        active = [r for r in results if r.total_volume_90d > 5]
        
        warframes = [r for r in active if r.item_type == 'warframe']
        weapons = [r for r in active if r.item_type == 'weapon']
        mods = [r for r in active if r.item_type == 'mod']
        
        return {
            'volume': {
                'warframe': sorted(warframes, key=lambda x: x.total_volume_90d, reverse=True)[:10],  # 前10
                'weapon': sorted(weapons, key=lambda x: x.total_volume_90d, reverse=True)[:10],
                'mod': sorted(mods, key=lambda x: x.total_volume_90d, reverse=True)[:10],
            },
            'price': {
                'warframe': sorted(warframes, key=lambda x: x.avg_price_7d, reverse=True)[:10],  # 前10
                'weapon': sorted(weapons, key=lambda x: x.avg_price_7d, reverse=True)[:10],
                'mod': sorted(mods, key=lambda x: x.avg_price_7d, reverse=True)[:10],
            },
            'gain': {
                'warframe': sorted(warframes, key=lambda x: x.price_change_7d_pct, reverse=True)[:10],  # 前10
                'weapon': sorted(weapons, key=lambda x: x.price_change_7d_pct, reverse=True)[:10],
                'mod': sorted(mods, key=lambda x: x.price_change_7d_pct, reverse=True)[:10],
            },
            'loss': {
                'warframe': sorted(warframes, key=lambda x: x.price_change_7d_pct)[:5],  # 跌幅前5
                'weapon': sorted(weapons, key=lambda x: x.price_change_7d_pct)[:5],
                'mod': sorted(mods, key=lambda x: x.price_change_7d_pct)[:5],
            }
        }
    
    def print_report(self, rankings: dict):
        type_names = {
            'warframe': '🎭 战甲类',
            'weapon': '⚔️ 武器类',
            'mod': '🧩 MOD 类'
        }
        
        print("\n" + "=" * 85)
        print("🎯 PRIME 市场分析报告")
        print("=" * 85)
        print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("数据来源: Warframe Market (PC)")
        print("排除物品: 伯斯顿/布莱顿/帕里斯/欧特鲁斯/雷克斯 Prime")
        print("=" * 85)
        
        # 维度1: 交易量
        print("\n" + "═" * 85)
        print("📊 【维度一】交易量排行榜 TOP 10 - 90天总成交量")
        print("═" * 85)
        
        for type_key in ['warframe', 'weapon', 'mod']:
            items = rankings['volume'].get(type_key, [])
            if not items:
                continue
            
            print(f"\n{type_names[type_key]} TOP 10")
            print("-" * 85)
            print(f"{'排名':<4} {'物品名':<28} {'90天均价':<10} {'7天均价':<10} {'成交量':<12} {'涨幅':<8}")
            print("-" * 85)
            
            for i, item in enumerate(items, 1):
                name = self._clean_name(item.chinese_name)[:26]
                print(f"{i:<4} {name:<28} "
                      f"{item.avg_price_90d:<10.1f} "
                      f"{item.avg_price_7d:<10.1f} "
                      f"{item.total_volume_90d:<12,} "
                      f"{item.price_change_7d_pct:>+7.1f}%")
        
        # 维度2: 均价
        print("\n" + "═" * 85)
        print("💰 【维度二】均价排行榜 TOP 10 - 7天成交均价")
        print("═" * 85)
        
        for type_key in ['warframe', 'weapon', 'mod']:
            items = rankings['price'].get(type_key, [])
            if not items:
                continue
            
            print(f"\n{type_names[type_key]} TOP 10")
            print("-" * 85)
            print(f"{'排名':<4} {'物品名':<28} {'7天均价':<10} {'当前最低':<10} {'当前平均':<10} {'涨幅':<8}")
            print("-" * 85)
            
            for i, item in enumerate(items, 1):
                name = self._clean_name(item.chinese_name)[:26]
                print(f"{i:<4} {name:<28} "
                      f"{item.avg_price_7d:<10.1f} "
                      f"{item.current_lowest_sell:<10.0f} "
                      f"{item.current_avg_sell:<10.1f} "
                      f"{item.price_change_7d_pct:>+7.1f}%")
        
        # 维度3: 涨幅
        print("\n" + "═" * 85)
        print("📈 【维度三】涨幅排行榜 TOP 10 - 7天价格涨幅")
        print("═" * 85)
        
        for type_key in ['warframe', 'weapon', 'mod']:
            items = rankings['gain'].get(type_key, [])
            if not items:
                continue
            
            print(f"\n{type_names[type_key]} TOP 10")
            print("-" * 85)
            print(f"{'排名':<4} {'物品名':<28} {'前7天':<10} {'近7天':<10} {'涨幅':<10} {'趋势':<6}")
            print("-" * 85)
            
            for i, item in enumerate(items, 1):
                name = self._clean_name(item.chinese_name)[:26]
                prev_price = item.avg_price_7d / (1 + item.price_change_7d_pct / 100)
                trend = self._get_trend_icon(item.price_change_7d_pct)
                print(f"{i:<4} {name:<28} "
                      f"{prev_price:<10.1f} "
                      f"{item.avg_price_7d:<10.1f} "
                      f"{item.price_change_7d_pct:>+9.1f}% "
                      f"{trend}")
        
        # 跌幅榜
        print("\n" + "═" * 85)
        print("📉 跌幅排行榜 TOP 5 - 价格下跌最多")
        print("═" * 85)
        
        for type_key in ['warframe', 'weapon', 'mod']:
            items = rankings['loss'].get(type_key, [])
            if not items:
                continue
            
            print(f"\n{type_names[type_key]} TOP 5")
            print("-" * 85)
            print(f"{'排名':<4} {'物品名':<28} {'7天均价':<10} {'跌幅':<10}")
            print("-" * 85)
            
            for i, item in enumerate(items, 1):
                name = self._clean_name(item.chinese_name)[:26]
                print(f"{i:<4} {name:<28} "
                      f"{item.avg_price_7d:<10.1f} "
                      f"{item.price_change_7d_pct:>+9.1f}%")
        
        print("\n" + "=" * 85)
        print("💡 说明: 价格单位白金 | 涨幅基于7天均价对比 | 排除5个新手武器")
        print("=" * 85 + "\n")
    
    def _get_trend_icon(self, change: float) -> str:
        if change > 20:
            return "🚀 暴涨"
        elif change > 10:
            return "📈 大涨"
        elif change > 5:
            return "📈 上涨"
        elif change < -20:
            return "💥 暴跌"
        elif change < -10:
            return "📉 大跌"
        elif change < -5:
            return "📉 下跌"
        return "➡️ 平稳"
    
    def export(self, rankings: dict, filename: str = "prime_market_report.json"):
        export = {}
        for dim, types in rankings.items():
            export[dim] = {}
            for type_name, items in types.items():
                cleaned_items = []
                for item in items:
                    item_dict = asdict(item)
                    item_dict['chinese_name'] = self._clean_name(item_dict['chinese_name'])
                    cleaned_items.append(item_dict)
                export[dim][type_name] = cleaned_items
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export, f, ensure_ascii=False, indent=2)
        print(f"📄 报告已导出: {filename}")


async def main():
    async with PrimeMarketReport() as analyzer:
        results = await analyzer.analyze_all()
        
        if results:
            print(f"\n✅ 成功分析 {len(results)} 个物品")
            rankings = analyzer.generate_rankings(results)
            analyzer.print_report(rankings)
            analyzer.export(rankings)
        else:
            print("❌ 无有效数据")


if __name__ == "__main__":
    asyncio.run(main())
