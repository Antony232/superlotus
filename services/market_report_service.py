"""
市场报告服务层 - 处理市场报告业务逻辑
解耦 DataManager、Formatter 和图像生成
"""
import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from managers.market_data_manager import market_data_manager
from core.formatters.market_report_formatter import MarketReportFormatter
from utils.text_to_image import text_to_image
from config import config

logger = logging.getLogger(__name__)


class MarketReportService:
    """市场报告服务 - 处理市场报告的生成、格式化和图片生成"""

    def __init__(self):
        self.data_manager = market_data_manager
        self.formatter = MarketReportFormatter()
        self.image_output_dir = Path(config.market_report_settings.get('image_output_dir', './market_images'))
        self.image_output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_report(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        生成市场报告数据

        Args:
            force_refresh: 是否强制刷新数据

        Returns:
            市场报告数据，包含四维排名
        """
        try:
            rankings = await self.data_manager.get_market_report(force_refresh=force_refresh)
            if not rankings:
                logger.error("无法生成市场报告：无有效数据")
                return None

            return {
                'rankings': rankings,
                'generated_at': self.data_manager._cache_time,
                'is_cached': not force_refresh and self.data_manager.is_cache_valid()
            }
        except Exception as e:
            logger.error(f"生成市场报告失败: {e}", exc_info=True)
            return None

    def format_report(self, report_data: Dict[str, Any]) -> Dict[str, str]:
        """
        格式化市场报告为文本

        Args:
            report_data: 市场报告数据

        Returns:
            包含四个维度格式化文本的字典
        """
        if not report_data or 'rankings' not in report_data:
            return {}

        rankings = report_data['rankings']

        return {
            'volume': self.formatter.format_volume_ranking(rankings),
            'price': self.formatter.format_price_ranking(rankings),
            'gain': self.formatter.format_gain_ranking(rankings),
            'loss': self.formatter.format_loss_ranking(rankings)
        }

    def generate_report_images(self, report_data: Dict[str, Any]) -> List[Tuple[str, Path]]:
        """
        生成市场报告图片

        Args:
            report_data: 市场报告数据

        Returns:
            图片路径列表，每个元素为 (标题, 图片路径)
        """
        if not report_data or 'rankings' not in report_data:
            return []

        rankings = report_data['rankings']
        formatted_texts = self.format_report(report_data)

        image_paths = []
        dimensions = [
            ('交易量排名', 'volume'),
            ('均价排名', 'price'),
            ('涨幅排名', 'gain'),
            ('跌幅排名', 'loss')
        ]

        timestamp = report_data['generated_at'].strftime('%Y%m%d_%H%M%S')

        for title, key in dimensions:
            try:
                text = formatted_texts.get(key, '')
                if not text:
                    logger.warning(f"无法生成 {title} 图片：无数据")
                    continue

                filename = f"prime_market_report_{key}_{timestamp}.png"
                output_path = self.image_output_dir / filename

                # 生成图片并保存到文件
                img_buffer = text_to_image.convert_simple(text, title=title, max_width=600)
                with open(output_path, 'wb') as f:
                    f.write(img_buffer.read())

                image_paths.append((title, output_path))
                logger.info(f"市场报告图片已生成: {output_path}")

            except Exception as e:
                logger.error(f"生成 {title} 图片失败: {e}", exc_info=True)

        return image_paths

    async def get_report_with_images(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        获取完整的市场报告（含图片）

        Args:
            force_refresh: 是否强制刷新数据

        Returns:
            包含数据和图片路径的完整报告
        """
        report_data = await self.generate_report(force_refresh=force_refresh)
        if not report_data:
            return None

        # 生成图片（同步操作，不阻塞事件循环）
        image_paths = await asyncio.get_event_loop().run_in_executor(
            None, self.generate_report_images, report_data
        )

        return {
            'data': report_data,
            'images': image_paths,
            'formatted_text': self.format_report(report_data)
        }


# 全局服务实例
market_report_service = MarketReportService()
