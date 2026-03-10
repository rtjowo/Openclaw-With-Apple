# 🍎 Apple iCloud Suite 快速入门

3 分钟内开始使用 iCloud 命令行工具！

## ✅ 实测验证 (2026-02-05)

| 功能 | 状态 |
|------|------|
| 📷 照片 | ✅ 可用 - 浏览、下载 |
| 💾 iCloud Drive | ✅ 可用 - 浏览文件 |
| 📱 查找设备 | ✅ 可用 - 列出设备 |
| 📅 日历 | ✅ 可用 - 读取/创建事件 |

## 第一步：安装

```bash
pip install pyicloud caldav icalendar
```

## 第二步：一次性登录（密码不保存）

```bash
python scripts/icloud_auth.py login
```

运行后会提示：

```
🔐 iCloud 认证登录

   密码仅用于本次登录验证，不会保存到任何文件。

Apple ID 邮箱: your@email.com
Apple ID 密码（输入不可见）: ********

🍎 正在连接 iCloud(中国大陆)...

🔐 需要双重认证
   请查看 iPhone/iPad/Mac 上的验证码弹窗
   请输入 6 位验证码: 123456
✅ 验证成功!
✅ 已信任此设备会话

✅ 登录成功! Session 已缓存到: ~/.pyicloud
💡 后续使用无需再输入密码
```

## 第三步：开始使用（无需密码）

```bash
# 列出相册
python scripts/icloud_tool.py photos albums

# 列出设备
python scripts/icloud_tool.py devices

# iCloud Drive
python scripts/icloud_tool.py drive list
```

## 📅 日历 (需应用专用密码)

```bash
# 设置应用专用密码（在 appleid.apple.com 生成）
export ICLOUD_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"

# 今天的事件
python scripts/icloud_calendar.py today

# 创建事件
python scripts/icloud_calendar.py new 2026-02-10 10:00 11:00 "开会"
```

## 🔧 Session 管理

```bash
# 检查 session 是否有效
python scripts/icloud_auth.py status

# 刷新 session
python scripts/icloud_auth.py refresh

# Session 过期了？重新登录即可
python scripts/icloud_auth.py login
```

## ⚠️ 重要提示

1. **照片/Drive/设备**：通过 session 缓存自动认证，**无需密码环境变量**
2. **日历**：使用 **应用专用密码**（在 appleid.apple.com 生成）
3. **中国大陆**：设置 `ICLOUD_CHINA=1` 环境变量（默认已启用）
4. **Session 过期**：重新运行 `icloud_auth.py login` 即可

## 更多功能

- 状态墙守护进程：`python scripts/status_wall.py --help`
- 批量下载照片：使用 icloudpd

详见 [SKILL.md](./SKILL.md)
