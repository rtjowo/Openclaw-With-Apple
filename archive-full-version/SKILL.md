---
name: Apple iCloud Suite
description: 完整访问 Apple iCloud 服务：日历、照片、iCloud Drive、设备查找等
icon: 🍎
os: linux, macos
tools: pyicloud, caldav, icloudpd
install: |
  # Python iCloud API (照片、iCloud Drive、设备等)
  pip install pyicloud
  # CalDAV 工具 (日历)
  pip install caldav icalendar
  # iCloud 照片批量下载 (可选)
  pip install icloudpd
---

# Apple iCloud Suite

这个 Skill 提供对 Apple iCloud 主要服务的命令行访问能力。

## ✅ 实测验证结果 (2026-02-05)

| 服务 | 状态 | 工具 | 说明 |
|------|------|------|------|
| 📷 **照片** | ✅ 完全可用 | pyicloud / icloudpd | 浏览相册、下载照片 |
| 💾 **iCloud Drive** | ✅ 完全可用 | pyicloud | 浏览和下载文件 |
| 📱 **查找设备** | ✅ 完全可用 | pyicloud | 查看所有设备位置和状态 |
| 📅 **日历** | ✅ 完全可用 | CalDAV (caldav库) | 读取/创建事件 (需应用专用密码) |
| 📝 **备忘录** | ⚠️ 有限支持 | - | Apple Notes 无公开 API |

---

## 🔐 认证方式说明

### 🆕 免密模式（推荐 — 密码不落盘）

**改造核心**：用户仅需在自己设备上**运行一次** `icloud_auth.py login`，输入密码完成认证后，密码**不保存到任何文件**。后续所有操作通过缓存的 session token 自动认证。

```
首次使用（仅一次）:
  python icloud_auth.py login      # 交互输入密码 + 2FA 验证码
                                    # 密码仅用于本次认证，不保存

后续使用（无需密码）:
  python icloud_tool.py devices     # 自动使用缓存的 session
  python status_wall.py start       # 自动使用缓存的 session

Session 管理:
  python icloud_auth.py status      # 检查 session 是否有效
  python icloud_auth.py refresh     # 刷新 session 延长有效期
  python icloud_auth.py logout      # 清除 session
```

### 安全保证

| 项目 | 说明 |
|------|------|
| 密码存储 | ❌ 不存储。密码仅在 login 时交互输入（不可见），用完即丢 |
| 环境变量 | ❌ 不需要 `ICLOUD_PASSWORD` 环境变量 |
| 配置文件 | ❌ 密码不写入任何配置文件 |
| Session 缓存 | ✅ 仅 session token + cookies 缓存在 `~/.pyicloud/`（权限 0o700） |
| 过期处理 | Session 过期后需重新运行 `icloud_auth.py login` |

### 凭证说明

| 凭证 | 用途 | 如何提供 | 是否保存 |
|------|------|---------|---------|
| Apple ID 主密码 | 照片/Drive/设备/GPS 定位 | 运行 `icloud_auth.py login` 时交互输入 | ❌ 不保存 |
| 应用专用密码 | CalDAV 日历读写 | 环境变量 `ICLOUD_APP_PASSWORD` | 仅存环境变量 |
| 高德 API Key | 逆地理编码 | `status_wall.py init` 配置 | 存配置文件 |

### ⚠️ 重要发现

**pyicloud API** 需要使用 **主密码 + 双重认证码**，不支持应用专用密码！
**CalDAV (日历)** 可以使用 **应用专用密码**。

### 认证流程

```python
# 方式一：免密模式（推荐）
# 先在终端运行一次: python icloud_auth.py login
# 然后在代码中直接使用:
from icloud_auth import get_api_with_session
api = get_api_with_session()  # 无需密码，自动从 session 恢复

# 方式二：传统模式（兼容）
from pyicloud import PyiCloudService
import os
os.environ['icloud_china'] = '1'
api = PyiCloudService('your@email.com', '主密码', china_mainland=True)
if api.requires_2fa:
    code = input("请输入 iPhone 上收到的验证码: ")
    api.validate_2fa_code(code)
```

---

## 📷 Part 1: 照片 (pyicloud) ✅ 已验证

### 列出相册

```python
#!/usr/bin/env python3
from icloud_auth import get_api_with_session
api = get_api_with_session()  # 无需密码

photos = api.photos
print(f'相册数量: {len(photos.albums)}')
for album_name in photos.albums:
    print(f'📁 {album_name}')
```

### 列出照片

```python
library = api.photos.albums['Library']
for i, photo in enumerate(library.photos):
    if i >= 10: break
    print(f'📷 {photo.filename} | {photo.created}')
```

### 下载照片

```python
photo = next(iter(library.photos))
download = photo.download()
with open(photo.filename, 'wb') as f:
    f.write(download.raw.read())
```

### 使用 icloudpd 批量下载

```bash
# 下载所有照片 (中国大陆)
icloudpd --directory ~/Pictures/iCloud \
  --username your@email.com \
  --domain cn

# 下载最近 100 张
icloudpd -d ~/Pictures/iCloud -u your@email.com --recent 100
```

---

## 💾 Part 2: iCloud Drive ✅ 已验证

```python
from icloud_auth import get_api_with_session
api = get_api_with_session()  # 无需密码

drive = api.drive
for item in drive.dir():
    print(f'📂 {item}')
```

---

## 📱 Part 3: 查找设备 ✅ 已验证

```python
from icloud_auth import get_api_with_session
api = get_api_with_session()  # 无需密码

for device in api.devices:
    print(f'📱 {device}')
```

---

## 📅 Part 4: 日历 (CalDAV) ✅ 已验证

日历功能使用 CalDAV 协议直接访问 iCloud 日历，**需要应用专用密码**。

### 使用 icloud_calendar.py

```bash
# 设置环境变量
export ICLOUD_USERNAME="your@email.com"
export ICLOUD_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"  # 应用专用密码！

# 列出日历
python icloud_calendar.py list

# 查看今天事件
python icloud_calendar.py today

# 创建事件
python icloud_calendar.py new 2026-02-10 10:00 11:00 "开会"
```

### ⚠️ 重要：日历需要应用专用密码

日历功能使用 CalDAV 协议，需要**应用专用密码**（不是主密码）：

1. 登录 https://appleid.apple.com
2. 进入「登录与安全」→「应用专用密码」
3. 点击「+」生成新密码
4. 复制密码（格式: `xxxx-xxxx-xxxx-xxxx`）

---

## 🏠 Part 5: 家庭共享日历场景 (Skill Prompts)

> **核心思路**：在 iCloud 中新建一个 **共享日历**（如"家庭看板"），所有场景统一往这个日历里写事件。
> 家庭成员订阅后，iPhone 日历 App 自动同步，实现零成本的家庭信息中枢。

### 前置约定

| 项目 | 值 |
|------|-----|
| 共享日历名 | 用户指定（如 `家庭看板`），通过参数 `--calendar` 传入 |
| 工具 | `icloud_calendar.py` 的 CalDAV 能力 |
| 排序技巧 | 全天事件按标题字母序排列，可用特殊前缀控制顺序（如 `!` < `A`） |
| 去重逻辑 | 创建前先 `search` 同名事件，存在则跳过或更新，避免重复 |
| 完成标记 | 删除事件 **或** 将标题改为 `✅ 原标题` |

---

### 场景一：家庭琐事公告栏 📋

> 把日历当「冰箱上的便签纸」——每条琐事 = 一个全天事件

**触发方式**：用户说出待办琐事（如"帮我记一下要取快递"、"提醒交电费"）

**Prompt 模板**：

```
你是家庭助手。用户提到一件家庭琐事时，请执行：

1. 确定任务内容，为其选择合适的 emoji 前缀：
   📦 快递/取件  👕 洗衣/收衣  ⚡️ 缴费  🛒 购物/采购
   🧹 打扫/清洁  🍳 做饭/食材  🐾 宠物  📮 其他

2. 先调用 search 检查今天的共享日历中是否已有同名事件（去重）
   python icloud_calendar.py search " <任务>" --calendar "家庭看板"

3. 若不存在，创建全天事件：
   python icloud_calendar.py new today " <任务>" --calendar "家庭看板"

4. 若用户说"xx已完成/搞定了"，删除对应事件或将标题改为 "✅ <原标题>"

示例输出：
  用户："要取快递" → 创建全天事件「📦 取快递」到 家庭看板
  用户："快递取了" → 标记「📦 取快递」→「✅ 📦 取快递」或直接删除
```

---

### 场景二：回家雷达 🚗

> 通过查找设备获取 GPS → 计算预计到家时间 → 日历事件实时显示 ETA

**触发方式**：用户说"我出发了"/"我要回家了"

**Prompt 模板**：

```
你是回家雷达助手。当用户触发"回家"意图时：

1. 调用 pyicloud 查找设备，获取用户当前 GPS 坐标：
   python icloud_tool.py devices   # 通过 session 缓存自动认证，无需密码

2. 根据 GPS 坐标与家庭地址估算 ETA

3. 在共享日历搜索今天是否已有"🚗 回家中"事件：
   python icloud_calendar.py search "回家" --calendar "家庭看板"

4. 若不存在 → 创建时间段事件
5. 若已存在 → 更新结束时间为最新 ETA
6. 到家后删除或改为「🏠 已到家」
```

---

### 场景三：票务托管 🎫

> 用户发来票务信息（文字/截图 OCR），自动解析并创建精确时间段事件

**Prompt 模板**：

```
你是票务管家。用户提供票务信息时：

1. 解析关键字段：类型、日期+时间、地点/座位/车次

2. 选择 emoji：🎬 电影 🚄 高铁 ✈️ 飞机 🎤 演出 🏨 酒店

3. 创建事件：
   python icloud_calendar.py new 2026-03-20 20:00 22:30 "🎬 [电影] 封神第三部" \
     --calendar "家庭看板" \
     --location "万达影城 3号厅 G排12座" \
     --description "取票码: 1234567"
```

---

### 场景四：状态墙 👤

> 日历全天事件当作"家人状态展示牌"，结合日历日程 + GPS 定位 + 高德逆地理编码自动更新。
> **Skill 启用后自动在后台运行**，每 15 分钟刷新一次，用户无需手动触发。

**工具脚本**：`status_wall.py` — 后台守护进程，自动轮询刷新状态

**Prompt 模板**：

```
你是家庭状态墙助手。Skill 启用时需完成以下流程：

═══ 首次使用（凭证收集 — 免密模式）═══

启用 Skill 时，引导用户完成认证（密码不保存）：

1. 运行一次性登录（密码交互输入，输入不可见，不保存到任何文件）：
   python icloud_auth.py login

2. 设置应用专用密码（CalDAV 日历读写用）：
   export ICLOUD_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"

3. 交互式配置状态墙参数：
   python status_wall.py init

   配置项：称呼、共享日历名、刷新间隔、围栏半径、高德API Key。

4. 地点坐标获取——让用户分别在家和公司时运行：
   python status_wall.py show-gps
   （自动使用缓存 session，无需再次输入密码）

═══ 启动守护进程 ═══

   python status_wall.py start      # 后台启动（无需密码）
   python status_wall.py stop       # 停止
   python status_wall.py status     # 查看状态（含 session 有效性检查）
   python status_wall.py once       # 单次执行（调试）

═══ Session 过期处理 ═══

   如果 session 过期，status 命令会提示。用户只需重新运行：
   python icloud_auth.py login
   然后重启守护进程即可，整个过程无需将密码告诉任何人。

═══ P1 日程读取（第一优先级）═══

系统首先读取用户的私人日历（非共享日历）。
如果当前时间点存在日程（如"产品评审会"），直接提取日程名作为状态。
→ 展示：「🚫 产品评审会 (勿扰)」

═══ P2 物理锚点（第二优先级）═══

如果私人日历为空，触发位置判定逻辑：
1. 通过 Find My 获取 GPS（自动使用缓存 session）
2. 调用高德地图 API 逆地理编码
3. 根据地理围栏匹配：
   - 🏢 搬砖中
   - 🏠 在家
   - 📍 在xx（高德 AOI 地名）
   - 🚗 在路上

═══ 双向通勤模式（自动触发）═══

上班：离家 >200m → 1分钟高频轮询 →「🚗 正在上班途中（当前：xx）」→ 到公司 <100m
下班：离公司 >200m → 1分钟高频轮询 →「🚗 正在下班途中，距离家 Xkm（当前：xx）」→ 到家 <100m

状态变化示例（自动发生，无需用户操作）：
08:10 →「👤 老公: 🏠 在家」
08:20 →「👤 老公: 🚗 正在上班途中（当前：上地东路）」
08:35 →「👤 老公: 🏢 搬砖中」
10:30 →「👤 老公: 🚫 产品评审 (勿扰)」
18:30 →「👤 老公: 🚗 正在下班途中，距离家 5.2km（当前：中关村软件园）」
18:45 →「👤 老公: 🏠 在家」
```

---

### ⚠️ 场景实现注意事项

1. **共享日历**：需用户先在 iPhone「日历」App 中创建共享日历并分享给家人
2. **`--calendar` 参数**：`icloud_calendar.py` 已支持 `-c` 指定目标日历
3. **GPS 定位**：通过 session 缓存自动认证，session 过期需重新运行 `icloud_auth.py login`
4. **地点坐标**：必须用 `show-gps` 实地获取的坐标（GCJ-02），不要用网上查的 WGS-84 坐标
5. **高德 API Key**：需用户在 [高德开放平台](https://lbs.amap.com/) 注册并创建 Web 服务类型的 Key
6. **凭证收集**：启用 Skill 时需收集应用专用密码和高德 API Key；**主密码仅在用户自己设备上一次性输入，不传递给任何人**
7. **OCR 解析**：票务截图可配合 Agent 的视觉能力直接提取信息

---

## 🔧 完整 Python 脚本

### icloud_auth.py（认证管理 — 核心模块）

```python
# 独立认证脚本，实现「一次登录，长期免密」
# 完整代码见 scripts/icloud_auth.py

# 供其他脚本调用的 API:
from icloud_auth import get_api_with_session
api = get_api_with_session()  # 无需密码，自动从 session 恢复
```

### icloud_tool.py（免密版）

```bash
# 无需设置 ICLOUD_PASSWORD！
python icloud_tool.py photos albums
python icloud_tool.py photos list 20
python icloud_tool.py drive list
python icloud_tool.py devices
```

### icloud_calendar.py

```bash
# 日历仍需应用专用密码
export ICLOUD_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"
python icloud_calendar.py today
python icloud_calendar.py new today "📦 取快递" --calendar "家庭看板"
```

### status_wall.py（免密版）

```bash
# 无需设置 ICLOUD_PASSWORD！
python icloud_auth.py login          # 一次性登录
python status_wall.py init           # 配置参数
python status_wall.py start          # 启动（自动使用 session）
```

---

## 📋 快速参考

### pyicloud (免密 — 通过 session 缓存)

| 功能 | 代码 |
|------|------|
| 首次登录 | `python icloud_auth.py login` |
| 连接 | `api = get_api_with_session()` |
| 照片相册 | `api.photos.albums` |
| 照片列表 | `api.photos.albums['Library'].photos` |
| 下载照片 | `photo.download().raw.read()` |
| iCloud Drive | `api.drive.dir()` |
| 设备列表 | `api.devices` |

### CalDAV (使用应用专用密码)

| 功能 | 命令 |
|------|------|
| 日历列表 | `python icloud_calendar.py list` |
| 今天事件 | `python icloud_calendar.py today` |
| 创建事件 | `python icloud_calendar.py new DATE TIME "标题"` |

---

## ⚠️ 注意事项

1. **免密模式**：主密码仅在 `icloud_auth.py login` 时交互输入一次，不保存到任何文件
2. **CalDAV 使用应用专用密码**：在 appleid.apple.com 生成
3. **中国大陆用户**：
   - pyicloud: `china_mainland=True` 或 `os.environ['icloud_china'] = '1'`
   - icloudpd: `--domain cn`
4. **会话缓存**：session 保存在 `~/.pyicloud/`，过期后重新 login 即可
5. **备忘录限制**：Apple Notes 没有公开 API，建议使用 iCloud.com 网页版

---

## 🔗 相关资源

- [pyicloud GitHub](https://github.com/picklepete/pyicloud)
- [icloudpd GitHub](https://github.com/icloud-photos-downloader/icloud_photos_downloader)
- [vdirsyncer 文档](https://vdirsyncer.pimutils.org/)
- [khal 文档](https://khal.readthedocs.io/)
