import io
import os
import sys
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont


class TextToImageConverter:
    def __init__(self):
        # 配置 - 450宽度，字体分级
        self.font_size = 16  # 正文字体 (T4)
        self.title_font_size = 40  # 标题字体 (T1)
        self.tier_font_size = 18  # 等级标题字体（比正文大）
        self.task_font_size = 20  # 深层科研任务字体（比等级标题更大）
        self.timestamp_font_size = 12  # 时间标注字体（较小）
        self.line_spacing = 8  # 行间距
        self.padding = 15  # 边距
        self.max_width = 450  # 默认宽度不变
        self.timestamp_color = (255, 80, 80)  # 时间标注红色 #FF5050

        # 猫娘风格配色方案（协调统一，柔和可爱）
        self.bg_color = (255, 248, 252)  # 极浅粉色背景 #FFF8FC
        self.text_color = (100, 80, 120)  # 深紫色文字 #645078
        self.title_color = (255, 140, 180)  # 浅粉色标题 #FF8CB4
        self.tier_color = (200, 80, 160)  # 玫紫色等级标题 #C850A0
        self.steel_color = (255, 100, 120)  # 粉红色钢铁任务 #FF6478
        self.normal_color = (160, 140, 220)  # 淡紫色普通任务 #A08CDC
        self.stats_color = (140, 120, 160)  # 中紫色统计信息 #8C78A0
        self.border_color = (255, 180, 200)  # 浅粉色边框 #FFB4C8
        # 赏金任务配色
        self.bounty_title_color = (255, 100, 120)  # 赏金标题粉红色 #FF6478
        self.bounty_task_color = (180, 100, 200)  # 赏金任务行紫红色 #B464C8
        self.bounty_desc_color = (100, 120, 180)  # 赏金描述蓝紫色 #6478B4
        self.bounty_zariman_color = (255, 140, 100)  # 扎里曼橙粉色 #FF8C64
        self.bounty_entra_color = (100, 180, 160)  # 英择谛青绿色 #64B4A0
        self.bounty_hex_color = (180, 100, 180)  # 1999紫罗兰色 #B464B4

        # T1-T4 统一样式配置
        # T1: 大标题（居中）
        # T2: 派系标题
        # T3: 任务行
        # T4: 描述行
        self.T_styles = {
            "T1": {
                "font_size": 40,
                "color": self.title_color,  # #FF8CB4 粉色
                "align": "center"
            },
            "T2": {
                "font_size": 22,
                "color": (255, 140, 100),  # #FF8C64 橙色
                "align": "left"
            },
            "T3": {
                "font_size": 20,
                "color": self.bounty_task_color,  # #B464C8 紫红色
                "align": "left"
            },
            "T4": {
                "font_size": 16,
                "color": self.bounty_desc_color,  # #6478B4 蓝紫色
                "align": "left"
            }
        }
        # 深层科研配色
        self.archimedea_title_color = (255, 120, 80)  # 深层科研标题橙红色 #FF7850
        self.archimedea_task_color = (180, 120, 200)  # 深层科研任务紫红色 #B478C8
        self.archimedea_condition_color = (100, 140, 180)  # 条件描述蓝紫色 #648CB4
        self.archimedea_var_color = (100, 180, 140)  # 可选变量青绿色 #64B48C
        # 市场报告配色
        self.market_warframe_color = (255, 140, 80)  # 战甲橙色 #FF8C50
        self.market_weapon_color = (80, 180, 140)  # 武器青绿色 #50B48C
        self.market_mod_color = (140, 100, 200)  # MOD紫色 #8C64C8
        # 日历配色
        self.calendar_date_color = (255, 120, 100)  # 日期粉红色 #FF7864
        self.calendar_challenge_color = (180, 100, 200)  # 挑战名称紫红色 #B464C8
        self.calendar_desc_color = (100, 120, 160)  # 描述蓝灰色 #6478A0
        self.calendar_reward_color = (100, 180, 140)  # 奖励青绿色 #64B48C
        self.calendar_upgrade_color = (200, 140, 80)  # 升级项橙色 #C88C50
        # 午夜电波配色
        self.nightwave_daily_color = (255, 140, 100)  # 日常挑战橙色 #FF8C64
        self.nightwave_weekly_color = (100, 180, 160)  # 周常挑战青绿色 #64B4A0
        self.nightwave_elite_color = (180, 100, 200)  # 精英挑战紫红色 #B464C8

        # 路径设置
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.abspath(os.path.join(current_dir, ".."))
        self.fonts_dir = os.path.join(self.project_root, "resources/fonts")

        # 字体文件
        self.font_files = {
            "sanjikengqiangti": "sanjikengqiangti.ttf",
            "msyh": "msyh.ttc",
            "msyhbd": "msyhbd.ttc",
            "arial": "arial.ttf"
        }

        # 加载字体
        self.font = None
        self.title_font = None
        self.tier_font = None

        try:
            sanjikengqiangti_path = os.path.join(self.fonts_dir, self.font_files["sanjikengqiangti"])

            self.font = ImageFont.truetype(sanjikengqiangti_path, self.font_size, encoding="utf-8")
            self.title_font = ImageFont.truetype(sanjikengqiangti_path, self.title_font_size, encoding="utf-8")
            self.tier_font = ImageFont.truetype(sanjikengqiangti_path, self.tier_font_size, encoding="utf-8")
            self.task_font = ImageFont.truetype(sanjikengqiangti_path, self.task_font_size, encoding="utf-8")
            self.timestamp_font = ImageFont.truetype(sanjikengqiangti_path, self.timestamp_font_size, encoding="utf-8")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"加载字体失败，使用默认字体: {e}")
            self.font = ImageFont.load_default(size=self.font_size)
            self.title_font = ImageFont.load_default(size=self.title_font_size)
            self.tier_font = ImageFont.load_default(size=self.tier_font_size)
            self.task_font = ImageFont.load_default(size=self.task_font_size)
            self.timestamp_font = ImageFont.load_default(size=self.timestamp_font_size)

    def _get_text_width(self, text, font=None):
        """获取文本宽度"""
        if font is None:
            font = self.font
        draw = ImageDraw.Draw(Image.new('RGB', (1, 1), self.bg_color))
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]

    def _get_timestamp_text(self) -> str:
        """生成时间标注文本 - 使用北京时间(UTC+8)"""
        beijing_tz = timezone(timedelta(hours=8))
        now = datetime.now(beijing_tz)
        return f"超级小莲 {now.strftime('%m-%d %H:%M:%S')}"

    def _draw_timestamp(self, draw, img_width, y_position):
        """绘制时间标注（右对齐，红色，小字号）"""
        timestamp_text = self._get_timestamp_text()
        text_width = self._get_text_width(timestamp_text, self.timestamp_font)
        x = img_width - self.padding - text_width
        draw.text((x, y_position), timestamp_text, font=self.timestamp_font, fill=self.timestamp_color, encoding="utf-8")

    def convert_simple(self, text, title="", max_width=None):
        """文本转图片函数 - 支持日历、午夜电波、赏金等多种格式"""
        if max_width is None:
            max_width = self.max_width

        # 处理文本行
        lines = text.split('\n')

        # 调试日志：查看处理前的文本行
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"convert_simple: 处理文本行，共{len(lines)}行")
        for i, line in enumerate(lines):
            logger.debug(f"  行{i}: '{line}'")

        # 重新格式化行，标记行类型
        formatted_lines = []  # 每行包含 (内容, 类型)
        in_bounty_section = False  # 跟踪是否在赏金任务区域
        last_was_bounty_task = False  # 上一行是否是赏金任务行
        in_archimedea_section = False  # 跟踪是否在深层科研区域
        in_calendar_section = False  # 跟踪是否在日历区域
        in_nightwave_section = False  # 跟踪是否在午夜电波区域
        in_void_trader_section = False  # 跟踪是否在虚空商人区域
        import re

        for line in lines:
            line_stripped = line.strip()

            # 跳过分割线（日历中）
            if line_stripped.startswith('=') and len(line_stripped) > 10:
                continue

            # 跳过空行（但在日历和午夜电波中保留适当分隔）
            if not line_stripped:
                last_was_bounty_task = False
                in_bounty_section = False
                # 日历和午夜电波中空行作为分隔，添加一个小的间隔标记
                if in_calendar_section or in_nightwave_section:
                    formatted_lines.append(("", 'spacer'))
                continue

            # 检测午夜电波区域
            if '午夜电波' in line_stripped and '赛季' in line_stripped:
                formatted_lines.append((line_stripped, 'nightwave_title'))
                in_nightwave_section = True
                in_calendar_section = False
                in_bounty_section = False
                in_archimedea_section = False
                continue

            # 午夜电波挑战行（以数字+点开头，包含[声望]）
            if in_nightwave_section and re.match(r'^\d+\.\[声望\+', line_stripped):
                formatted_lines.append((line_stripped, 'nightwave_challenge'))
                continue

            # 检测日历区域（包含 1999 或日历相关标识）
            if '1999' in line_stripped and ('📅' in line_stripped or '春季' in line_stripped or '夏季' in line_stripped or '秋季' in line_stripped or '冬季' in line_stripped):
                formatted_lines.append((line_stripped, 'calendar_header'))
                in_calendar_section = True
                in_nightwave_section = False
                in_bounty_section = False
                in_archimedea_section = False
                continue

            # 日历倒计时行
            if in_calendar_section and '⏰' in line_stripped:
                formatted_lines.append((line_stripped, 'calendar_countdown'))
                continue

            # 日历日期行（格式：数字 日期  类型，如 "101  2月16日           待办清单"）
            if in_calendar_section and re.match(r'^\d+\s+\d+月\d+日', line_stripped):
                formatted_lines.append((line_stripped, 'calendar_date'))
                continue

            # 日历内容行（以4个空格开头）
            if in_calendar_section and line.startswith('    ') and not line.startswith('     '):
                # 判断是挑战名称还是描述/奖励
                if any(keyword in line_stripped for keyword in ['待办清单', '选择奖励', '增益覆写']):
                    formatted_lines.append((line_stripped, 'calendar_type'))
                elif re.match(r'^\d+月\d+日', line_stripped):
                    # 可能是日期行
                    formatted_lines.append((line_stripped, 'calendar_date'))
                else:
                    # 根据上一行判断类型
                    if formatted_lines and formatted_lines[-1][1] == 'calendar_date':
                        # 日期后的第一行是挑战名称或奖励项
                        formatted_lines.append((line_stripped, 'calendar_name'))
                    elif formatted_lines and formatted_lines[-1][1] in ['calendar_name', 'calendar_desc']:
                        # 挑战名称后的行是描述
                        formatted_lines.append((line_stripped, 'calendar_desc'))
                    else:
                        formatted_lines.append((line_stripped, 'calendar_desc'))
                continue

            # 如果是深层科研标题行（【深层科研】开头）或时光科研标题行（【时光科研】开头）
            if line_stripped.startswith('【深层科研】') or line_stripped.startswith('【时光科研】'):
                formatted_lines.append((line_stripped, 'archimedea_title'))
                in_archimedea_section = True
                in_bounty_section = False
                in_calendar_section = False
                in_nightwave_section = False
                last_was_bounty_task = False
                continue

            # 如果是深层科研可选风险变量标题（【可选风险变量】开头）
            if in_archimedea_section and line_stripped.startswith('【可选风险变量】'):
                formatted_lines.append((line_stripped, 'archimedea_var_title'))
                in_archimedea_section = True
                last_was_bounty_task = False
                continue

            # 如果是深层科研任务行（在深层科研区域内，以数字+点开头）
            if in_archimedea_section:
                if re.match(r'^\d+\.', line_stripped):
                    formatted_lines.append((line_stripped, 'archimedea_task'))
                    last_was_bounty_task = False
                    continue
                elif line.startswith('  '):
                    formatted_lines.append((line_stripped, 'archimedea_condition'))
                    last_was_bounty_task = False
                    continue

            # 深层科研可选风险变量列表（在可选风险变量标题之后的行，且包含多个用空格隔开的变量）
            if in_archimedea_section and line_stripped and '  ' in line_stripped and not line_stripped.startswith('【') and not line.startswith('  ') and not re.match(r'^\d+\.', line_stripped):
                # 这行是变量列表，用空格分隔
                formatted_lines.append((line_stripped, 'archimedea_var_list'))
                last_was_bounty_task = False
                continue

            # 如果是赏金标题行（【扎里曼】、【英择谛】、【1999】开头）
            if (line_stripped.startswith('【扎里曼】') or line_stripped.startswith('【英择谛】') or line_stripped.startswith('【1999】')):
                formatted_lines.append((line_stripped, 'bounty_title'))
                in_bounty_section = True
                in_archimedea_section = False
                in_calendar_section = False
                in_nightwave_section = False
                last_was_bounty_task = False
                continue

            # 如果是赏金任务行（在赏金区域内，以数字+点开头）
            if in_bounty_section:
                # 检查是否是任务行：数字+点开头，且包含括号（扎里曼/英择谛格式）或包含"霍瓦尼亚-"（1999格式）
                import re
                if re.match(r'^\d+\.', line_stripped) and (('(' in line_stripped and ')' in line_stripped) or '霍瓦尼亚-' in line_stripped):
                    formatted_lines.append((line_stripped, 'bounty_task'))
                    last_was_bounty_task = True
                    continue
                # 检查是否是描述行：紧接在任务行之后，不是任务行
                elif last_was_bounty_task and not re.match(r'^\d+\.', line_stripped):
                    formatted_lines.append((line_stripped, 'bounty_desc'))
                    last_was_bounty_task = False
                    continue
                # 其他情况
                else:
                    last_was_bounty_task = False
                    # 可能是下一个区域标题或空行前的其他内容
                    if line_stripped.startswith('【') and line_stripped.endswith('】'):
                        in_bounty_section = False

            # 如果是裂缝等级标题（以【开头以】结尾，且包含"裂缝"）
            if line_stripped.startswith('【') and line_stripped.endswith('】') and '裂缝' in line_stripped:
                formatted_lines.append((line_stripped, 'fissure_tier_title'))
                continue

            # 如果是裂缝行（以【钢铁】或【普通】开头）
            if line_stripped.startswith('【钢铁】') or line_stripped.startswith('【普通】'):
                formatted_lines.append((line_stripped, 'fissure_item'))
                continue

            # 虚空商人区域检测
            if line_stripped.startswith('【虚空商人】'):
                formatted_lines.append((line_stripped, 'void_trader_title'))
                in_void_trader_section = True
                in_calendar_section = False
                in_nightwave_section = False
                in_bounty_section = False
                in_archimedea_section = False
                continue

            # 虚空商人商品列表标题
            if in_void_trader_section and line_stripped.startswith('【商品列表】'):
                formatted_lines.append((line_stripped, 'void_trader_list_title'))
                continue

            # 虚空商人商品行（以4个空格开头，包含数字价格）
            if in_void_trader_section and line.startswith('    ') and not line.startswith('     '):
                formatted_lines.append((line_stripped, 'void_trader_item'))
                continue

            # 虚空商人信息行（以2个空格开头）
            if in_void_trader_section and line.startswith('  ') and not line.startswith('    '):
                formatted_lines.append((line_stripped, 'void_trader_info'))
                continue

            # 如果是标题行（包含"查询"或"结果"）
            if "查询" in line_stripped or "结果" in line_stripped:
                formatted_lines.append((line_stripped, 'title'))
                continue

            # 如果是分割线
            if line_stripped.startswith('=') or line_stripped.startswith('-') or line_stripped.startswith('—'):
                formatted_lines.append((line_stripped, 'divider'))
                continue

            # 如果是平原标题行（以【开头以】结尾）
            if line_stripped.startswith('【') and line_stripped.endswith('】'):
                formatted_lines.append((line_stripped, 'plain_title'))
                continue

            # 市场报告类别标题（战甲、武器、MOD）
            if '◆ 战甲' in line_stripped:
                formatted_lines.append((line_stripped, 'market_warframe'))
                continue
            if '▲ 武器' in line_stripped:
                formatted_lines.append((line_stripped, 'market_weapon'))
                continue
            if '● MOD' in line_stripped:
                formatted_lines.append((line_stripped, 'market_mod'))
                continue

            # 如果是项目行（以•开头）
            if line_stripped.startswith('•'):
                formatted_lines.append((line_stripped, 'item'))
                continue

            # 其他情况视为普通文本
            formatted_lines.append((line_stripped, 'text'))

        # 计算图片高度
        line_heights = []
        for content, line_type in formatted_lines:
            # 处理间隔标记
            if line_type == 'spacer':
                line_heights.append(self.line_spacing)
                continue

            if not content.strip():
                continue

            # 根据行类型确定字体高度
            if line_type == 'title':
                font_height = self.tier_font_size
            elif line_type in ['plain_title', 'fissure_tier_title', 'bounty_title', 'archimedea_title', 'archimedea_var_title',
                              'calendar_header', 'calendar_date', 'nightwave_title']:
                font_height = self.tier_font_size
            elif line_type in ['archimedea_task', 'nightwave_challenge']:
                font_height = self.task_font_size
            elif line_type in ['archimedea_var_list', 'calendar_name', 'calendar_desc']:
                font_height = self.font_size
            elif line_type == 'divider':
                font_height = self.font_size
            else:  # fissure_item, item, text, bounty_task, bounty_desc, archimedea_condition
                # 检查是否需要换行
                line_width = self._get_text_width(content)
                available_width = max_width - 2 * self.padding

                if line_width > available_width:
                    # 需要多行显示
                    words = content.split()
                    lines_needed = 1
                    current_line = ""
                    for word in words:
                        if self._get_text_width(current_line + " " + word) > available_width:
                            lines_needed += 1
                            current_line = word
                        else:
                            current_line += " " + word if current_line else word
                    font_height = (self.font_size + self.line_spacing) * lines_needed
                else:
                    font_height = self.font_size

            line_heights.append(font_height + self.line_spacing)

        # 计算总高度
        total_height = self.padding * 2

        if title:
            total_height += self.title_font_size + self.line_spacing * 2

        total_height += sum(line_heights)

        # 添加时间标注高度
        total_height += self.timestamp_font_size + self.line_spacing

        # 创建图片
        img = Image.new('RGB', (max_width, total_height), self.bg_color)
        draw = ImageDraw.Draw(img)

        y = self.padding

        # 绘制标题（40号大字）
        if title:
            title_width = self._get_text_width(title, self.title_font)
            x = (max_width - title_width) // 2
            draw.text((x, y), title, font=self.title_font, fill=self.title_color, encoding="utf-8")
            y += self.title_font_size + self.line_spacing * 2

        # 绘制正文
        for content, line_type in formatted_lines:
            # 处理间隔标记
            if line_type == 'spacer':
                y += self.line_spacing
                continue

            if not content.strip():
                y += self.line_spacing
                continue

            # 根据行类型确定字体、颜色和样式
            if line_type == 'title':
                # 主标题：玫紫色，18号字体，左对齐
                draw.text((self.padding, y), content, font=self.tier_font, fill=self.tier_color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'calendar_header':
                # 日历标题：粉红色，18号字体
                draw.text((self.padding, y), content, font=self.tier_font, fill=self.calendar_date_color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'calendar_countdown':
                # 日历倒计时：橙红色，普通字体
                draw.text((self.padding, y), content, font=self.font, fill=self.bounty_zariman_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'calendar_date':
                # 日历日期行：粉红色，18号字体
                draw.text((self.padding, y), content, font=self.tier_font, fill=self.calendar_date_color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'calendar_name':
                # 日历挑战名称/升级项名称：紫红色，普通字体
                draw.text((self.padding, y), content, font=self.font, fill=self.calendar_challenge_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'calendar_desc':
                # 日历描述：蓝灰色，普通字体
                draw.text((self.padding, y), content, font=self.font, fill=self.calendar_desc_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'nightwave_title':
                # 午夜电波标题：紫红色，18号字体
                draw.text((self.padding, y), content, font=self.tier_font, fill=self.bounty_task_color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'nightwave_challenge':
                # 午夜电波挑战行：根据声望值选择颜色
                if '[声望+1000]' in content or '[声望+3000]' in content:
                    color = self.nightwave_daily_color  # 日常/普通橙色
                elif '[声望+4500]' in content:
                    color = self.nightwave_weekly_color  # 周常青绿色
                elif '[声望+7000]' in content or '[声望+5000]' in content:
                    color = self.nightwave_elite_color  # 精英紫红色
                else:
                    color = self.text_color
                draw.text((self.padding, y), content, font=self.font, fill=color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'bounty_title':
                # 赏金标题：根据区域选择颜色，18号字体
                if content.startswith('【扎里曼】'):
                    color = self.bounty_zariman_color  # 橙粉色
                elif content.startswith('【英择谛】'):
                    color = self.bounty_entra_color  # 青绿色
                elif content.startswith('【1999】'):
                    color = self.bounty_hex_color  # 紫罗兰色
                else:
                    color = self.bounty_title_color  # 默认粉红色
                draw.text((self.padding, y), content, font=self.tier_font, fill=color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'bounty_task':
                # 赏金任务行：紫红色，普通字体
                draw.text((self.padding, y), content, font=self.font, fill=self.bounty_task_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'bounty_desc':
                # 赏金描述行：蓝紫色，普通字体
                draw.text((self.padding, y), content, font=self.font, fill=self.bounty_desc_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'archimedea_title':
                # 深层科研标题：橙红色，18号字体
                draw.text((self.padding, y), content, font=self.tier_font, fill=self.archimedea_title_color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'archimedea_task':
                # 深层科研任务行：根据任务序号使用不同颜色，20号字体
                if content.startswith('1.'):
                    color = (255, 140, 80)  # 任务1橙色 #FF8C50
                elif content.startswith('2.'):
                    color = (80, 180, 140)  # 任务2青绿色 #50B48C
                elif content.startswith('3.'):
                    color = (140, 100, 200)  # 任务3紫色 #8C64C8
                else:
                    color = self.archimedea_task_color
                draw.text((self.padding, y), content, font=self.task_font, fill=color, encoding="utf-8")
                y += self.task_font_size + self.line_spacing

            elif line_type == 'archimedea_condition':
                # 深层科研条件行：紫红色 #B464C8，普通字体
                draw.text((self.padding, y), content, font=self.font, fill=self.bounty_task_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'archimedea_var_title':
                # 深层科研可选变量标题：橙红色，18号字体
                draw.text((self.padding, y), content, font=self.tier_font, fill=self.archimedea_title_color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'archimedea_var_list':
                # 深层科研可选变量列表：青绿色，普通字体，一行显示
                draw.text((self.padding, y), content, font=self.font, fill=self.archimedea_var_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'void_trader_title':
                # 虚空商人标题：玫紫色 #C850A0，18号字体
                draw.text((self.padding, y), content, font=self.tier_font, fill=self.tier_color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'void_trader_list_title':
                # 虚空商人商品列表标题：玫紫色 #C850A0，18号字体
                draw.text((self.padding, y), content, font=self.tier_font, fill=self.tier_color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'void_trader_info':
                # 虚空商人信息行：深紫色，普通字体
                draw.text((self.padding, y), content, font=self.font, fill=self.text_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'void_trader_item':
                # 虚空商人商品行：蓝紫色（T4样式），16号字体
                draw.text((self.padding, y), content, font=self.font, fill=self.bounty_desc_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'divider':
                # 分割线：浅粉色，普通字体
                draw.text((self.padding, y), content, font=self.font, fill=self.border_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'market_warframe':
                # 战甲类别标题：橙色 #FF8C50
                draw.text((self.padding, y), content, font=self.tier_font, fill=self.market_warframe_color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'market_weapon':
                # 武器类别标题：青绿色 #50B48C
                draw.text((self.padding, y), content, font=self.tier_font, fill=self.market_weapon_color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'market_mod':
                # MOD类别标题：紫色 #8C64C8
                draw.text((self.padding, y), content, font=self.tier_font, fill=self.market_mod_color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'plain_title' or line_type == 'fissure_tier_title':
                # 平原图/裂缝等级标题：粉红色，18号字体
                draw.text((self.padding, y), content, font=self.tier_font, fill=self.steel_color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'fissure_item':
                # 裂缝行：根据前缀选择颜色
                if content.startswith('【钢铁】'):
                    color = self.steel_color  # 粉红色
                elif content.startswith('【普通】'):
                    color = self.normal_color  # 淡紫色
                else:
                    color = self.text_color
                draw.text((self.padding, y), content, font=self.font, fill=color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'item':
                # 项目行：深紫色，普通字体
                draw.text((self.padding, y), content, font=self.font, fill=self.text_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'text':
                # 普通文本：中紫色，普通字体
                draw.text((self.padding, y), content, font=self.font, fill=self.stats_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

        # 绘制时间标注（右对齐，红色，小字号）
        y += self.line_spacing  # 添加一点间距
        self._draw_timestamp(draw, max_width, y)

        # 简单边框（浅粉色）
        draw.rectangle(
            [(1, 1), (max_width - 2, total_height - 2)],
            outline=self.border_color,
            width=1
        )

        # 保存为字节流
        img_byte_io = io.BytesIO()
        img.save(img_byte_io, format='PNG', quality=90, optimize=True)
        img_byte_io.seek(0)

        return img_byte_io

    def convert_plain(self, text, title="", max_width=450):
        """平原查询专用文本转图片（简化版本）"""
        # 平原专用配色
        plain_bg_color = (255, 248, 252)  # 极浅粉色背景 #FFF8FC
        plain_text_color = (100, 80, 120)  # 深紫色文字 #645078
        plain_title_color = (180, 100, 200)  # 紫红色标题 #B464C8
        plain_section_color = (160, 80, 180)  # 紫色章节标题 #A050B4
        plain_time_color = (220, 80, 100)  # 粉红色时间 #DC5064
        plain_border_color = (220, 180, 220)  # 浅紫色边框 #DCB4DC

        # 处理文本行
        lines = text.split('\n')
        
        # 计算图片高度
        line_heights = []
        for line in lines:
            line = line.strip()
            if line:
                # 简单处理，每行高度相同
                line_heights.append(self.font_size + self.line_spacing)

        # 计算总高度
        total_height = self.padding * 2

        if title:
            total_height += self.title_font_size + self.line_spacing * 2

        total_height += sum(line_heights)

        # 添加时间标注高度
        total_height += self.timestamp_font_size + self.line_spacing

        # 创建图片
        img = Image.new('RGB', (max_width, total_height), plain_bg_color)
        draw = ImageDraw.Draw(img)

        y = self.padding

        # 绘制标题
        if title:
            title_width = self._get_text_width(title, self.title_font)
            x = (max_width - title_width) // 2
            draw.text((x, y), title, font=self.title_font, fill=plain_title_color, encoding="utf-8")
            y += self.title_font_size + self.line_spacing * 2

        # 绘制正文
        for line in lines:
            line = line.strip()
            if not line:
                y += self.line_spacing
                continue

            # 确定颜色（根据行内容简单分类）
            if "平原昼夜状态查询" in line:
                color = plain_title_color
                font = self.tier_font
                line_height = self.tier_font_size
            elif "===" in line or "---" in line or "===" in line:
                color = plain_border_color
                font = self.font
                line_height = self.font_size
            elif line.startswith('【') and line.endswith('】'):
                color = plain_section_color
                font = self.tier_font
                line_height = self.tier_font_size
            elif "剩余时间:" in line or "切换时间:" in line:
                color = plain_time_color
                font = self.font
                line_height = self.font_size
            else:
                color = plain_text_color
                font = self.font
                line_height = self.font_size

            # 绘制文本
            draw.text((self.padding, y), line, font=font, fill=color, encoding="utf-8")
            y += line_height + self.line_spacing

        # 绘制时间标注（右对齐，红色，小字号）
        y += self.line_spacing
        self._draw_timestamp(draw, max_width, y)

        # 简单边框
        draw.rectangle(
            [(1, 1), (max_width - 2, total_height - 2)],
            outline=plain_border_color,
            width=1
        )

        # 保存为字节流
        img_byte_io = io.BytesIO()
        img.save(img_byte_io, format='PNG', quality=90, optimize=True)
        img_byte_io.seek(0)

        return img_byte_io

    def convert_riven(self, text, title="", max_width=600):
        """紫卡查询专用文本转图片（宽度调整为600）"""
        # 紫卡专用配色（使用紫色系，与裂缝查询区分但保持协调）
        riven_bg_color = (255, 248, 252)  # 极浅粉色背景 #FFF8FC
        riven_text_color = (100, 80, 120)  # 深紫色文字 #645078
        riven_title_color = (180, 100, 200)  # 紫红色标题 #B464C8
        riven_section_color = (160, 80, 180)  # 紫色章节标题 #A050B4
        riven_price_color = (220, 80, 100)  # 粉红色价格 #DC5064
        riven_border_color = (220, 180, 220)  # 浅紫色边框 #DCB4DC

        # 处理文本行
        lines = text.split('\n')

        # 计算图片高度
        line_heights = []
        for line in lines:
            line = line.strip()
            if line:
                # 简单处理，每行高度相同
                line_heights.append(self.font_size + self.line_spacing)

        # 计算总高度
        total_height = self.padding * 2

        if title:
            total_height += self.title_font_size + self.line_spacing * 2

        total_height += sum(line_heights)

        # 添加时间标注高度
        total_height += self.timestamp_font_size + self.line_spacing

        # 创建图片
        img = Image.new('RGB', (max_width, total_height), riven_bg_color)
        draw = ImageDraw.Draw(img)

        y = self.padding

        # 绘制标题
        if title:
            title_width = self._get_text_width(title, self.title_font)
            x = (max_width - title_width) // 2
            draw.text((x, y), title, font=self.title_font, fill=riven_title_color, encoding="utf-8")
            y += self.title_font_size + self.line_spacing * 2

        # 绘制正文
        for line in lines:
            line = line.strip()
            if not line:
                y += self.line_spacing
                continue

            # 确定颜色（根据行内容简单分类）
            if '喵~ 找到【' in line and '】的紫卡啦！' in line:
                color = riven_title_color
            elif '价格：' in line:
                color = riven_price_color
            elif '【第' in line and '条】' in line:
                color = riven_section_color
            elif '段位要求：' in line or '紫卡属性：' in line:
                color = riven_text_color
            elif '卖家：' in line:
                color = (100, 160, 100)  # 卖家用绿色
            elif '提示：' in line:
                color = (200, 120, 160)  # 提示用粉色
            else:
                color = riven_text_color

            # 绘制文本
            draw.text((self.padding, y), line, font=self.font, fill=color, encoding="utf-8")
            y += self.font_size + self.line_spacing

        # 绘制时间标注（右对齐，红色，小字号）
        y += self.line_spacing
        self._draw_timestamp(draw, max_width, y)

        # 简单边框
        draw.rectangle(
            [(1, 1), (max_width - 2, total_height - 2)],
            outline=riven_border_color,
            width=1
        )

        # 保存为字节流
        img_byte_io = io.BytesIO()
        img.save(img_byte_io, format='PNG', quality=90, optimize=True)
        img_byte_io.seek(0)

        return img_byte_io

    def convert_research(self, text, max_width=450):
        """科研查询专用文本转图片 - 同时显示深层科研和时光科研"""
        # 处理文本行
        lines = text.split('\n')

        # 重新格式化行，标记行类型
        formatted_lines = []  # 每行包含 (内容, 类型)

        for line in lines:
            line = line.strip()

            # 跳过空行
            if not line:
                continue

            # 如果是科研标题行（【深层科研】或【时光科研】）
            if line.startswith('【深层科研】') or line.startswith('【时光科研】'):
                formatted_lines.append((line, 'research_title'))
                continue

            # 如果是科研可选风险变量标题（【可选风险变量】）
            if line.startswith('【可选风险变量】'):
                formatted_lines.append((line, 'research_var_title'))
                continue

            # 如果是任务行（以数字+点开头）
            import re
            if re.match(r'^\d+\.', line):
                formatted_lines.append((line, 'research_task'))
                continue

            # 如果是条件行（以两个空格开头）
            if line.startswith('  '):
                formatted_lines.append((line, 'research_condition'))
                continue

            # 如果是变量列表（不包含特殊标记，且有多个空格分隔）
            if '  ' in line and not line.startswith('【') and not line.startswith('  ') and not re.match(r'^\d+\.', line):
                formatted_lines.append((line, 'research_var_list'))
                continue

            # 其他情况作为普通文本
            formatted_lines.append((line, 'text'))

        # 计算图片高度
        line_heights = []
        for content, line_type in formatted_lines:
            if not content.strip():
                continue

            # 根据行类型确定字体高度
            if line_type == 'research_title' or line_type == 'research_var_title':
                font_height = self.tier_font_size
            elif line_type == 'research_task':
                font_height = self.task_font_size
            else:
                # 检查是否需要换行
                line_width = self._get_text_width(content)
                available_width = max_width - 2 * self.padding

                if line_width > available_width:
                    # 需要多行显示
                    words = content.split()
                    lines_needed = 1
                    current_line = ""
                    for word in words:
                        if self._get_text_width(current_line + " " + word) > available_width:
                            lines_needed += 1
                            current_line = word
                        else:
                            current_line += " " + word if current_line else word
                    font_height = (self.font_size + self.line_spacing) * lines_needed
                else:
                    font_height = self.font_size

            line_heights.append(font_height + self.line_spacing)

        # 计算总高度
        total_height = self.padding * 2 + sum(line_heights)

        # 添加时间标注高度
        total_height += self.timestamp_font_size + self.line_spacing

        # 创建图片
        img = Image.new('RGB', (max_width, total_height), self.bg_color)
        draw = ImageDraw.Draw(img)

        y = self.padding

        # 绘制正文
        for content, line_type in formatted_lines:
            if not content.strip():
                y += self.line_spacing
                continue

            # 根据行类型确定字体、颜色和样式
            if line_type == 'research_title':
                # 科研标题：橙红色，18号字体
                draw.text((self.padding, y), content, font=self.tier_font, fill=self.archimedea_title_color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'research_task':
                # 科研任务行：根据任务序号使用不同颜色，20号字体
                if content.startswith('1.'):
                    color = (255, 140, 80)  # 任务1橙色 #FF8C50
                elif content.startswith('2.'):
                    color = (80, 180, 140)  # 任务2青绿色 #50B48C
                elif content.startswith('3.'):
                    color = (140, 100, 200)  # 任务3紫色 #8C64C8
                else:
                    color = self.archimedea_task_color
                draw.text((self.padding, y), content, font=self.task_font, fill=color, encoding="utf-8")
                y += self.task_font_size + self.line_spacing

            elif line_type == 'research_condition':
                # 科研条件行：紫红色 #B464C8，普通字体
                draw.text((self.padding, y), content, font=self.font, fill=self.bounty_task_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'research_var_title':
                # 科研可选变量标题：橙红色，18号字体
                draw.text((self.padding, y), content, font=self.tier_font, fill=self.archimedea_title_color, encoding="utf-8")
                y += self.tier_font_size + self.line_spacing

            elif line_type == 'research_var_list':
                # 科研可选变量列表：青绿色，普通字体
                draw.text((self.padding, y), content, font=self.font, fill=self.archimedea_var_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

            elif line_type == 'text':
                # 普通文本：中紫色，普通字体
                draw.text((self.padding, y), content, font=self.font, fill=self.stats_color, encoding="utf-8")
                y += self.font_size + self.line_spacing

        # 绘制时间标注（右对齐，红色，小字号）
        y += self.line_spacing
        self._draw_timestamp(draw, max_width, y)

        # 简单边框（浅粉色）
        draw.rectangle(
            [(1, 1), (max_width - 2, total_height - 2)],
            outline=self.border_color,
            width=1
        )

        # 保存为字节流
        img_byte_io = io.BytesIO()
        img.save(img_byte_io, format='PNG', quality=90, optimize=True)
        img_byte_io.seek(0)

        return img_byte_io

    def convert_structured(self, content: list, max_width=None) -> io.BytesIO:
        """
        结构化内容转图片
        
        Args:
            content: 内容列表，每项为 {"type": "T1-T4", "text": "内容", "align": "left/center"}
            max_width: 图片宽度
        
        Returns:
            图片字节流
        """
        if max_width is None:
            max_width = self.max_width

        # 为每种字号创建字体缓存
        font_cache = {}
        for t_type, style in self.T_styles.items():
            font_size = style["font_size"]
            if font_size not in font_cache:
                try:
                    font_cache[font_size] = ImageFont.truetype(
                        os.path.join(self.fonts_dir, self.font_files["sanjikengqiangti"]),
                        font_size, encoding="utf-8"
                    )
                except Exception:
                    font_cache[font_size] = ImageFont.load_default(size=font_size)

        # 计算图片高度
        line_heights = []
        for item in content:
            text = item.get("text", "")
            t_type = item.get("type", "T4")
            
            if not text.strip():
                line_heights.append(self.line_spacing)
                continue

            style = self.T_styles.get(t_type, self.T_styles["T4"])
            font_size = style["font_size"]
            font = font_cache.get(font_size, self.font)
            
            line_heights.append(font_size + self.line_spacing)

        # 计算总高度
        total_height = self.padding * 2
        total_height += sum(line_heights)
        total_height += self.timestamp_font_size + self.line_spacing * 2

        # 创建图片
        img = Image.new('RGB', (max_width, total_height), self.bg_color)
        draw = ImageDraw.Draw(img)

        y = self.padding

        # 绘制内容
        for item in content:
            text = item.get("text", "")
            t_type = item.get("type", "T4")
            align = item.get("align", "left")

            if not text.strip():
                y += self.line_spacing
                continue

            style = self.T_styles.get(t_type, self.T_styles["T4"])
            font_size = style["font_size"]
            color = style["color"]
            default_align = style.get("align", "left")
            
            # 优先使用 item 中的 align，否则使用样式默认值
            align = align if align else default_align
            font = font_cache.get(font_size, self.font)

            # 计算x位置
            if align == "center":
                text_width = self._get_text_width(text, font)
                x = (max_width - text_width) // 2
            else:
                x = self.padding

            draw.text((x, y), text, font=font, fill=color, encoding="utf-8")
            y += font_size + self.line_spacing

        # 绘制时间标注（右对齐，红色，小字号）
        y += self.line_spacing
        self._draw_timestamp(draw, max_width, y)

        # 简单边框（浅粉色）
        draw.rectangle(
            [(1, 1), (max_width - 2, total_height - 2)],
            outline=self.border_color,
            width=1
        )

        # 保存为字节流
        img_byte_io = io.BytesIO()
        img.save(img_byte_io, format='PNG', quality=90, optimize=True)
        img_byte_io.seek(0)

        return img_byte_io


text_to_image = TextToImageConverter()