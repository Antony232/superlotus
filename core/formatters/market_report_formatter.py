"""
市场报告格式化器 - 将市场数据转换为文本格式（带条形图和排名图标）
"""
from typing import Dict, List, Callable, Any
from datetime import datetime


class MarketReportFormatter:
    """市场报告文本格式化器"""

    # 类别标识映射
    CATEGORY_MARKERS = {
        'warframe': '◆ 战甲',
        'weapon': '▲ 武器',
        'mod': '● MOD'
    }

    # 所有支持的类别
    CATEGORIES = ['warframe', 'weapon', 'mod']

    @staticmethod
    def _get_display_width(text: str) -> int:
        """计算字符串的显示宽度（中文=2，英文=1）"""
        width = 0
        for char in text:
            if ord(char) > 127:  # 中文字符
                width += 2
            else:  # 英文字符
                width += 1
        return width

    @staticmethod
    def _pad_to_width(text: str, target_width: int) -> str:
        """将文本填充到目标显示宽度"""
        current_width = MarketReportFormatter._get_display_width(text)
        spaces_needed = target_width - current_width
        return text + ' ' * max(0, spaces_needed)

    @staticmethod
    def _get_rank_icon(idx: int) -> str:
        """获取排名图标（TOP 3 特殊标识）"""
        icons = ['①', '②', '③']
        return icons[idx - 1] if idx <= 3 else f'{idx:2d}'

    @staticmethod
    def _get_bar_length(value: float, max_value: float, bar_max_chars: int = 12) -> int:
        """计算条形图长度"""
        if max_value == 0:
            return 0
        ratio = abs(value) / max_value
        return int(ratio * bar_max_chars)

    @staticmethod
    def _get_heatmap_indicator(value: float, dimension_type: str) -> str:
        """根据数值获取热力图指示器（纯文本）"""
        if dimension_type == 'gain':
            if value >= 20:
                return '▲▲'  # 大涨
            elif value >= 10:
                return '▲ '   # 中涨
            elif value >= 5:
                return '↑ '    # 小涨
            else:
                return '↗ '   # 微涨
        elif dimension_type == 'loss':
            if value <= -20:
                return '▼▼'  # 大跌
            elif value <= -10:
                return '▼ '   # 中跌
            elif value <= -5:
                return '↓ '    # 小跌
            else:
                return '↘ '   # 微跌
        return '  '

    def _calculate_name_column_width(self, items: List[Dict[str, Any]]) -> int:
        """计算名称列的显示宽度"""
        max_name_width = 0
        for item in items:
            name = self._clean_name(item['chinese_name'])
            max_name_width = max(max_name_width, self._get_display_width(name))
        return max_name_width + 3  # 增加间距

    def _calculate_max_value(self, items: List[Dict[str, Any]], value_extractor: Callable[[Dict[str, Any]], float]) -> float:
        """计算最大值用于条形图比例"""
        max_value = 0.0
        for item in items:
            try:
                val = value_extractor(item)
                max_value = max(max_value, abs(val))
            except (KeyError, TypeError):
                continue
        return max_value

    def _format_ranking_section(
        self,
        items: List[Dict[str, Any]],
        category: str,
        title_suffix: str,
        value_formatter: Callable[[Dict[str, Any], int, int, int], str]
    ) -> List[str]:
        """格式化单个排名段落"""
        if not items:
            return []

        lines = []
        marker = self.CATEGORY_MARKERS.get(category, '■ 未知')
        lines.append(f"\n{marker} {title_suffix}：")

        name_width = self._calculate_name_column_width(items)
        max_value = self._calculate_max_value(items, lambda x: float(x.get('total_volume_90d', 0)))

        for idx, item in enumerate(items, 1):
            name = self._clean_name(item['chinese_name'])
            padded_name = self._pad_to_width(name, name_width)
            rank_icon = self._get_rank_icon(idx)

            formatted_line = value_formatter(item, idx, name_width, int(max_value))
            lines.append(formatted_line)

        return lines

    def format_volume_ranking(self, rankings: Dict[str, Any]) -> str:
        """格式化交易量排名"""
        lines = []

        for category in self.CATEGORIES:
            items = rankings.get('volume', {}).get(category, [])
            if not items:
                continue

            def format_item(item: Dict[str, Any], idx: int, name_width: int, max_val: int) -> str:
                value = item['total_volume_90d']
                bar = '█' * min(12, self._get_bar_length(value, max_val))
                name = self._clean_name(item['chinese_name'])
                padded_name = self._pad_to_width(name, name_width)
                rank_icon = self._get_rank_icon(idx)
                return f"  {rank_icon} {padded_name} 交易量: {value:,} {bar}"

            section_lines = self._format_ranking_section(items, category, 'TOP 10', format_item)
            lines.extend(section_lines)

        return '\n'.join(lines) if lines else "暂无数据"

    def format_price_ranking(self, rankings: Dict[str, Any]) -> str:
        """格式化均价排名"""
        lines = []

        for category in self.CATEGORIES:
            items = rankings.get('price', {}).get(category, [])
            if not items:
                continue

            def format_item(item: Dict[str, Any], idx: int, name_width: int, max_val: int) -> str:
                value = item['avg_price_90d']
                bar = '█' * min(12, self._get_bar_length(value, max_val))
                name = self._clean_name(item['chinese_name'])
                padded_name = self._pad_to_width(name, name_width)
                rank_icon = self._get_rank_icon(idx)
                return f"  {rank_icon} {padded_name} 均价: {value:.2f} {bar}"

            section_lines = self._format_ranking_section(items, category, 'TOP 10', format_item)
            lines.extend(section_lines)

        return '\n'.join(lines) if lines else "暂无数据"

    def format_gain_ranking(self, rankings: Dict[str, Any]) -> str:
        """格式化涨幅排名"""
        lines = []

        for category in self.CATEGORIES:
            items = rankings.get('gain', {}).get(category, [])
            if not items:
                continue

            def format_item(item: Dict[str, Any], idx: int, name_width: int, max_val: int) -> str:
                value = item['price_change_7d_pct']
                bar = '█' * min(12, self._get_bar_length(value, max_val))
                indicator = self._get_heatmap_indicator(value, 'gain')
                name = self._clean_name(item['chinese_name'])
                padded_name = self._pad_to_width(name, name_width)
                rank_icon = self._get_rank_icon(idx)
                return f"  {rank_icon} {padded_name} 涨幅: {indicator}{value:+.2f}% {bar}"

            section_lines = self._format_ranking_section(items, category, 'TOP 10', format_item)
            lines.extend(section_lines)

        return '\n'.join(lines) if lines else "暂无数据"

    def format_loss_ranking(self, rankings: Dict[str, Any]) -> str:
        """格式化跌幅排名"""
        lines = []

        for category in self.CATEGORIES:
            items = rankings.get('loss', {}).get(category, [])
            if not items:
                continue

            def format_item(item: Dict[str, Any], idx: int, name_width: int, max_val: int) -> str:
                value = item['price_change_7d_pct']
                bar = '█' * min(12, self._get_bar_length(value, max_val))
                indicator = self._get_heatmap_indicator(value, 'loss')
                name = self._clean_name(item['chinese_name'])
                padded_name = self._pad_to_width(name, name_width)
                rank_icon = self._get_rank_icon(idx)
                return f"  {rank_icon} {padded_name} 跌幅: {indicator}{value:+.2f}% {bar}"

            section_lines = self._format_ranking_section(items, category, 'TOP 5', format_item)
            lines.extend(section_lines)

        return '\n'.join(lines) if lines else "暂无数据"

    def _clean_name(self, name: str) -> str:
        """清理物品名称（去除'一套'等后缀）"""
        return name.replace(' 一套', '').replace('一套', '').strip()

    def _get_trend_icon(self, change: float) -> str:
        """获取趋势图标"""
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

    def format_all(self, rankings: Dict) -> List[bytes]:
        """格式化所有维度并生成图片"""
        from utils.text_to_image import text_to_image

        titles = ['交易量排名', '均价排名', '涨幅排名', '跌幅排名']
        texts = [
            self.format_volume_ranking(rankings),
            self.format_price_ranking(rankings),
            self.format_gain_ranking(rankings),
            self.format_loss_ranking(rankings)
        ]

        images = []
        for title, text in zip(titles, texts):
            img = text_to_image.convert_simple(text, title=title, max_width=600)
            images.append(img.read())

        return images
