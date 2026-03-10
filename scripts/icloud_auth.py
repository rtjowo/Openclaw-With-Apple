#!/usr/bin/env python3
"""
iCloud 认证管理工具 — 「一次登录，长期免密」

核心原理：
  pyicloud 会将 session token 和 cookies 持久化到 cookie_directory（默认 ~/.pyicloud/）。
  只要 session 未过期，后续所有脚本都可以**无需密码**直接复用已缓存的会话。

使用方式：
  python icloud_auth.py login           # 交互式登录（仅需运行一次）
  python icloud_auth.py status          # 检查当前 session 是否有效
  python icloud_auth.py logout          # 清除已缓存的 session
  python icloud_auth.py refresh         # 刷新 session（延长有效期）

认证流程（面向高管/最终用户）：
  1. 首次使用时运行 `python icloud_auth.py login`
  2. 输入 Apple ID 和密码（密码仅用于本次登录，不会被保存到任何文件）
  3. 在 iPhone/iPad/Mac 上确认双重认证弹窗，输入 6 位验证码
  4. 完成！后续所有操作均自动复用 session，无需再输入密码

安全保证：
  - 密码不落盘、不写入配置文件、不存储为环境变量
  - 仅 session token + cookies 被缓存在 ~/.pyicloud/ 目录（权限 0o700）
  - session 过期后需重新运行 login，但无需泄露密码给任何人

环境变量（可选，替代交互输入）：
  ICLOUD_USERNAME    - Apple ID 邮箱
  ICLOUD_COOKIE_DIR  - 自定义 session 缓存目录（默认 ~/.pyicloud）
"""

import sys
import os
import json
import getpass
import shutil
from pathlib import Path

os.environ['icloud_china'] = '1'

try:
    from pyicloud import PyiCloudService
except ImportError:
    print("请先安装 pyicloud: pip install pyicloud")
    sys.exit(1)

# 默认缓存目录
DEFAULT_COOKIE_DIR = Path.home() / ".pyicloud"


def get_cookie_directory():
    """获取 session 缓存目录"""
    custom = os.environ.get('ICLOUD_COOKIE_DIR')
    if custom:
        return custom
    return str(DEFAULT_COOKIE_DIR)


def get_username():
    """获取 Apple ID（优先环境变量，其次交互输入）"""
    username = os.environ.get('ICLOUD_USERNAME')
    if not username:
        username = input("Apple ID 邮箱: ").strip()
    return username


def get_session_file(username):
    """获取指定用户的 session 文件路径"""
    cookie_dir = get_cookie_directory()
    # pyicloud 用 apple_id 做文件名（替换特殊字符）
    sanitized = username.replace('@', '_at_').replace('.', '_dot_')
    session_file = Path(cookie_dir) / f"{sanitized}.session"
    cookie_file = Path(cookie_dir) / sanitized
    return session_file, cookie_file


def try_restore_session(username, china_mainland=True):
    """
    尝试仅通过 session 缓存恢复连接（不需要密码）。
    返回 (api, error_message)：
      - 成功: (api_instance, None)
      - 失败: (None, "错误描述")
    """
    cookie_dir = get_cookie_directory()
    session_file, cookie_file = get_session_file(username)

    if not session_file.exists() and not cookie_file.exists():
        return None, "未找到缓存的 session，请先运行: python icloud_auth.py login"

    try:
        # pyicloud 初始化时会自动尝试加载 session 并验证
        # 传入密码为空字符串，它会先尝试 session token 验证
        # 如果 session 有效就不需要密码
        api = PyiCloudService(
            username,
            password="",
            cookie_directory=cookie_dir,
            china_mainland=china_mainland
        )

        # 检查是否需要重新认证
        if api.requires_2fa or api.requires_2sa:
            return None, "Session 已过期，需要重新认证。请运行: python icloud_auth.py login"

        return api, None
    except Exception as e:
        error_str = str(e)
        if 'Missing apple_id' in error_str or 'password' in error_str.lower():
            return None, "Session 已过期，请重新登录: python icloud_auth.py login"
        return None, f"恢复 session 失败: {error_str}\n请重新登录: python icloud_auth.py login"


def get_api_with_session(username=None, china_mainland=True):
    """
    供其他脚本调用的统一入口：优先 session 复用，不需要密码。
    如果 session 失效，给出明确提示而非要求输入密码。

    返回 PyiCloudService 实例，失败时 sys.exit(1)。
    """
    if username is None:
        username = os.environ.get('ICLOUD_USERNAME')
        if not username:
            # 尝试从已有 session 文件推断用户名
            username = _guess_username_from_session()
            if not username:
                print("❌ 未指定 Apple ID")
                print("   请设置环境变量 ICLOUD_USERNAME 或先运行: python icloud_auth.py login")
                sys.exit(1)

    api, error = try_restore_session(username, china_mainland)
    if api:
        return api

    print(f"❌ {error}")
    sys.exit(1)


def _guess_username_from_session():
    """从 session 缓存目录中推断用户名"""
    cookie_dir = Path(get_cookie_directory())
    if not cookie_dir.exists():
        return None

    # 找 .session 文件
    session_files = list(cookie_dir.glob("*.session"))
    if len(session_files) == 1:
        # 反向解析用户名
        name = session_files[0].stem
        username = name.replace('_at_', '@').replace('_dot_', '.')
        return username
    return None


def cmd_login():
    """交互式登录 — 密码仅用于本次，不保存"""
    print("🔐 iCloud 认证登录\n")
    print("   密码仅用于本次登录验证，不会保存到任何文件。\n")

    username = get_username()
    password = getpass.getpass("Apple ID 密码（输入不可见）: ")

    if not password:
        print("❌ 密码不能为空")
        return

    cookie_dir = get_cookie_directory()
    china = os.environ.get('ICLOUD_CHINA', '1') == '1'

    print(f'\n🍎 正在连接 iCloud{"(中国大陆)" if china else ""}...')

    try:
        api = PyiCloudService(
            username,
            password,
            cookie_directory=cookie_dir,
            china_mainland=china
        )
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return

    # 处理双重认证
    if api.requires_2fa:
        print("\n🔐 需要双重认证")
        print("   请查看 iPhone/iPad/Mac 上的验证码弹窗")
        code = input("   请输入 6 位验证码: ").strip()
        if not api.validate_2fa_code(code):
            print("❌ 验证失败!")
            return
        print("✅ 验证成功!")

        # 信任此会话
        if not api.is_trusted_session:
            api.trust_session()
            print("✅ 已信任此设备会话")

    elif api.requires_2sa:
        print("\n🔐 需要双重验证")
        devices = api.trusted_devices
        for i, dev in enumerate(devices):
            name = dev.get('deviceName', f'设备 {i+1}')
            print(f"   {i+1}. {name}")
        idx = int(input("   选择接收验证码的设备编号: ")) - 1
        device = devices[idx]
        if not api.send_verification_code(device):
            print("❌ 发送验证码失败")
            return
        code = input("   请输入验证码: ").strip()
        if not api.validate_verification_code(device, code):
            print("❌ 验证失败!")
            return
        print("✅ 验证成功!")

    # 验证 session 可用性
    try:
        _ = list(api.devices)
    except Exception:
        pass  # 不影响，只是触发一次请求让 session 被保存

    print(f"\n✅ 登录成功! Session 已缓存到: {cookie_dir}")
    print(f"   用户: {username}")
    print(f"\n💡 后续使用无需再输入密码，所有脚本将自动复用此 session。")
    print(f"   Session 过期后重新运行 'python icloud_auth.py login' 即可。")

    # 清除内存中的密码引用
    del password


def cmd_status():
    """检查当前 session 状态"""
    print("🔍 检查 iCloud session 状态\n")

    username = os.environ.get('ICLOUD_USERNAME') or _guess_username_from_session()
    if not username:
        print("❌ 未找到任何已缓存的 session")
        print("   请先运行: python icloud_auth.py login")
        return

    cookie_dir = get_cookie_directory()
    session_file, cookie_file = get_session_file(username)

    print(f"   用户: {username}")
    print(f"   缓存目录: {cookie_dir}")
    print(f"   Session 文件: {'✅ 存在' if session_file.exists() else '❌ 不存在'}")
    print(f"   Cookie 文件: {'✅ 存在' if cookie_file.exists() else '❌ 不存在'}")

    if session_file.exists():
        try:
            with open(session_file) as f:
                data = json.load(f)
            has_token = bool(data.get('session_token'))
            print(f"   Session Token: {'✅ 存在' if has_token else '❌ 不存在'}")
        except Exception:
            print(f"   Session 文件: ⚠️ 无法解析")

    # 尝试实际连接验证
    print(f"\n   正在验证 session 有效性...")
    api, error = try_restore_session(username)
    if api:
        print(f"   ✅ Session 有效! 可以正常使用。")
        try:
            devices = list(api.devices)
            print(f"   📱 已关联 {len(devices)} 个设备")
        except Exception:
            print(f"   ⚠️ 设备查询失败（可能需要刷新）")
    else:
        print(f"   ❌ {error}")


def cmd_logout():
    """清除缓存的 session"""
    print("🗑️ 清除 iCloud session\n")

    username = os.environ.get('ICLOUD_USERNAME') or _guess_username_from_session()
    if not username:
        print("   没有找到需要清除的 session")
        return

    session_file, cookie_file = get_session_file(username)

    removed = False
    if session_file.exists():
        session_file.unlink()
        print(f"   ✅ 已删除: {session_file}")
        removed = True
    if cookie_file.exists():
        cookie_file.unlink()
        print(f"   ✅ 已删除: {cookie_file}")
        removed = True

    if removed:
        print(f"\n   Session 已清除。下次使用需重新登录。")
    else:
        print(f"   没有找到需要清除的文件")


def cmd_refresh():
    """刷新 session，延长有效期"""
    print("🔄 刷新 iCloud session\n")

    username = os.environ.get('ICLOUD_USERNAME') or _guess_username_from_session()
    if not username:
        print("❌ 未找到 session，请先登录: python icloud_auth.py login")
        return

    api, error = try_restore_session(username)
    if not api:
        print(f"❌ {error}")
        return

    # 触发一些 API 调用来刷新 session
    try:
        _ = list(api.devices)
        print(f"   ✅ Session 已刷新!")
        print(f"   用户: {username}")
    except Exception as e:
        print(f"   ⚠️ 刷新时出错: {e}")
        print(f"   可能需要重新登录: python icloud_auth.py login")


def show_help():
    print("""
🔐 iCloud 认证管理工具

  「一次登录，长期免密」— 密码不落盘，session 自动缓存。

用法:
  python icloud_auth.py <命令>

命令:
  login     交互式登录（密码仅用一次，不保存）
  status    检查当前 session 是否有效
  refresh   刷新 session 延长有效期
  logout    清除已缓存的 session

环境变量（可选）:
  ICLOUD_USERNAME     Apple ID 邮箱
  ICLOUD_COOKIE_DIR   自定义缓存目录（默认 ~/.pyicloud）
  ICLOUD_CHINA        设为 1 表示中国大陆（默认 1）

安全说明:
  ✅ 密码仅在 login 时交互输入，输入不可见
  ✅ 密码不写入任何文件或环境变量
  ✅ 仅 session token 被缓存（~/.pyicloud/）
  ✅ session 过期后需重新 login
""")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help', 'help'):
        show_help()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'login':
        cmd_login()
    elif cmd == 'status':
        cmd_status()
    elif cmd == 'logout':
        cmd_logout()
    elif cmd == 'refresh':
        cmd_refresh()
    else:
        print(f"❌ 未知命令: {cmd}")
        show_help()


if __name__ == '__main__':
    main()
