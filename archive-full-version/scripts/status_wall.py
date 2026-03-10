#!/usr/bin/env python3
"""
状态墙守护进程 (免密版)

改造要点：
  - GPS 定位不再需要 ICLOUD_PASSWORD 环境变量
  - 通过 icloud_auth.py 缓存的 session 自动获取 Find My 位置
  - 首次使用需运行: python icloud_auth.py login（仅一次）
  - CalDAV 日历仍使用应用专用密码（ICLOUD_APP_PASSWORD）

逻辑优先级：
  P1 日程读取：查私人日历 → 当前有日程 → 直接展示日程名作为状态
  P2 物理锚点：查 Find My GPS → 高德逆地理编码 → 语义化地点判定

通勤模式（双向自动触发）：
  上班：离开家 >200m → 「🚗 正在上班途中（当前：xx）」→ 到公司 <100m
  下班：离开公司 >200m → 「🚗 正在下班途中，距离家 Xkm（当前：xx）」→ 到家 <100m
  通勤模式下轮询从 15 分钟切换为 1 分钟

命令:
  python status_wall.py init       # 交互式初始化配置
  python status_wall.py start      # 启动后台守护进程
  python status_wall.py stop       # 停止守护进程
  python status_wall.py status     # 查看运行状态
  python status_wall.py once       # 单次执行（调试）
  python status_wall.py show-gps   # 显示当前GPS坐标 + 高德地名

配置文件: ~/.status_wall.json
PID文件:  ~/.status_wall.pid
日志文件: ~/.status_wall.log

环境变量:
  ICLOUD_USERNAME      - Apple ID
  ICLOUD_APP_PASSWORD  - 应用专用密码 (CalDAV 日历读写)
  AMAP_API_KEY         - 高德地图 Web 服务 API Key (逆地理编码)
  注意: 不再需要 ICLOUD_PASSWORD！GPS 通过 session 缓存自动认证。
"""

import os
import sys
import json
import math
import time
import signal
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

os.environ['icloud_china'] = '1'

# 导入认证模块
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

CONFIG_PATH = Path.home() / ".status_wall.json"
PID_PATH = Path.home() / ".status_wall.pid"
LOG_PATH = Path.home() / ".status_wall.log"

DEFAULT_EXCLUDE = ["日天酱共享日历", "家庭共享", "提醒 ⚠️", "大麦", "哔哩哔哩", "携程"]

# 通勤参数
COMMUTE_DEPART_METERS = 200   # 离开锚点触发通勤的距离
COMMUTE_ARRIVE_METERS = 100   # 到达目的地判定距离
COMMUTE_INTERVAL_MINUTES = 1  # 通勤模式轮询间隔（分钟）

# 通勤状态机（进程内存，守护进程生命周期内有效）
_commute_state = None
_last_anchor = None


# ============================================================
# 配置管理
# ============================================================

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def save_config(cfg):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def cmd_init():
    """交互式初始化配置（不再需要主密码）"""
    cfg = load_config()
    print("🔧 状态墙初始化配置\n")
    print("   💡 GPS 定位通过 session 缓存自动认证，无需在此配置密码。\n")

    cfg["member_name"] = input(f"  称呼 [{cfg.get('member_name', '老公')}]: ").strip() or cfg.get("member_name", "老公")
    cfg["target_calendar"] = input(f"  共享日历名 [{cfg.get('target_calendar', '日天酱共享日历')}]: ").strip() or cfg.get("target_calendar", "日天酱共享日历")
    cfg["interval_minutes"] = int(input(f"  正常刷新间隔(分钟) [{cfg.get('interval_minutes', 15)}]: ").strip() or cfg.get("interval_minutes", 15))
    cfg["threshold_meters"] = int(input(f"  地点围栏半径(米) [{cfg.get('threshold_meters', 500)}]: ").strip() or cfg.get("threshold_meters", 500))

    # 高德 API Key
    amap_hint = cfg.get("amap_api_key", "")
    amap_display = (amap_hint[:4] + "****") if amap_hint else "未配置"
    amap_key = input(f"  高德地图 API Key [{amap_display}]: ").strip()
    if amap_key:
        cfg["amap_api_key"] = amap_key

    if "exclude_calendars" not in cfg:
        cfg["exclude_calendars"] = DEFAULT_EXCLUDE

    # 检查 session 状态
    print("\n  🔍 检查 iCloud session...")
    try:
        from icloud_auth import try_restore_session, _guess_username_from_session
        username = os.environ.get('ICLOUD_USERNAME') or _guess_username_from_session()
        if username:
            api, error = try_restore_session(username)
            if api:
                print(f"  ✅ Session 有效 (用户: {username})")
            else:
                print(f"  ⚠️ Session 无效: {error}")
                print(f"  请运行: python icloud_auth.py login")
        else:
            print(f"  ⚠️ 未找到 session，请先运行: python icloud_auth.py login")
    except Exception as e:
        print(f"  ⚠️ 检查失败: {e}")

    # 地点配置
    if "places" not in cfg:
        cfg["places"] = {}

    print(f"\n  当前已配置地点: {list(cfg['places'].keys()) or '无'}")
    print("  提示: 到对应地点后运行 'python status_wall.py show-gps' 获取坐标\n")

    while True:
        name = input("  添加地点名 (如 🏠 在家, 留空结束): ").strip()
        if not name:
            break
        lat = input("    纬度: ").strip()
        lng = input("    经度: ").strip()
        try:
            cfg["places"][name] = [float(lat), float(lng)]
            print(f"    ✅ {name} ({lat}, {lng})")
        except ValueError:
            print("    ❌ 格式错误")

    save_config(cfg)
    print(f"\n✅ 配置已保存到 {CONFIG_PATH}")
    print(f"   运行 'python status_wall.py start' 启动守护进程")


# ============================================================
# 进程管理
# ============================================================

def get_running_pid():
    if not PID_PATH.exists():
        return None
    pid = int(PID_PATH.read_text().strip())
    try:
        os.kill(pid, 0)
        return pid
    except ProcessLookupError:
        PID_PATH.unlink(missing_ok=True)
        return None
    except OSError:
        PID_PATH.unlink(missing_ok=True)
        return None


def cmd_start():
    cfg = load_config()
    if not cfg.get("target_calendar"):
        print("❌ 未配置，请先运行: python status_wall.py init")
        return

    # 检查 session
    try:
        from icloud_auth import try_restore_session, _guess_username_from_session
        username = os.environ.get('ICLOUD_USERNAME') or _guess_username_from_session()
        if username:
            api, error = try_restore_session(username)
            if not api:
                print(f"⚠️ iCloud session 无效: {error}")
                print("   GPS 定位功能将不可用，建议先运行: python icloud_auth.py login")
    except Exception:
        pass

    pid = get_running_pid()
    if pid:
        print(f"⚠️ 守护进程已在运行 (PID: {pid})")
        return

    log_file = open(LOG_PATH, 'a')
    proc = subprocess.Popen(
        [sys.executable, __file__, '_daemon'],
        stdout=log_file,
        stderr=log_file,
        start_new_session=True
    )
    PID_PATH.write_text(str(proc.pid))

    print(f"✅ 守护进程已启动 (PID: {proc.pid})")
    print(f"   正常间隔: {cfg.get('interval_minutes', 15)} 分钟 | 通勤间隔: {COMMUTE_INTERVAL_MINUTES} 分钟")
    print(f"   高德API: {'✅' if cfg.get('amap_api_key') else '❌ 未配置'}")
    print(f"   GPS认证: Session 缓存（无需密码）")
    print(f"   日志: {LOG_PATH}")
    print(f"   停止: python status_wall.py stop")


def cmd_stop():
    pid = get_running_pid()
    if not pid:
        print("ℹ️ 守护进程未运行")
        return
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        print(f"✅ 守护进程已停止 (PID: {pid})")
    except Exception as e:
        print(f"⚠️ 停止失败: {e}")
    PID_PATH.unlink(missing_ok=True)


def cmd_status():
    cfg = load_config()
    pid = get_running_pid()

    print("👤 状态墙守护进程\n")
    print(f"  运行状态: {'✅ 运行中 (PID: ' + str(pid) + ')' if pid else '❌ 未运行'}")
    print(f"  成员: {cfg.get('member_name', '未配置')}")
    print(f"  日历: {cfg.get('target_calendar', '未配置')}")
    print(f"  间隔: {cfg.get('interval_minutes', 15)} 分钟 (通勤: {COMMUTE_INTERVAL_MINUTES} 分钟)")
    print(f"  地点: {list(cfg.get('places', {}).keys()) or '未配置'}")
    print(f"  高德: {'✅ 已配置' if cfg.get('amap_api_key') else '❌ 未配置'}")
    print(f"  GPS认证: Session 缓存（无需密码）")
    print(f"  配置: {CONFIG_PATH}")
    print(f"  日志: {LOG_PATH}")

    # 检查 session
    try:
        from icloud_auth import try_restore_session, _guess_username_from_session
        username = os.environ.get('ICLOUD_USERNAME') or _guess_username_from_session()
        if username:
            api, error = try_restore_session(username)
            if api:
                print(f"  Session: ✅ 有效 ({username})")
            else:
                print(f"  Session: ❌ 过期 — 请运行 python icloud_auth.py login")
        else:
            print(f"  Session: ❌ 未登录 — 请运行 python icloud_auth.py login")
    except Exception:
        print(f"  Session: ⚠️ 无法检查")

    if LOG_PATH.exists():
        lines = LOG_PATH.read_text().strip().split('\n')
        recent = lines[-5:] if len(lines) >= 5 else lines
        if recent:
            print(f"\n  最近日志:")
            for line in recent:
                print(f"    {line}")


# ============================================================
# 日志
# ============================================================

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] {msg}", flush=True)


# ============================================================
# P1 日程读取：查私人日历
# ============================================================

def check_calendar_events(cfg):
    """查私人日历当前时段是否有日程，返回日程名或 None"""
    try:
        import caldav
        from icalendar import Calendar
    except ImportError:
        log("⚠️ 缺少 caldav/icalendar")
        return None

    username = os.environ.get('ICLOUD_USERNAME') or cfg.get('icloud_username')
    app_password = os.environ.get('ICLOUD_APP_PASSWORD') or cfg.get('icloud_app_password')

    if not username or not app_password:
        return None

    try:
        client = caldav.DAVClient(url="https://caldav.icloud.com/", username=username, password=app_password)
        principal = client.principal()
    except Exception as e:
        log(f"⚠️ CalDAV 连接失败: {e}")
        return None

    now = datetime.now()
    exclude = cfg.get("exclude_calendars", DEFAULT_EXCLUDE)

    for cal in principal.calendars():
        cal_name = cal.name or ""
        if cal_name in exclude:
            continue
        try:
            events = cal.search(start=now - timedelta(minutes=1), end=now + timedelta(minutes=1), event=True, expand=True)
            for event in events:
                ical = Calendar.from_ical(event.data)
                for comp in ical.walk():
                    if comp.name != "VEVENT":
                        continue
                    summary = str(comp.get('summary', ''))
                    dtstart = comp.get('dtstart')
                    dtend = comp.get('dtend')
                    if not dtstart:
                        continue
                    start_dt = dtstart.dt
                    if not hasattr(start_dt, 'hour'):
                        continue  # 跳过全天事件
                    end_dt = dtend.dt if dtend else None
                    s = start_dt.replace(tzinfo=None) if start_dt.tzinfo else start_dt
                    e = end_dt.replace(tzinfo=None) if end_dt and end_dt.tzinfo else end_dt
                    if s <= now and (e is None or now <= e):
                        log(f"📅 命中日程: [{cal_name}] {summary}")
                        return summary
        except Exception:
            pass
    return None


# ============================================================
# P2 物理锚点：Find My GPS + 高德逆地理编码
# ============================================================

def haversine(lat1, lon1, lat2, lon2):
    """两点间球面距离（米）"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def get_gps_coords(cfg):
    """
    获取 iPhone GPS 坐标（通过 session 缓存，无需密码）。
    返回 (lat, lng) 或 None。
    """
    try:
        from icloud_auth import get_api_with_session, try_restore_session, _guess_username_from_session
    except ImportError:
        log("⚠️ 找不到 icloud_auth.py")
        return None

    username = os.environ.get('ICLOUD_USERNAME') or _guess_username_from_session()
    if not username:
        log("⚠️ 未找到 iCloud session，GPS 不可用")
        return None

    api, error = try_restore_session(username)
    if not api:
        log(f"⚠️ iCloud session 失效: {error}")
        return None

    try:
        for dev in api.devices:
            info = dev.content
            loc = info.get('location')
            if loc and 'iPhone' in info.get('deviceDisplayName', ''):
                lat, lng = loc.get('latitude'), loc.get('longitude')
                log(f"📡 GPS: ({lat:.4f}, {lng:.4f})")
                return (lat, lng)
    except Exception as e:
        log(f"⚠️ GPS 获取失败: {e}")

    return None


def amap_regeo(lat, lng, cfg):
    """
    高德逆地理编码：GPS 坐标 → 语义化地名
    Find My 中国区返回 GCJ-02，高德 API 也用 GCJ-02，无需转换。
    """
    api_key = os.environ.get('AMAP_API_KEY') or cfg.get('amap_api_key')
    if not api_key:
        return None

    try:
        params = urllib.parse.urlencode({
            'key': api_key,
            'location': f'{lng:.6f},{lat:.6f}',
            'extensions': 'base',
            'output': 'JSON'
        })
        url = f'https://restapi.amap.com/v3/geocode/regeo?{params}'
        req = urllib.request.Request(url, headers={'User-Agent': 'StatusWall/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        if data.get('status') != '1':
            log(f"⚠️ 高德API错误: {data.get('info')}")
            return None

        regeo = data.get('regeocode', {})
        addr_comp = regeo.get('addressComponent', {})

        # 优先 AOI
        aois = regeo.get('aois')
        if isinstance(aois, list) and aois and aois[0].get('name'):
            name = aois[0]['name']
            log(f"📍 高德AOI: {name}")
            return name

        # 街道
        street_info = addr_comp.get('streetNumber', {})
        street_name = street_info.get('street', '') if isinstance(street_info, dict) else ''
        if street_name:
            log(f"📍 高德街道: {street_name}")
            return street_name

        # 乡镇
        township = addr_comp.get('township', '')
        if township:
            log(f"📍 高德区域: {township}")
            return township

        # 兜底
        formatted = regeo.get('formatted_address', '')
        if formatted:
            return formatted
    except Exception as e:
        log(f"⚠️ 高德逆地理编码失败: {e}")

    return None


def find_place_key(cfg, keyword):
    for key in cfg.get("places", {}):
        if keyword in key:
            return key
    return None


def format_distance(meters):
    if meters >= 1000:
        return f"{meters/1000:.1f}km"
    return f"{meters:.0f}m"


def get_gps_status(cfg, coords):
    """根据 GPS 坐标判定状态 + 双向通勤逻辑 + 高德逆地理编码"""
    global _commute_state, _last_anchor

    if coords is None:
        return (None, False)

    lat, lng = coords
    places = cfg.get("places", {})
    threshold = cfg.get("threshold_meters", 500)

    if not places:
        return ("📍 未配置地点", False)

    work_key = find_place_key(cfg, "搬砖") or find_place_key(cfg, "公司")
    home_key = find_place_key(cfg, "在家") or find_place_key(cfg, "家")

    distances = {}
    for place_key, place_coords in places.items():
        distances[place_key] = haversine(lat, lng, place_coords[0], place_coords[1])

    dist_to_work = distances.get(work_key, float('inf')) if work_key else float('inf')
    dist_to_home = distances.get(home_key, float('inf')) if home_key else float('inf')

    # 到达判定
    if work_key and dist_to_work <= COMMUTE_ARRIVE_METERS:
        if _commute_state == "to_work":
            log(f"🏢 到公司了！({dist_to_work:.0f}m)")
        _commute_state = None
        _last_anchor = "work"
        return (work_key, False)

    if home_key and dist_to_home <= COMMUTE_ARRIVE_METERS:
        if _commute_state == "to_home":
            log(f"🏠 到家了！({dist_to_home:.0f}m)")
        _commute_state = None
        _last_anchor = "home"
        return (home_key, False)

    # 在围栏内
    if work_key and dist_to_work <= threshold and _commute_state is None:
        _last_anchor = "work"
        return (work_key, False)

    if home_key and dist_to_home <= threshold and _commute_state is None:
        _last_anchor = "home"
        return (home_key, False)

    # 通勤触发
    if _last_anchor == "home" and _commute_state is None:
        if home_key and dist_to_home > COMMUTE_DEPART_METERS:
            _commute_state = "to_work"
            log(f"🚗 离开家，通勤模式：上班途中 (距家 {dist_to_home:.0f}m)")

    if _last_anchor == "work" and _commute_state is None:
        if work_key and dist_to_work > COMMUTE_DEPART_METERS:
            _commute_state = "to_home"
            log(f"🚗 离开公司，通勤模式：下班途中 (距公司 {dist_to_work:.0f}m)")

    # 通勤中
    location_name = amap_regeo(lat, lng, cfg)
    current_loc = f"（当前：{location_name}）" if location_name else ""

    if _commute_state == "to_work":
        log(f"🚗 上班途中 距公司 {format_distance(dist_to_work)} {current_loc}")
        return (f"🚗 正在上班途中{current_loc}", True)

    if _commute_state == "to_home":
        dist_str = format_distance(dist_to_home) if home_key else ""
        log(f"🚗 下班途中 距家 {dist_str} {current_loc}")
        if home_key and dist_to_home != float('inf'):
            return (f"🚗 正在下班途中，距离家 {dist_str}{current_loc}", True)
        return (f"🚗 正在下班途中{current_loc}", True)

    # 其他已知地点
    for place_key, dist in distances.items():
        if place_key in (work_key, home_key):
            continue
        if dist <= threshold:
            return (place_key, False)

    if location_name:
        return (f"📍 在{location_name}", False)

    return ("🚗 在路上", False)


def cmd_show_gps(cfg):
    """显示当前GPS坐标 + 高德逆地理编码结果（通过 session，无需密码）"""
    try:
        from icloud_auth import try_restore_session, _guess_username_from_session
    except ImportError:
        print("❌ 找不到 icloud_auth.py")
        return

    username = os.environ.get('ICLOUD_USERNAME') or _guess_username_from_session()
    if not username:
        print("❌ 未找到 session，请先运行: python icloud_auth.py login")
        return

    api, error = try_restore_session(username)
    if not api:
        print(f"❌ {error}")
        return

    for dev in api.devices:
        info = dev.content
        loc = info.get('location')
        if loc and 'iPhone' in info.get('deviceDisplayName', ''):
            lat, lng = loc.get('latitude'), loc.get('longitude')
            print(f"📱 {info.get('name', '?')}")
            print(f"📍 坐标: [{lat:.6f}, {lng:.6f}]")

            location_name = amap_regeo(lat, lng, cfg)
            if location_name:
                print(f"🗺️  高德地名: {location_name}")
            else:
                print(f"🗺️  高德地名: 未获取（需配置 AMAP_API_KEY）")

            print(f"\n在 init 配置地点时填入此坐标即可")
            return

    print("❌ 未找到有位置的 iPhone")


# ============================================================
# 写入共享日历
# ============================================================

def update_calendar_status(cfg, status_text):
    """更新共享日历状态卡片"""
    cal_script = os.path.join(SCRIPTS_DIR, 'icloud_calendar.py')
    target = cfg["target_calendar"]
    member = cfg["member_name"]
    title = f"👤 {member}: {status_text}"

    r = subprocess.run(
        ['python3', cal_script, 'search', f'👤 {member}', '-c', target],
        capture_output=True, text=True
    )

    if f'📌 {title}' in r.stdout:
        log(f"状态未变: {status_text}")
        return

    if '找到 0 个' not in r.stdout and '没有找到' not in r.stdout:
        subprocess.run(
            ['python3', cal_script, 'delete', f'👤 {member}', '-c', target],
            capture_output=True, text=True
        )

    r = subprocess.run(
        ['python3', cal_script, 'new', 'today', title, '-c', target],
        capture_output=True, text=True
    )

    if '✅ 事件已创建' in r.stdout:
        log(f"✅ {title}")
    else:
        log(f"❌ 写入失败")


# ============================================================
# 单次执行 / 守护循环
# ============================================================

def run_once(cfg):
    """执行一次状态判定+更新，返回 is_commuting"""
    log("🔄 刷新状态...")

    # P1: 日程读取
    event = check_calendar_events(cfg)
    if event:
        status = f"🚫 {event} (勿扰)"
        update_calendar_status(cfg, status)
        return False

    # P2: 物理锚点
    coords = get_gps_coords(cfg)
    status, is_commuting = get_gps_status(cfg, coords)
    status = status or "📅 空闲"
    update_calendar_status(cfg, status)
    return is_commuting


def run_daemon(cfg):
    """守护进程主循环"""
    normal_interval = cfg.get("interval_minutes", 15)
    log("=" * 50)
    log(f"👤 状态墙启动: {cfg['member_name']} → {cfg['target_calendar']}")
    log(f"   正常间隔={normal_interval}分钟 通勤间隔={COMMUTE_INTERVAL_MINUTES}分钟")
    log(f"   地点={list(cfg.get('places', {}).keys())}")
    log(f"   高德API={'✅' if cfg.get('amap_api_key') else '❌'}")
    log(f"   GPS认证=Session缓存（无需密码）")
    log(f"   通勤触发={COMMUTE_DEPART_METERS}m 到达判定={COMMUTE_ARRIVE_METERS}m")
    log("=" * 50)

    def handle_term(sig, frame):
        log("收到停止信号，退出")
        PID_PATH.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_term)
    signal.signal(signal.SIGINT, handle_term)

    while True:
        try:
            is_commuting = run_once(cfg)
        except Exception as e:
            log(f"❌ 异常: {e}")
            is_commuting = False

        interval = COMMUTE_INTERVAL_MINUTES if is_commuting else normal_interval
        next_run = datetime.now() + timedelta(minutes=interval)
        mode = "🚗 通勤模式" if is_commuting else "💤 正常模式"
        log(f"{mode} 下次: {next_run.strftime('%H:%M:%S')} ({interval}分钟后)")
        time.sleep(interval * 60)


# ============================================================
# 入口
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("""
👤 状态墙守护进程 (免密版)

用法: python status_wall.py <命令>

命令:
  init       交互式初始化配置（首次使用）
  start      启动后台守护进程
  stop       停止守护进程
  status     查看运行状态和最近日志
  once       单次执行（调试用）
  show-gps   显示当前GPS坐标 + 高德地名

首次使用:
  1. python icloud_auth.py login        # 一次性登录（密码不保存）
  2. python status_wall.py init         # 配置状态墙参数
  3. python status_wall.py show-gps     # 在家/公司分别获取坐标
  4. python status_wall.py start        # 启动守护进程

注意: 不再需要配置 ICLOUD_PASSWORD 环境变量！
""")
        return

    cmd = sys.argv[1]
    cfg = load_config()

    if cmd == 'init':
        cmd_init()
    elif cmd == 'start':
        cmd_start()
    elif cmd == 'stop':
        cmd_stop()
    elif cmd == 'status':
        cmd_status()
    elif cmd == 'once':
        if not cfg.get("target_calendar"):
            print("❌ 未配置，请先运行: python status_wall.py init")
            return
        run_once(cfg)
    elif cmd == 'show-gps':
        cmd_show_gps(cfg)
    elif cmd == '_daemon':
        run_daemon(cfg)
    else:
        print(f"❌ 未知命令: {cmd}")


if __name__ == '__main__':
    main()
