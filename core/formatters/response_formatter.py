# formatters/response_formatter.py
# 响应格式化器：统一处理机器人回复的文本格式（优化价格排序+统一风格）
class ResponseFormatter:
    @staticmethod
    def format_price_response(
            original_query: str,
            english_slug: str,
            sell_orders: list,
            is_translated: bool = False,
            is_arcane: bool = False,
            rank0_orders: list = None,
            max_rank_orders: list = None,
            max_rank: int = 5  # 赋能实际最大等级
    ) -> str:
        """格式化价格查询响应（优化价格排序+统一回复风格）"""
        # 1. 处理赋能物品
        if is_arcane:
            rank0_prices = []
            rank0_sellers = []
            max_rank_prices = []
            max_rank_sellers = []
            # 提取等级0价格和卖家（取前10条排序后，保留前3个最低价）
            if rank0_orders and isinstance(rank0_orders, list):
                # 先按价格排序
                sorted_rank0 = sorted(
                    [order for order in rank0_orders[:10] if isinstance(order, dict) and order.get('platinum') > 0],
                    key=lambda x: x.get('platinum', 0)
                )[:3]
                # 提取价格和卖家昵称
                rank0_prices = [order.get('platinum', 0) for order in sorted_rank0]
                rank0_sellers = [order.get('user', {}).get('ingameName', '未知卖家') for order in sorted_rank0]
            # 提取最大等级价格和卖家（同上）
            if max_rank_orders and isinstance(max_rank_orders, list):
                # 先按价格排序
                sorted_max_rank = sorted(
                    [order for order in max_rank_orders[:10] if isinstance(order, dict) and order.get('platinum') > 0],
                    key=lambda x: x.get('platinum', 0)
                )[:3]
                # 提取价格和卖家昵称
                max_rank_prices = [order.get('platinum', 0) for order in sorted_max_rank]
                max_rank_sellers = [order.get('user', {}).get('ingameName', '未知卖家') for order in sorted_max_rank]
            # 构建回复内容（统一风格）
            response_lines = [
                "🐾 喵~ 主人，赋能价格查到啦！",
                f"📦 物品: {original_query}",
                "📊 赋能等级价格对比:"
            ]
            # 添加等级0价格和卖家
            if rank0_prices:
                for i, (price, seller) in enumerate(zip(rank0_prices, rank0_sellers)):
                    response_lines.append(f"{'🔸' if i % 2 == 0 else '🔹'} 等级0: {price} 白金    卖家：{seller}")
            else:
                response_lines.append("🔸 等级0: 暂无有效价格")
            # 添加实际最大等级价格和卖家
            if max_rank_prices:
                for i, (price, seller) in enumerate(zip(max_rank_prices, max_rank_sellers)):
                    response_lines.append(f"⭐ 等级{max_rank}: {price} 白金    卖家：{seller}")
            else:
                response_lines.append(f"⭐ 等级{max_rank}: 暂无有效价格")
            return "\n".join(response_lines)
        # 2. 处理普通物品（非赋能）
        # 提取前10条，按价格排序后，保留前5个最低价及对应的卖家
        valid_orders = sorted(
            [order for order in sell_orders[:10] if isinstance(order, dict) and order.get('platinum') > 0],
            key=lambda x: x.get('platinum', 0)
        )[:5]
        # 构建普通物品回复（统一风格）
        if not valid_orders:
            return (
                f"🐾 喵~ 找到物品信息啦！\n"
                f"📦 物品: {original_query}\n"
                f"💰 价格统计:\n"
                f"暂无有效价格数据"
            )
        price_lines = []
        for i, order in enumerate(valid_orders):
            price = order.get('platinum', 0)
            seller = order.get('user', {}).get('ingameName', '未知卖家')
            price_lines.append(f"{'🔸' if i % 2 == 0 else '🔹'} {price} 白金    卖家：{seller}")
        return (
                f"🐾 喵~ 找到价格信息啦！\n"
                f"📦 物品: {original_query}\n"
                f"💰 价格统计:\n" +
                "\n".join(price_lines)
        )

    @staticmethod
    def format_error_response(error_msg: str) -> str:
        """格式化错误响应"""
        return (
            f"😿 喵~ 出错了哦！\n"
            f"❌ 错误信息: {error_msg}"
        )

    @staticmethod
    def format_short_help() -> str:
        """格式化简短帮助信息"""
        return (
            "🐱 喵~ 我是Warframe价格查询小助手！\n"
            "💡 使用方法：/wm + 物品名称\n"
            "📌 示例：/wm 近战刃影、/wm 正直狂怒、/wm 悟空prime一套"
        )

    @staticmethod
    def format_full_help() -> str:
        """格式化完整帮助信息"""
        return (
            "🐱 超级小莲使用指南\n"
            "══════════════════════\n"
            "\n"
            "📦 价格查询\n"
            "────────────────\n"
            "• /wm [物品名] - 查WFM市场价\n"
            "• /紫卡 [武器名] - 查紫卡最低价\n"
            "• /紫卡 [武器名] 0洗 - 查0洗紫卡\n"
            "• /市场分析 - PRIME市场趋势\n"
            "\n"
            "🌍 游戏状态\n"
            "────────────────\n"
            "• /全部 - 查看所有实时状态\n"
            "• /平原 - 希图斯/福尔图娜时间\n"
            "• /裂缝 - 所有虚空裂缝\n"
            "• /裂缝 钢铁/普通 - 指定难度\n"
            "• /突击 - 每日突击任务\n"
            "• /警报 - 警报任务\n"
            "• /电波 - 午夜电波挑战\n"
            "• /赏金 - 扎里曼/英择谛赏金\n"
            "• /回廊 - 无尽回廊奖励\n"
            "• /日历 - 1999日历赛季\n"
            "• /商人 - 虚空商人信息\n"
            "\n"
            "🧪 科研任务\n"
            "────────────────\n"
            "• /科研 - 深层+时光科研\n"
            "• /深层科研 - Archimedea任务\n"
            "• /时光科研 - Temporal任务\n"
            "\n"
            "🔔 裂缝订阅 (群聊)\n"
            "────────────────\n"
            "• /订阅裂缝 [难度] [任务] [星球] [等级]\n"
            "• /我的订阅 - 查看订阅列表\n"
            "• /取消订阅 [类型/全部]\n"
            "\n"
            "💬 智能互动\n"
            "────────────────\n"
            "• @机器人 [内容] - 闲聊或查价\n"
            "\n"
            "💡 小贴士：/wm 支持模糊搜索喵~"
        )

    @staticmethod
    def format_empty_query_response() -> str:
        """格式化空查询响应（备用方法）"""
        return (
            "😺 喵~ 你还没告诉我要查什么哦！\n"
            "💡 请输入 /wm + 物品名称，例如：/wm 近战刃影"
        )

    @staticmethod
    def format_game_status_response(status_text: str) -> str:
        """格式化游戏状态响应（保持原有逻辑）"""
        return f"🐾 喵~ 游戏状态查询结果：\n{status_text}"

    @staticmethod
    def format_plain_status_response(plain_text: str) -> str:
        """格式化平原昼夜状态回复（猫娘风格统一）"""
        return (
            "🐾 喵~ 主人，平原昼夜状态查到啦！\n"
            f"{plain_text}\n"
            "✨ 小贴士：切换时间为北京时间，记得合理安排游戏哦~"
        )
