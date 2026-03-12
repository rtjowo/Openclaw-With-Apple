# 🍎 OpenClaw with Apple

Apple iCloud 全功能访问 + Apple Health 深度健康分析 + 双向待办/备忘录同步的 AI Skill。

## 功能

| 服务 | 能力 |
|------|------|
| 🍎 iCloud | 照片、iCloud Drive、查找设备、日历 (CalDAV) |
| 🏥 Health | 深度健康分析 — 心率 HRV / 睡眠周期 / 压力评估 / 交叉关联 / 综合评分 |
| 📋 Tasks | AI 对话 → 提醒事项自动推送到 iPhone |
| 📝 Notes | AI 对话 → 备忘录自动推送到 iPhone |

## 快速开始

```bash
git clone https://github.com/rtjowo/openclaw-with-Apple.git
cd openclaw-with-Apple
pip install pyicloud caldav icalendar
```

把项目文件夹作为工作目录加载到支持 Skill 的 AI 助手（CodeBuddy / Cursor 等），AI 会自动读取 `SKILL.md` 并引导你完成配置。

> 📖 **第一次用？** 看 [保姆级安装配置教程](TUTORIAL.md)，从零开始手把手教你。

## 核心功能

### 📋 待办 & 备忘录自动同步

跟 AI 聊天时说到的行动事项和笔记，自动分类推送到 iPhone：

| 你说的话 | AI 做什么 |
|---------|----------|
| "明天去洗车" | → 写入提醒事项 |
| "明天下午2点开会" | → 写入提醒事项 + 日历 |
| "记一下：useEffect 空数组只执行一次" | → 写入备忘录 |

**iPhone 快捷指令**（用 Safari 打开）：

- **Tasks Import**：https://www.icloud.com/shortcuts/9054c0236adb4909b3dbf72fa58b4933
- **Notes Import**：https://www.icloud.com/shortcuts/56d84868591f4233b7d362c83fb71d59

### 数据流

```
你对 AI 说话 → AI 自动写入 JSON
                    │
              21:00 自动推送到 iCloud Drive
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
  Shortcuts/Tasks/      Shortcuts/Notes/
          │                   │
    22:15 iPhone 自动化   22:15 iPhone 自动化
          ▼                   ▼
    提醒事项 App          备忘录 App
```

### 🏥 Apple Health 健康分析

无需密码，iPhone 导入快捷指令即可：

https://www.icloud.com/shortcuts/4a5dff0072a6463a9a1fef47d6ec13e2

分析内容：
- **心率**：夜间静息心率、HRV (RMSSD)、心率突变检测、昼夜差异
- **睡眠**：周期完整性、Deep/REM 分布、碎片化、效率
- **交叉关联**：运动↔睡眠循环、心率↔睡眠联动、作息节律
- **综合评分**：0-100 分 + 可视化进度条

```bash
python scripts/health_tool.py today                          # 今日分析
python scripts/health_tool.py report <dir> --days 7          # 7 天趋势
```

> ⚠️ iPhone「设置」→「快捷指令」→「高级」→ 开启「允许共享大量数据」

### 🍎 iCloud

```bash
# 日历
python scripts/icloud_calendar.py today
python scripts/icloud_calendar.py new 2026-03-15 10:00 11:00 "开会"

# 照片 / Drive / 设备
python scripts/icloud_tool.py photos list 10
python scripts/icloud_tool.py drive list
python scripts/icloud_tool.py devices
python scripts/icloud_tool.py find locate
```

## 时间线

| 时间 | 事件 |
|------|------|
| 全天 | AI 自动识别待办/笔记并写入文件 |
| 21:00 | 服务端推送 JSON 到 iCloud Drive |
| 22:00 | iPhone 采集健康数据 |
| 22:15 | iPhone 导入待办到提醒事项、笔记到备忘录 |
| 22:30 | 服务端分析健康数据，生成报告 |

## 认证

| 凭证 | 用途 | 获取方式 |
|------|------|---------|
| 应用专用密码 | 日历 | [appleid.apple.com](https://appleid.apple.com) → 应用专用密码 |
| Apple ID 邮箱 + 主密码 | 照片/Drive/设备 | 提供给 AI，通过环境变量登录 |
| Apple Health | 不需要 | iPhone 导入快捷指令即可 |

## 文件结构

```
scripts/
├── icloud_auth.py              # iCloud 认证管理
├── icloud_tool.py              # 照片 / Drive / 设备
├── icloud_calendar.py          # 日历 (CalDAV)
├── health_tool.py              # Health 深度分析（1400+ 行）
├── tasks_tool.py               # 待办/备忘录管理 + iCloud 同步
├── setup_tasks_cron.py         # 定时任务安装/卸载
└── generate_tasks_shortcut.py  # 快捷指令生成指南
```

## 文档

- [保姆级安装配置教程](TUTORIAL.md) — 从零开始，适合小白
- [完整 Skill 文档](SKILL.md) — AI 行为规则和功能参考

## License

MIT
