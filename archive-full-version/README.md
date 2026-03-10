# 🍎 Apple iCloud Suite

命令行访问 Apple iCloud 服务，同时提供基于 iCloud 的家庭协作场景。

## 🆕 免密模式

**高管友好** — 密码仅在自己设备上输入一次，不保存、不传递。

```bash
# 一次性登录（密码交互输入，不保存）
python scripts/icloud_auth.py login

# 后续使用无需密码
python scripts/icloud_tool.py devices
python scripts/status_wall.py start
```

## ✅ 实测验证 (2026-02-05)

| 功能 | 状态 | 说明 |
|------|------|------|
| 📷 照片 | ✅ 可用 | 浏览相册、下载照片 |
| 💾 iCloud Drive | ✅ 可用 | 浏览和下载文件 |
| 📱 查找设备 | ✅ 可用 | 列出所有设备位置 |
| 📅 日历 | ✅ 可用 | 读取/创建/删除事件 (CalDAV) |

## 快速开始

```bash
# 安装依赖
pip install pyicloud caldav icalendar

# 一次性登录（密码仅用一次，不保存）
python scripts/icloud_auth.py login

# 设置日历用的应用专用密码
export ICLOUD_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"

# 可选：高德地图 API Key（状态墙用）
export AMAP_API_KEY="你的高德API Key"
```

### 基础工具（无需密码）

```bash
# 照片
python scripts/icloud_tool.py photos albums
python scripts/icloud_tool.py photos list 10

# iCloud Drive
python scripts/icloud_tool.py drive list

# 设备
python scripts/icloud_tool.py devices

# 日历（需应用专用密码）
python scripts/icloud_calendar.py today
python scripts/icloud_calendar.py new 2026-03-01 10:00 11:00 "开会"
```

### 状态墙（无需密码）

```bash
python scripts/icloud_auth.py login        # 一次性登录
python scripts/status_wall.py init          # 配置参数
python scripts/status_wall.py show-gps      # 获取坐标
python scripts/status_wall.py start         # 启动守护进程
python scripts/status_wall.py status        # 查看状态
python scripts/status_wall.py stop          # 停止
```

### Session 管理

```bash
python scripts/icloud_auth.py status        # 检查 session
python scripts/icloud_auth.py refresh       # 刷新 session
python scripts/icloud_auth.py logout        # 清除 session
```

## 认证说明

| 凭证 | 用途 | 如何提供 | 是否保存 |
|------|------|---------|---------|
| Apple ID 主密码 | 照片/Drive/设备/GPS | `icloud_auth.py login` 交互输入 | ❌ 不保存 |
| 应用专用密码 | CalDAV 日历 | 环境变量 `ICLOUD_APP_PASSWORD` | 仅环境变量 |
| 高德 API Key | 逆地理编码 | `status_wall.py init` 配置 | 配置文件 |

## 文件结构

```
├── SKILL.md                   # 完整文档 (Skill Prompt)
├── QUICKSTART.md              # 快速入门
├── scripts/
│   ├── icloud_auth.py         # 🆕 认证管理（一次登录，长期免密）
│   ├── icloud_tool.py         # 主工具 (照片/Drive/设备) — 免密版
│   ├── icloud_calendar.py     # 日历工具 (CalDAV)
│   └── status_wall.py         # 状态墙守护进程 — 免密版
```

## 中国大陆用户

```bash
export ICLOUD_CHINA=1
```

## 文档

- [完整文档](SKILL.md)
- [快速入门](QUICKSTART.md)

## License

MIT
