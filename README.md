# 🍎 OpenClaw with Apple

Apple iCloud 全功能访问 + Apple Health 深度健康分析的 AI Skill。

## 功能

| 服务 | 能力 |
|------|------|
| 🍎 iCloud | 照片、iCloud Drive、查找设备、日历 (CalDAV) |
| 🏥 Health | 深度健康分析 — 心率 HRV / 睡眠周期 / 压力评估 / 交叉关联诊断 |

## 快速开始

```bash
pip install pyicloud caldav icalendar

# Apple iCloud
python scripts/icloud_auth.py login              # 一次性登录（密码不保存）
export ICLOUD_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx" # 日历用
```

## Apple Health — 零配置健康分析

无需密码、无需 token，3 步启用：

1. **iPhone 打开链接** → 添加快捷指令：
   https://www.icloud.com/shortcuts/4a5dff0072a6463a9a1fef47d6ec13e2

2. **开通权限** → 手动运行一次，逐项允许（步数、心率、睡眠、活动能量）

3. **设置自动化** → 快捷指令 App → 自动化 → 每天 23:00 运行

> ⚠️ iPhone「设置」→「快捷指令」→「高级」→ 开启「允许共享大量数据」

### 分析示例

```bash
python scripts/health_tool.py today                          # 今日分析
python scripts/health_tool.py analyze health_2026-03-10.txt  # 单日文件
python scripts/health_tool.py report <dir> --days 7          # 7 天趋势
```

### 分析深度

- **心率**：夜间精确静息心率、HRV (RMSSD) 自主神经评估、心率突变事件定位、昼夜差异分析
- **睡眠**：周期完整性、Deep/REM/Core 前后半夜分布、碎片化指数、睡眠效率
- **压力**：基于 HRV + 白天心率 + 睡眠质量的综合压力判断
- **交叉关联**：运动↔睡眠恶性循环检测、心率↔睡眠联动、作息节律评估
- **综合评分**：0-100 分健康评定

## iCloud 使用

```bash
# 照片
python scripts/icloud_tool.py photos albums
python scripts/icloud_tool.py photos list 10
python scripts/icloud_tool.py photos download 1

# iCloud Drive
python scripts/icloud_tool.py drive list

# 设备
python scripts/icloud_tool.py devices

# 日历
python scripts/icloud_calendar.py today
python scripts/icloud_calendar.py new 2026-03-15 10:00 11:00 "开会"
python scripts/icloud_calendar.py search "开会"
```

## 认证

| 凭证 | 用途 | 获取方式 |
|------|------|---------|
| Apple ID 主密码 | 照片/Drive/设备 | `icloud_auth.py login` 交互输入 |
| 应用专用密码 | CalDAV 日历 | [appleid.apple.com](https://appleid.apple.com) 生成 |
| Apple Health | (不需要) | iPhone 打开 iCloud 链接导入快捷指令 |

## 文件结构

```
scripts/
├── icloud_auth.py       # iCloud 认证管理
├── icloud_tool.py       # 照片 / Drive / 设备
├── icloud_calendar.py   # 日历 (CalDAV)
└── health_tool.py       # Health 深度分析
```

## 文档

- [完整 Skill 文档](SKILL.md)

## License

MIT
