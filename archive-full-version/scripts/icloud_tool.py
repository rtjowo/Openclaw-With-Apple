#!/usr/bin/env python3
"""
Apple iCloud 命令行工具 (免密版)

改造要点：不再需要密码环境变量，通过 icloud_auth.py 缓存的 session 自动连接。
首次使用请先运行: python icloud_auth.py login

用法: python icloud_tool.py [photos|drive|devices] [子命令]

环境变量:
  ICLOUD_USERNAME  - Apple ID（可选，能从 session 自动推断）
  ICLOUD_CHINA     - 设为 1 表示中国大陆用户（默认 1）
"""

import sys
import os

# 中国大陆用户设置
if os.environ.get('ICLOUD_CHINA', '1') == '1':
    os.environ['icloud_china'] = '1'

# 导入认证模块
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

try:
    from icloud_auth import get_api_with_session
except ImportError:
    print("❌ 找不到 icloud_auth.py，请确保它与本脚本在同一目录")
    sys.exit(1)


def get_api():
    """通过 session 缓存连接 iCloud（无需密码）"""
    china = os.environ.get('icloud_china') == '1'
    return get_api_with_session(china_mainland=china)


def cmd_photos(api, args):
    """照片命令"""
    photos = api.photos

    if not args or args[0] == 'albums':
        print('📷 相册列表:')
        for name in photos.albums:
            print(f'  📁 {name}')
        print(f'\n共 {len(photos.albums)} 个相册')

    elif args[0] == 'list':
        limit = int(args[1]) if len(args) > 1 else 10
        library = photos.albums['Library']
        print(f'📷 最近 {limit} 张照片:\n')
        for i, p in enumerate(library.photos):
            if i >= limit:
                break
            print(f'  {i+1:3}. {p.filename:25} | {p.created}')

    elif args[0] == 'download':
        if len(args) < 2:
            print("用法: photos download <编号>")
            return
        index = int(args[1]) - 1
        library = photos.albums['Library']
        for i, p in enumerate(library.photos):
            if i == index:
                print(f'⬇️  正在下载: {p.filename}')
                dl = p.download()
                with open(p.filename, 'wb') as f:
                    f.write(dl.raw.read())
                size = os.path.getsize(p.filename) / 1024
                print(f'✅ 已保存: {p.filename} ({size:.1f} KB)')
                break
        else:
            print(f'❌ 未找到第 {index+1} 张照片')

    else:
        print(f"未知子命令: {args[0]}")
        print("可用: albums, list [N], download N")


def cmd_drive(api, args):
    """iCloud Drive 命令"""
    drive = api.drive

    if not args or args[0] == 'list':
        print('💾 iCloud Drive:\n')
        items = list(drive.dir())
        for item in items:
            print(f'  📂 {item}')
        print(f'\n共 {len(items)} 个项目')

    elif args[0] == 'cd' and len(args) > 1:
        folder_name = args[1]
        try:
            folder = drive[folder_name]
            print(f'📂 {folder_name}:\n')
            items = list(folder.dir())
            for item in items:
                print(f'  📄 {item}')
            print(f'\n共 {len(items)} 个项目')
        except KeyError:
            print(f'❌ 文件夹不存在: {folder_name}')

    else:
        print(f"未知子命令: {args[0]}")
        print("可用: list, cd <文件夹>")


def cmd_devices(api, args):
    """设备命令"""
    print('📱 我的设备:\n')
    devices = list(api.devices)
    for d in devices:
        print(f'  - {d}')
    print(f'\n共 {len(devices)} 个设备')


def show_help():
    """显示帮助"""
    print("""
🍎 Apple iCloud 命令行工具 (免密版)

用法: python icloud_tool.py <命令> [参数]

命令:
  photos                照片功能
    albums              列出所有相册
    list [N]            列出最近 N 张照片 (默认 10)
    download N          下载第 N 张照片

  drive                 iCloud Drive 功能
    list                列出根目录
    cd <文件夹>         进入并列出文件夹内容

  devices               列出所有设备

首次使用:
  python icloud_auth.py login     # 一次性登录（密码不保存）

环境变量:
  ICLOUD_USERNAME   Apple ID 邮箱（可选，自动从 session 推断）
  ICLOUD_CHINA      设为 1 表示中国大陆 (默认 1)

示例:
  python icloud_tool.py photos albums
  python icloud_tool.py photos list 20
  python icloud_tool.py photos download 1
  python icloud_tool.py drive list
  python icloud_tool.py devices

注意:
  - 无需配置密码环境变量
  - Session 过期后重新运行 icloud_auth.py login 即可
""")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help', 'help'):
        show_help()
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    api = get_api()

    if cmd == 'photos':
        cmd_photos(api, args)
    elif cmd == 'drive':
        cmd_drive(api, args)
    elif cmd == 'devices':
        cmd_devices(api, args)
    else:
        print(f'❌ 未知命令: {cmd}')
        print('运行 python icloud_tool.py --help 查看帮助')


if __name__ == '__main__':
    main()
