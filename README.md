# 超级小莲 (SuperLotus) - Warframe 智能助手

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![NoneBot2](https://img.shields.io/badge/Framework-NoneBot2-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**超级小莲** 是一款基于 NoneBot2 开发的 Warframe 游戏智能助手。以可爱的猫娘为设定，为玩家提供高效的价格查询、实时游戏状态监控以及智能提醒服务。

## ✨ 核心功能

### 📦 价格查询
- **市场价格查询**：对接 Warframe Market，支持中英文搜索、套装识别、赋能等级价格对比
- **紫卡查询**：支持紫卡价格筛选及 0 洗紫卡过滤
- **市场分析**：PRIME 物品市场趋势分析报告

### 🌍 实时游戏状态
- **基础状态**：平原昼夜、虚空裂缝、突击任务、警报任务（图片格式）
- **午夜电波**：每周/每日挑战列表及奖励（图片格式，按声望值分色）
- **无尽回廊**：可选战甲和钢铁灵化武器列表
- **赏金任务**：扎里曼/英择谛赏金监控（图片格式）
- **1999 日历**：日历赛季挑战、奖励和升级项查询（图片格式）
- **虚空商人**：商人位置、剩余时间、商品价格（图片格式，按杜卡德金币排序）

### 🧪 科研任务
- **深层科研 (Archimedea)**：任务详情、风险变量、奖励
- **时光科研 (Temporal Archimedea)**：时光回溯科研任务

### 🔔 裂缝订阅通知
- 支持订阅特定难度/类型/星球/等级的裂缝
- 发现匹配目标时自动 @ 提醒
- 每个用户最多订阅 5 个裂缝

## 💬 命令列表

### 价格查询
| 命令 | 说明 |
|------|------|
| `/wm [物品名]` | 查询 WFM 市场价格 |
| `/紫卡 [武器名]` | 查询紫卡最低价 |
| `/紫卡 [武器名] 0洗` | 查询 0 洗紫卡 |
| `/市场分析` | PRIME 市场分析报告 |

### 游戏状态
| 命令 | 说明 |
|------|------|
| `/全部` | 查看所有实时状态 |
| `/平原` | 希图斯/福尔图娜/魔胎之境时间 |
| `/裂缝` | 所有虚空裂缝 |
| `/裂缝 钢铁` | 钢铁裂缝 |
| `/裂缝 普通` | 普通裂缝 |
| `/突击` | 每日突击任务 |
| `/警报` | 警报任务 |
| `/电波` | 午夜电波挑战（图片格式） |
| `/赏金` | 扎里曼/英择谛赏金（图片格式） |
| `/回廊` | 无尽回廊奖励 |
| `/日历` | 1999 日历赛季（图片格式） |
| `/商人` | 虚空商人信息（图片格式） |

### 科研任务
| 命令 | 说明 |
|------|------|
| `/科研` | 深层科研 + 时光科研（图片格式） |
| `/深层科研` | 深层科研任务详情 |
| `/时光科研` | 时光科研任务详情 |

### 裂缝订阅
| 命令 | 说明 |
|------|------|
| `/订阅裂缝 [参数]` | 订阅裂缝通知 |
| `/我的订阅` | 查看订阅列表 |
| `/取消订阅 [类型]` | 取消订阅 |

### 智能互动
| 命令 | 说明 |
|------|------|
| `@机器人 [内容]` | 闲聊或查价 |

## 🚀 快速上手

### 环境要求
- Python 3.11 或更高版本
- Go-CqHttp 或其他支持 OneBot V11 的协议端

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/your-username/superlotus.git
   cd superlotus
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境**
   复制 `.env.example` 为 `.env` 并填写相关配置：
   - `BOT_QQ_NUMBER`: 机器人的 QQ 号
   - `WFM_API_BASE_URL`: Warframe Market API 地址
   - `QWEN_API_KEY`: (可选) 通义千问 API，用于增强对话能力

4. **启动机器人**
   ```bash
   python bot_main.py
   ```

## 🛠️ 项目结构

```
superlotus/
├── core/              # 核心基础设施
│   ├── constants.py       # 统一常量定义（缓存TTL、API URL等）
│   ├── world_state_client.py  # 世界状态获取器（单例模式）
│   ├── cache_manager.py   # 缓存管理
│   ├── api_manager.py     # API 请求封装
│   ├── logger_config.py   # 日志配置（彩色输出）
│   └── formatters/        # 响应格式化器
├── handlers/          # 指令处理器
│   ├── archimedea/        # 深层科研
│   ├── game_status/       # 游戏状态查询
│   ├── interaction/       # 互动命令
│   ├── price/             # 价格查询
│   ├── research/          # 科研任务
│   ├── subscription/      # 订阅管理
│   └── temporal_archimedea/  # 时光科研
├── managers/          # 业务逻辑层
│   ├── base/              # 基础管理器
│   │   └── base_conquest.py   # Conquest 解析基类
│   ├── game_status_manager.py # 游戏状态管理
│   ├── archimedea_manager.py  # 深层科研管理
│   ├── temporal_archimedea_manager.py  # 时光科研管理
│   ├── kahl_manager.py    # Kahl 任务管理
│   ├── fissure_monitor.py # 裂缝监控
│   ├── void_trader_monitor.py  # 虚空商人监控
│   └── zariman_bounty_monitor.py  # 扎里曼赏金监控
├── services/          # 服务层
├── utils/             # 通用工具
│   └── time_utils.py      # 统一时间处理工具
├── data/              # 数据文件
│   ├── translations/      # 翻译文件
│   └── game_data/         # 游戏数据
└── warframe_exports/  # Warframe 导出数据
```

## 🏗️ 架构亮点

### 统一世界状态获取
- `world_state_client` 单例模式，避免重复 API 请求
- 订阅者模式，数据更新自动通知所有监控器
- 5分钟缓存，大幅减少 API 调用频率

### 统一时间处理
- `time_utils.py` 提供统一的时间解析和格式化
- 支持 MongoDB 时间戳解析
- 自动转换为北京时间显示

### Conquest 基类复用
- `BaseConquestManager` 消除深层科研/时光科研/Kahl任务的重复代码
- 统一的挑战解析和翻译流程

### 彩色日志系统
- 启动横幅美观展示
- 第三方库日志抑制，输出更清爽
- 时间/级别彩色区分

## 🤝 贡献指南

欢迎提交 Issue 或 Pull Request 来完善超级小莲。在提交代码前，请确保您的代码符合 PEP 8 规范。

## 📄 开源协议

本项目基于 [MIT](LICENSE) 协议开源。
