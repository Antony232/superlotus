# config.py - 主配置文件（支持环境变量）
import json
import os
import random
from typing import Dict, Any, List
from pathlib import Path

class Config:
    def __init__(self):
        self.config = self.load_config()
        self.ensure_directories()

    def ensure_directories(self):
        """确保必要的目录存在"""
        cache_dir = Path(self.cache_settings.get('path', './cache'))
        cache_dir.mkdir(exist_ok=True)

    def load_config(self) -> Dict[str, Any]:
        """加载配置（优先读取环境变量）"""
        return {
            'wfm_api': {
                'base_url': os.getenv('WFM_API_BASE_URL', 'https://api.warframe.market/v2'),
                'asset_url': 'https://warframe.market/static/assets',
                'language': 'en',
                'platform': os.getenv('WFM_PLATFORM', 'pc'),
                'crossplay': os.getenv('WFM_CROSSPLAY', 'true').lower() == 'true',
                'rate_limit': int(os.getenv('WFM_RATE_LIMIT', 3))
            },
            'bot': {
                'command_prefix': '/wm',
                'cache_time': 30,
                'max_results': 10,
                'qq_number': os.getenv('BOT_QQ_NUMBER', '2093845106')  # 支持环境变量配置
            },
            'cache': {
                'enabled': True,
                'path': './cache'
            },
            'catgirl_personality': {
                'name': '超级小莲',
                'greetings': [
                    "喵~ 找到价格信息了！",
                    "锵锵~ 价格信息来啦！",
                    "主人，我查到了哦~",
                ],
                'emojis': ["💫", "✨", "🌟", "⭐", "🐱", "🐾", "🌸", "🎀"],
                'suffixes': ["喵~", "啦~", "哦！", "呢~", "呐！"],
                'ending_phrases': [
                    "主人，这四个是最低价哦，赶快去交易吧喵~",
                    "这四个都是最低价呢，希望主人能买到心仪的物品~",
                    "价格都在这里啦，祝主人交易顺利喵~",
                    "喵~ 找到最划算的价格了，快去联系卖家吧！",
                    "这些卖家都在线呢，主人快去找他们交易吧~"
                ],
                'at_responses': [
                    "喵~ 主人叫小莲有什么事吗？",
                    "啊啦~ 主人在叫我吗？小莲在这里呢！",
                    "喵呜~ 小莲听到了！需要帮忙吗？",
                    "主人主人，小莲在哦！是不是想查询价格呀？",
                    "锵锵~ 小莲登场！主人有什么吩咐喵~",
                    "（竖起耳朵）喵？主人在叫小莲吗？",
                    "小莲来啦！主人是不是需要查询Warframe Market的价格呢？",
                    "喵~ 小莲在这里！随时为主人服务哦！",
                    "（摇晃尾巴）主人，小莲已经准备好啦！",
                    "呜喵~ 听到主人的召唤了！有什么可以帮您的吗？",
                    "主人，小莲在这里呢！需要查询价格的话，请使用 /wm 命令哦！",
                    "喵~ 小莲的耳朵可是很灵的！主人有什么需要吗？",
                    "（开心地转圈）主人叫小莲啦！小莲好开心喵~",
                    "主人，小莲已经上线了！需要帮忙查询物品价格吗？",
                    "喵呜~ 小莲听到主人的声音了！请吩咐吧！"
                ],
                'casual_responses': [
                    "喵~ 今天也是充满干劲的一天呢！",
                    "主人，要和小莲一起玩游戏吗？",
                    "小莲最喜欢帮助主人查询价格了！",
                    "喵呜~ 主人对小莲真好！",
                    "今天的Warframe市场也很热闹呢！",
                    "主人，您知道吗？小莲可是价格查询专家哦！",
                    "喵~ 看到主人小莲就好开心！",
                    "主人有什么想查询的物品吗？小莲随时待命！",
                    "小莲会努力帮主人找到最划算的价格的！",
                    "喵~ 主人今天想查询什么物品呢？"
                ]
            },
            'qwen_api': {
                'enabled': os.getenv('QWEN_ENABLED', 'true').lower() == 'true',
                'api_key': os.getenv('QWEN_API_KEY', ''),
                'base_url': 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
                'model': 'qwen-max',
                'timeout': 10,
                'max_retries': 2
            },
            'market_report': {
                'enabled': os.getenv('MARKET_REPORT_ENABLED', 'true').lower() == 'true',
                'auto_push': os.getenv('MARKET_REPORT_AUTO_PUSH', 'true').lower() == 'true',
                'target_group': int(os.getenv('MARKET_REPORT_TARGET_GROUP', '813532268')),
                'schedule_day': int(os.getenv('MARKET_REPORT_SCHEDULE_DAY', '0')),
                'schedule_hour': int(os.getenv('MARKET_REPORT_SCHEDULE_HOUR', '10')),
                'schedule_minute': int(os.getenv('MARKET_REPORT_SCHEDULE_MINUTE', '0')),
                'image_output_dir': './market_images',
                'max_items_per_category': 10
            }
        }

    @property
    def wfm_api(self) -> Dict[str, Any]:
        return self.config.get('wfm_api', {})

    @property
    def bot_settings(self) -> Dict[str, Any]:
        return self.config.get('bot', {})

    @property
    def cache_settings(self) -> Dict[str, Any]:
        return self.config.get('cache', {})

    @property
    def personality(self) -> Dict[str, Any]:
        return self.config.get('catgirl_personality', {})

    @property
    def market_report_settings(self) -> Dict[str, Any]:
        return self.config.get('market_report', {})

    def get_market_report_target_group(self) -> int:
        """获取市场报告推送目标群号"""
        return int(self.market_report_settings.get('target_group', 813532268))

    def is_market_report_enabled(self) -> bool:
        """是否启用市场报告功能"""
        return bool(self.market_report_settings.get('enabled', True))

    def is_auto_push_enabled(self) -> bool:
        """是否启用自动推送"""
        return bool(self.market_report_settings.get('auto_push', True))

    def get_random_greeting(self) -> str:
        greetings = self.personality.get('greetings', [])
        return random.choice(greetings) if greetings else "查询结果"

    def get_random_emoji(self) -> str:
        emojis = self.personality.get('emojis', [])
        return random.choice(emojis) if emojis else "💫"

    def get_random_ending_phrase(self) -> str:
        phrases = self.personality.get('ending_phrases', [])
        return random.choice(phrases) if phrases else ""

    def get_random_at_response(self) -> str:
        """随机获取@回应"""
        responses = self.personality.get('at_responses', [])
        return random.choice(responses) if responses else "喵~ 我在呢！"

    def get_random_casual_response(self) -> str:
        """随机获取闲聊回应"""
        responses = self.personality.get('casual_responses', [])
        return random.choice(responses) if responses else "喵~ 今天天气真好！"

    def get_bot_qq_number(self) -> str:
        """获取机器人QQ号"""
        result: str = self.bot_settings.get('qq_number', '')
        if not result:
            result = os.getenv('BOT_QQ_NUMBER', '2093845106')
        return result

# 全局配置实例
config = Config()