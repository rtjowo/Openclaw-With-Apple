# 🍎 Apple iCloud Suite

命令行访问 Apple iCloud 服务，同时提供基于 iCloud 的家庭协作场景。

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

# 设置环境变量
export ICLOUD_USERNAME="your@email.com"
export ICLOUD_PASSWORD="主密码"
export ICLOUD_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"  # 应用专用密码
export AMAP_API_KEY="你的高德API Key"              # 逆地理编码
```

### 基础工具

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
python scripts/icloud_calendar.py new 2026-03-01 10:00 11:00 "开会"
python scripts/icloud_calendar.py search "开会"
```

### 状态墙

```bash
# 首次配置（含高德API Key）
python scripts/status_wall.py init

# 获取当前位置坐标 + 高德地名验证（在家/公司分别运行一次）
python scripts/status_wall.py show-gps

# 启动后台守护进程
python scripts/status_wall.py start

# 查看运行状态
python scripts/status_wall.py status

# 停止
python scripts/status_wall.py stop
```

**状态判定优先级**：
- P1 日程读取：私人日历有日程 → 直接展示日程名
- P2 物理锚点：Find My GPS + 高德逆地理编码 → 语义化地点

**双向通勤模式**：
- 上班：离开家(>200m) → 1分钟轮询 →「🚗 正在上班途中（当前：xx）」→ 到公司(<100m)
- 下班：离开公司(>200m) → 1分钟轮询 →「🚗 正在下班途中，距离家 Xkm（当前：xx）」→ 到家(<100m)

## 中国大陆用户

```bash
export ICLOUD_CHINA=1
```

## 文件结构

```
├── SKILL.md               # 完整文档 (Skill Prompt)
├── scripts/
│   ├── icloud_tool.py     # 主工具 (照片/Drive/设备)
│   ├── icloud_calendar.py # 日历工具 (CalDAV)
│   └── status_wall.py     # 状态墙守护进程
```

## 认证说明

| 凭证 | 用途 | 获取方式 |
|------|------|---------|
| Apple ID 主密码 | 照片/Drive/设备/GPS定位 | Apple ID 登录密码 |
| 应用专用密码 | CalDAV 日历读写 | [appleid.apple.com](https://appleid.apple.com) 生成 |
| 高德 API Key | 逆地理编码（坐标→地名） | [lbs.amap.com](https://lbs.amap.com/) 创建 Web 服务 Key |

- **GPS 坐标**：中国区 Find My 返回 GCJ-02 坐标，高德 API 原生支持，无需转换
- 配置地点时需用 `show-gps` 实地获取坐标

## 文档

- [完整文档](SKILL.md)

## License

MIT
