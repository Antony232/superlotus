"""
消息构建器 - 将文本转换为图片消息
"""

import os
import logging
from utils.text_to_image import text_to_image

logger = logging.getLogger(__name__)


class MessageBuilder:
    """消息构建器类 - 负责将文本转换为图片"""

    def __init__(self):
        """初始化消息构建器"""
        self.converter = text_to_image
        self.output_dir = "market_images"

        # 确保输出目录存在
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
                logger.info(f"创建图片输出目录: {self.output_dir}")
            except Exception as e:
                logger.error(f"创建输出目录失败: {e}")

    def build_image_message(self, text: str, filename: str = "message.png", method: str = "simple") -> str:
        """
        将文本转换为图片并保存

        Args:
            text: 要转换的文本内容
            filename: 输出文件名
            method: 转换方法 ("simple" | "plain" | "riven" | "research")

        Returns:
            保存的图片路径，如果失败返回 None
        """
        try:
            # 根据方法选择转换函数
            if method == "plain":
                img_byte_io = self.converter.convert_plain(text)
            elif method == "riven":
                img_byte_io = self.converter.convert_riven(text)
            elif method == "research":
                img_byte_io = self.converter.convert_research(text)
            else:  # 默认使用 simple
                img_byte_io = self.converter.convert_simple(text)

            # 构建输出路径
            output_path = os.path.join(self.output_dir, filename)

            # 保存图片
            with open(output_path, 'wb') as f:
                f.write(img_byte_io.getvalue())

            logger.info(f"图片已生成: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"生成图片失败: {e}", exc_info=True)
            return None


# 创建全局消息构建器实例
message_builder = MessageBuilder()
