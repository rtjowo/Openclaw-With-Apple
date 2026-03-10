# 🚀 Personal Productivity Suite

集成 Apple iCloud、Health、Notion、Gmail、Outlook 的 AI Skill，通过对话式交互统一管理个人生产力工具。

## 功能一览

| 服务 | 能力 |
|------|------|
| 🍎 iCloud | 照片、iCloud Drive、查找设备、日历 (CalDAV) |
| 🏥 Health | 深度健康分析 — 心率 HRV / 睡眠周期 / 压力评估 / 交叉关联诊断 |
| 📝 Notion | 搜索、数据库查询/创建、页面读写 |
| 📧 Gmail | 收件箱、搜索、读取、发送 |
| 📧 Outlook | 收件箱、搜索、读取、发送 |

## 快速开始

```bash
pip install pyicloud caldav icalendar

# Apple iCloud（必选）
python scripts/icloud_auth.py login              # 一次性登录（密码不保存）
export ICLOUD_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx" # 日历用

# Notion（可选）
export NOTION_TOKEN="ntn_xxx"

# Gmail（可选）
export GMAIL_USERNAME="your@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"

# Outlook（可选）
export OUTLOOK_USERNAME="your@outlook.com"
export OUTLOOK_PASSWORD="your_password"
```

## Apple Health — 零配置健康分析

无需密码、无需 token，3 步启用：

1. **iPhone 打开链接** → 添加快捷指令：
   https://www.icloud.com/shortcuts/4a5dff0072a6463a9a1fef47d6ec13e2

2. **开通权限** → 手动运行一次快捷指令，逐项允许（步数、心率、睡眠、活动能量）

3. **设置自动化** → 快捷指令 App → 自动化 → 每天 23:00 运行

> ⚠️ iPhone「设置」→「快捷指令」→「高级」→ 开启「允许共享大量数据」

之后每天自动导出健康数据到 iCloud Drive，AI 可直接读取分析。

### 分析示例

```bash
python scripts/health_tool.py today                          # 今日分析
python scripts/health_tool.py analyze health_2026-03-10.txt  # 单日文件
python scripts/health_tool.py report <dir> --days 7          # 7 天趋势
```

### 分析深度

- **心率**：静息/夜间精确心率、HRV (RMSSD) 自主神经评估、心率突变事件定位、昼夜差异分析
- **睡眠**：周期完整性、Deep/REM/Core 前后半夜分布、碎片化指数、睡眠效率
- **压力**：基于 HRV + 白天心率 + 睡眠质量的综合压力判断
- **交叉关联**：运动↔睡眠恶性循环检测、心率↔睡眠联动分析、作息节律评估
- **综合评分**：0-100 分健康评定

## 使用

```bash
# iCloud
python scripts/icloud_tool.py photos albums
python scripts/icloud_tool.py devices
python scripts/icloud_calendar.py today

# Notion
python scripts/notion_tool.py databases
python scripts/notion_tool.py db <database_id>
python scripts/notion_tool.py create <db_id> -t "新任务"

# Gmail
python scripts/gmail_tool.py inbox
python scripts/gmail_tool.py send -t "a@b.com" -s "主题" -b "内容"

# Outlook
python scripts/outlook_tool.py inbox
python scripts/outlook_tool.py send -t "a@b.com" -s "主题" -b "内容"
```

## 文件结构

```
scripts/
├── icloud_auth.py       # iCloud 认证管理
├── icloud_tool.py       # 照片 / Drive / 设备
├── icloud_calendar.py   # 日历 (CalDAV)
├── health_tool.py       # Health 深度分析
├── notion_tool.py       # Notion
├── gmail_tool.py        # Gmail
└── outlook_tool.py      # Outlook
archive-full-version/    # 旧版 iCloud Suite 归档
```

## 文档

- [完整 Skill 文档](SKILL.md)

## License

MIT
