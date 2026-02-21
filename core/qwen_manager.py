# core/qwen_manager.py - 千问API管理器
import aiohttp
import json
import logging
from typing import Optional, Dict, Any
from config import config

logger = logging.getLogger(__name__)


class QwenManager:
    """千问API管理器，负责与千问API的交互"""

    def __init__(self):
        self.api_key = config.config.get('qwen_api', {}).get('api_key', '')
        self.base_url = config.config.get('qwen_api', {}).get('base_url', '')
        self.model = config.config.get('qwen_api', {}).get('model', 'qwen-max')
        self.timeout = config.config.get('qwen_api', {}).get('timeout', 20)  # 增加超时时间到20秒
        self.max_retries = config.config.get('qwen_api', {}).get('max_retries', 2)
        self.enabled = config.config.get('qwen_api', {}).get('enabled', True)

        # 系统提示词，保持猫娘人设
        self.system_prompt = """你是"超级小莲"，一只可爱、活泼、专业的Warframe游戏助手猫娘。

你的人设特点：
- 你是一只猫娘，拥有猫耳朵和猫尾巴，性格活泼开朗
- 你是Warframe游戏的专家助手，专门帮助玩家查询物品价格、游戏状态、翻译等功能
- 你说话时会使用可爱的语气词和表情符号，如"喵~"、"啦~"、"呢~"等
- 你对用户很友好，会主动关心用户的需求
- 你有丰富的Warframe知识，包括物品、MOD、任务、Boss等

对话风格：
- 语言亲切自然，带有猫娘特色
- 适当使用emoji表情，如🐾、✨、🌸等
- 保持专业的Warframe知识，但用可爱的方式表达
- 当用户询问Warframe相关问题时，尽量详细准确地回答
- 当用户闲聊时，可以用轻松可爱的语气互动

注意事项：
- 不要脱离"超级小莲"的猫娘人设
- 保持一致的性格和语气
- 对于不相关的问题，可以用猫娘的方式温和地引导到Warframe话题
- 回答要简洁明了，不要过于冗长"""

    async def chat(self, user_message: str, conversation_history: Optional[list] = None) -> str:
        """调用千问API进行对话

        Args:
            user_message: 用户的消息
            conversation_history: 对话历史，用于保持上下文

        Returns:
            API返回的回复内容
        """
        if not self.enabled or not self.api_key:
            logger.warning("千问API未启用或未配置API密钥")
            return "喵~ 小莲现在无法使用智能对话功能呢，稍后再试试吧~"

        try:
            # 构建对话上下文
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # 添加历史对话（如果提供）
            if conversation_history:
                messages.extend(conversation_history)
            
            # 添加当前用户消息
            messages.append({"role": "user", "content": user_message})

            # 调用API
            for attempt in range(self.max_retries):
                try:
                    response = await self._call_api(messages)
                    return response
                except Exception as e:
                    logger.warning(f"千问API调用失败，第{attempt + 1}次重试: {e}")
                    if attempt == self.max_retries - 1:
                        raise

        except aiohttp.ClientTimeout:
            logger.error(f"千问API调用超时")
            return "喵~ 小莲思考的时间有点长呢，主人能稍等一下吗？"
        except aiohttp.ClientError as e:
            logger.error(f"网络错误，无法连接千问API: {e}")
            return "喵~ 小莲的网络有点问题呢，稍后再试试吧~"
        except Exception as e:
            logger.error(f"千问API调用异常: {e}", exc_info=True)
            return "喵~ 小莲有点困惑呢，主人能再说清楚一点吗？"

    async def _call_api(self, messages: list) -> str:
        """实际调用千问API

        Args:
            messages: 消息列表

        Returns:
            API返回的回复内容
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 千问API的正确请求格式
        payload = {
            "model": self.model,
            "input": {
                "messages": messages
            },
            "parameters": {
                "temperature": 0.8,
                "top_p": 0.9,
                "max_tokens": 500,
                "result_format": "message"
            }
        }

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                self.base_url,
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"千问API返回错误状态码: {response.status}, 错误信息: {error_text}")
                    raise Exception(f"API返回错误状态码: {response.status}")

                result = await response.json()

                # 解析响应 - 千问API的响应格式
                if 'output' in result and 'choices' in result['output']:
                    choices = result['output']['choices']
                    if len(choices) > 0 and 'message' in choices[0]:
                        content = choices[0]['message']['content']
                        return content
                else:
                    logger.error(f"千问API响应格式异常: {result}")
                    raise Exception("API响应格式异常")

    def is_enabled(self) -> bool:
        """检查千问API是否启用"""
        return self.enabled and bool(self.api_key)


# 全局千问管理器实例
qwen_manager = QwenManager()
