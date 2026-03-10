#!/usr/bin/env python3
"""
Apple iCloud 命令行工具 (已验证可用)
用法: python icloud_tool.py [photos|drive|devices] [子命令]

环境变量:
  ICLOUD_USERNAME  - Apple ID
  ICLOUD_PASSWORD  - 主密码 (非应用专用密码)
  ICLOUD_CHINA     - 设为 1 表示中国大陆用户
"""

import sys
import os

# 中国大陆用户设置
if os.environ.get('ICLOUD_CHINA', '1') == '1':
    os.environ['icloud_china'] = '1'

try:
    from pyicloud import PyiCloudService
except ImportError:
    print("请先安装 pyicloud: pip install pyicloud")
    sys.exit(1)


def get_api():
    """连接 iCloud"""
    username = os.environ.get('ICLOUD_USERNAME')
    password = os.environ.get('ICLOUD_PASSWORD')
    
    if not username:
        username = input("Apple ID: ")
    if not password:
        password = input("密码 (主密码，非应用专用密码): ")
    
    china = os.environ.get('icloud_china') == '1'
    print(f'🍎 正在连接 iCloud{"(中国大陆)" if china else ""}...')
    
    api = PyiCloudService(username, password, china_mainland=china)
    
    if api.requires_2fa:
        print("\n🔐 需要双重认证")
        print("请查看 iPhone/iPad/Mac 上的验证码弹窗")
        code = input("请输入 6 位验证码: ")
        
        if not api.validate_2fa_code(code):
            print("❌ 验证失败!")
            sys.exit(1)
        
        print("✅ 验证成功!")
        
        # 信任会话
        if not api.is_trusted_session:
            api.trust_session()
    
    print("✅ 已连接!\n")
    return api


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
                print(f'⬇️ 正在下载: {p.filename}')
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
🍎 Apple iCloud 命令行工具

用法: python icloud_tool.py <命令> [参数]

命令:
  photos                 照片功能
    albums               列出所有相册
    list [N]             列出最近 N 张照片 (默认 10)
    download N           下载第 N 张照片
  
  drive                  iCloud Drive 功能
    list                 列出根目录
    cd <文件夹>          进入并列出文件夹内容
  
  devices                列出所有设备

环境变量:
  ICLOUD_USERNAME        Apple ID 邮箱
  ICLOUD_PASSWORD        主密码 (不是应用专用密码!)
  ICLOUD_CHINA           设为 1 表示中国大陆 (默认为 1)

示例:
  python icloud_tool.py photos albums
  python icloud_tool.py photos list 20
  python icloud_tool.py photos download 1
  python icloud_tool.py drive list
  python icloud_tool.py devices

注意:
  - 需要使用 Apple ID 主密码，不是应用专用密码
  - 首次使用需要输入双重认证验证码
  - 验证成功后会话会被缓存
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
