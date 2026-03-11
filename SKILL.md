---
name: OpenClaw with Apple
description: Apple iCloud 全功能访问 + Apple Health 深度健康分析
icon: 🍎
os: linux, macos
tools: pyicloud, caldav
install: |
  pip install pyicloud caldav icalendar
---

# OpenClaw with Apple

Apple iCloud 服务访问 + Apple Health 深度健康分析的 AI Skill。

---

## 🎯 Skill 启用引导流程

> **重要**：启用此 Skill 后，请严格按照以下分阶段流程与用户交互。
> 不要一次性索要所有凭证，按阶段逐步引导。

### 阶段一：Apple iCloud（必选）

Skill 启用后，**首先且仅**收集 Apple 相关凭证：

```
你好！我来帮你配置 OpenClaw with Apple。

首先设置 Apple iCloud 服务（照片、文件、设备、日历）。

🔐 需要两个凭证：

1️⃣ Apple ID 主密码 — 用于照片/Drive/设备
   → 请在终端运行: python icloud_auth.py login
   → 密码交互输入，不可见，不保存到任何文件

2️⃣ 应用专用密码 — 用于日历
   → 在 https://appleid.apple.com →「登录与安全」→「应用专用密码」生成
   → 请提供给我，我来设置环境变量
```

用户完成后，设置环境变量并验证：

```bash
export ICLOUD_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"
python icloud_auth.py status      # 验证 session
python icloud_calendar.py list    # 验证日历
```

### 阶段二：询问 Apple Health

Apple iCloud 配置完成后，**主动询问**：

```
✅ Apple iCloud 已配置完成！

你需要启用 Apple Health 健康数据分析吗？

  🏥 Apple Health — 基于 iPhone 数据的深度健康分析
     分析心率、睡眠、步数、活动能量，给出压力评估和健康建议

需要的话我来引导你设置。（回复"需要"或"不需要"）
```

#### 如果用户选了 Apple Health：

```
🏥 配置 Apple Health：

无需任何密码或 token！只需 3 步即可启用每日健康数据分析。

📱 第 1 步：导入快捷指令

用 iPhone 打开以下链接，点击「添加快捷指令」：
https://www.icloud.com/shortcuts/4a5dff0072a6463a9a1fef47d6ec13e2

⚠️ 必须用 iPhone 上的 Safari 打开，不能在电脑上打开。

🔓 第 2 步：开通健康数据权限

添加后，进入「快捷指令」App：
1. 找到刚添加的「Health Daily Export」快捷指令
2. 长按 → 点击「详细信息」（或点击右上角 ··· 编辑按钮）
3. 点击右上角 ··· → 「隐私」，确保「健康」权限已开启
4. 手动运行一次快捷指令，系统会逐一弹出权限请求：
   - 步数 → 允许
   - 心率 → 允许
   - 睡眠 → 允许
   - 活动能量 → 允许
5. 运行成功后会提示保存文件到 iCloud Drive

🔐 第 3 步（重要）：开启共享大量数据

iPhone →「设置」→「快捷指令」→「高级」→ 开启「允许共享大量数据」
（不开启此选项，自动化运行时可能无法导出数据）

⏰ 第 4 步：设置每日自动化

打开「快捷指令」App → 底部「自动化」标签：
1. 点击右上角 +
2. 选择「特定时间」→ 设为每天 23:00
3. 选择运行「Health Daily Export」
4. 关闭「运行前询问」

配置完成后，每天 23:00 会自动导出当天的健康数据到 iCloud Drive。
```

> **AI 在后续对话中的职责：**
> 1. 当用户询问健康相关内容时，自动去 iCloud Drive 读取当天的健康数据文件
> 2. 文件路径：`~/Library/Mobile Documents/com~apple~CloudDocs/Shortcuts/Health/health_YYYY-MM-DD.txt`
> 3. 使用 `python scripts/health_tool.py analyze <file>` 分析数据
> 4. 根据分析结果向用户报告健康状态（步数、活动能量、心率压力、睡眠质量），并给出个性化建议
> 5. 也可以用 `python scripts/health_tool.py report <dir> --days 7` 做多日趋势分析

### 阶段三：确认完成

所有配置完毕后：

```
✅ 配置完成！已启用的服务：

  🍎 Apple iCloud — 照片、Drive、设备、日历
  🏥 Apple Health — 深度健康分析           （如果选了）

直接告诉我你想做什么，比如：
  "帮我查看今天的日历"
  "分析一下我今天的健康数据"
  "我最近睡眠怎么样"
```

---

## 📋 功能参考

### 🍎 Apple iCloud

#### 照片

```bash
python icloud_tool.py photos albums
python icloud_tool.py photos list 20
python icloud_tool.py photos download 1
```

#### iCloud Drive

```bash
python icloud_tool.py drive list
python icloud_tool.py drive cd Downloads
```

#### 查找设备

```bash
python icloud_tool.py devices
```

#### 日历 (CalDAV)

```bash
python icloud_calendar.py list
python icloud_calendar.py today
python icloud_calendar.py week 7
python icloud_calendar.py new 2026-03-15 10:00 11:00 "开会"
python icloud_calendar.py new today "买牛奶" -c "家庭看板"
python icloud_calendar.py search 开会
python icloud_calendar.py delete 开会
```

选项: `--calendar/-c` 指定日历, `--location/-l` 地点, `--description/-d` 描述

#### Session 管理

```bash
python icloud_auth.py login      # 一次性登录（密码不保存）
python icloud_auth.py status     # 检查 session
python icloud_auth.py refresh    # 刷新
python icloud_auth.py logout     # 清除
```

---

### 🏥 Apple Health

#### 导入快捷指令

用 iPhone 打开 iCloud 链接添加快捷指令：
https://www.icloud.com/shortcuts/4a5dff0072a6463a9a1fef47d6ec13e2

快捷指令每天自动采集 4 项健康数据（步数、活动能量、心率详细、睡眠详细），
保存为 TXT/JSON 到 iCloud Drive/Shortcuts/Health/。

#### 分析每日数据

```bash
python health_tool.py today                                  # 分析今日数据
python health_tool.py analyze  health_2026-03-10.txt         # 分析单日文件
python health_tool.py analyze  <dir> [--days 7]              # 分析目录中所有数据
python health_tool.py report   <dir> [--days 7]              # 多日趋势报告
```

默认数据目录: `~/Library/Mobile Documents/com~apple~CloudDocs/Shortcuts/Health/`

#### 数据文件格式

每日文件名: `health_YYYY-MM-DD.txt`（或 `.json`），内容为 JSON：

```json
{
  "date": "2026-03-10",
  "steps": 5444,
  "active_energy_kcal": 169.08,
  "heart_rate": [{"t": "08:32", "v": 72}, ...],
  "sleep": [{"start": "23:30", "end": "00:15", "type": "Core"}, ...]
}
```

#### 分析深度

- **运动与代谢**: 步数评估、每步能耗效率、活动强度判断
- **心率**:
  - 静息心率 / 夜间精确静息心率
  - HRV (RMSSD) 自主神经系统评估
  - 心率突变事件检测（精确到时间点）
  - 昼夜心率差异分析
  - 按时段分布（夜间/上午/下午/晚间）
- **睡眠**:
  - 睡眠周期完整性（Deep→REM 循环计数）
  - Deep/REM/Core 前后半夜分布对比
  - 碎片化指数、睡眠效率
  - 最长连续睡眠段、夜间醒来次数
  - 入睡时间与褪黑素窗口评估
- **交叉关联**:
  - 低运动量 ↔ 低深度睡眠恶性循环检测
  - 高运动量 + 睡眠不足 = 恢复失衡警告
  - 心率偏高 + 低睡眠效率 = 慢性压力信号
  - 晚睡 + 低活动量的昼夜节律紊乱
- **综合评定**: 0-100 分健康评分 + 等级判定

---

## 🔐 凭证汇总

| 服务 | 凭证 | 环境变量 | 获取方式 |
|------|------|---------|---------|
| iCloud 照片/Drive/设备 | 主密码 | (不需要) | `icloud_auth.py login` 交互输入，不保存 |
| iCloud 日历 | 应用专用密码 | `ICLOUD_APP_PASSWORD` | appleid.apple.com 生成 |
| Apple Health | (不需要) | (不需要) | iPhone 打开 [iCloud 链接](https://www.icloud.com/shortcuts/4a5dff0072a6463a9a1fef47d6ec13e2) 导入快捷指令 |

---

## ⚠️ 注意事项

1. **iCloud 中国大陆**：默认已启用 `ICLOUD_CHINA=1`
2. **iCloud Session**：缓存在 `~/.pyicloud/`，过期重新 `login`
3. **Apple Health 零凭证**：无需密码/token，通过 iCloud 链接导入快捷指令，自动导出数据到 iCloud Drive
4. **Apple Health 权限**：首次运行快捷指令需手动逐项授权（步数、心率、睡眠、活动能量）
5. **Apple Health 共享数据**：设置→快捷指令→高级→允许共享大量数据，否则自动化可能无法导出

---

## 📋 文件结构

```
scripts/
├── icloud_auth.py       # iCloud 认证管理
├── icloud_tool.py       # iCloud 照片 / Drive / 设备
├── icloud_calendar.py   # iCloud 日历 (CalDAV)
└── health_tool.py       # Apple Health 深度分析
```
