#!/usr/bin/env python3
"""
Notion 命令行工具

通过 Notion API 管理页面、数据库和内容。

用法: python notion_tool.py [search|databases|pages|db|page|create|append|update] [参数]

环境变量:
  NOTION_TOKEN  - Notion Internal Integration Token
                  获取方式: https://www.notion.so/my-integrations → 创建集成 → 复制 Token

认证说明:
  1. 访问 https://www.notion.so/my-integrations
  2. 点击「New integration」创建内部集成
  3. 复制 Internal Integration Token（以 ntn_ 或 secret_ 开头）
  4. 在 Notion 中将需要访问的页面/数据库「Connect to」你的集成
"""

import sys
import os
import json
import urllib.request
import urllib.parse
import argparse
from datetime import datetime

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def get_token():
    token = os.environ.get('NOTION_TOKEN')
    if not token:
        print("❌ 未设置 NOTION_TOKEN")
        print("   export NOTION_TOKEN=\"ntn_xxx\"")
        print("")
        print("   获取方式:")
        print("   1. 访问 https://www.notion.so/my-integrations")
        print("   2. 创建 Internal Integration")
        print("   3. 复制 Token")
        print("   4. 在 Notion 页面点击 ··· → Connect to → 选择你的集成")
        sys.exit(1)
    return token


def api_request(method, endpoint, data=None):
    """发送 Notion API 请求"""
    token = get_token()
    url = f"{NOTION_API}/{endpoint}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    body = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            err = json.loads(error_body)
            print(f"❌ API 错误: {err.get('message', error_body)}")
        except Exception:
            print(f"❌ HTTP {e.code}: {error_body}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        sys.exit(1)


# ============================================================
# 富文本解析
# ============================================================

def rich_text_to_str(rich_text_list):
    """将 Notion rich_text 数组转为纯文本"""
    if not rich_text_list:
        return ""
    return "".join(t.get("plain_text", "") for t in rich_text_list)


def str_to_rich_text(text):
    """纯文本转 rich_text 数组"""
    return [{"type": "text", "text": {"content": text}}]


def format_property_value(prop):
    """格式化属性值为可读字符串"""
    ptype = prop.get("type", "")

    if ptype == "title":
        return rich_text_to_str(prop.get("title", []))
    elif ptype == "rich_text":
        return rich_text_to_str(prop.get("rich_text", []))
    elif ptype == "number":
        val = prop.get("number")
        return str(val) if val is not None else ""
    elif ptype == "select":
        sel = prop.get("select")
        return sel.get("name", "") if sel else ""
    elif ptype == "multi_select":
        return ", ".join(s.get("name", "") for s in prop.get("multi_select", []))
    elif ptype == "status":
        st = prop.get("status")
        return st.get("name", "") if st else ""
    elif ptype == "date":
        d = prop.get("date")
        if not d:
            return ""
        start = d.get("start", "")
        end = d.get("end", "")
        return f"{start} → {end}" if end else start
    elif ptype == "checkbox":
        return "✅" if prop.get("checkbox") else "⬜"
    elif ptype == "url":
        return prop.get("url", "")
    elif ptype == "email":
        return prop.get("email", "")
    elif ptype == "phone_number":
        return prop.get("phone_number", "")
    elif ptype == "people":
        return ", ".join(p.get("name", "") for p in prop.get("people", []))
    elif ptype == "relation":
        return f"[{len(prop.get('relation', []))} 个关联]"
    elif ptype == "formula":
        f = prop.get("formula", {})
        ftype = f.get("type", "")
        return str(f.get(ftype, ""))
    elif ptype == "rollup":
        r = prop.get("rollup", {})
        rtype = r.get("type", "")
        return str(r.get(rtype, ""))
    elif ptype == "created_time":
        return prop.get("created_time", "")[:10]
    elif ptype == "last_edited_time":
        return prop.get("last_edited_time", "")[:10]
    elif ptype == "created_by":
        return prop.get("created_by", {}).get("name", "")
    elif ptype == "last_edited_by":
        return prop.get("last_edited_by", {}).get("name", "")
    elif ptype == "files":
        files = prop.get("files", [])
        return ", ".join(f.get("name", "") for f in files)
    else:
        return f"[{ptype}]"


def block_to_text(block, indent=0):
    """将 block 转为文本"""
    btype = block.get("type", "")
    prefix = "  " * indent
    content = ""

    if btype in ("paragraph", "quote", "callout", "toggle"):
        content = rich_text_to_str(block.get(btype, {}).get("rich_text", []))
    elif btype in ("heading_1", "heading_2", "heading_3"):
        level = int(btype[-1])
        text = rich_text_to_str(block.get(btype, {}).get("rich_text", []))
        content = f"{'#' * level} {text}"
    elif btype == "bulleted_list_item":
        text = rich_text_to_str(block.get(btype, {}).get("rich_text", []))
        content = f"• {text}"
    elif btype == "numbered_list_item":
        text = rich_text_to_str(block.get(btype, {}).get("rich_text", []))
        content = f"  {text}"
    elif btype == "to_do":
        todo = block.get(btype, {})
        text = rich_text_to_str(todo.get("rich_text", []))
        check = "✅" if todo.get("checked") else "⬜"
        content = f"{check} {text}"
    elif btype == "code":
        code = block.get(btype, {})
        text = rich_text_to_str(code.get("rich_text", []))
        lang = code.get("language", "")
        content = f"```{lang}\n{text}\n```"
    elif btype == "divider":
        content = "---"
    elif btype == "image":
        img = block.get("image", {})
        url = img.get("file", img.get("external", {})).get("url", "")
        caption = rich_text_to_str(img.get("caption", []))
        content = f"[图片] {caption}" if caption else "[图片]"
    elif btype == "bookmark":
        url = block.get("bookmark", {}).get("url", "")
        content = f"🔗 {url}"
    elif btype == "table_row":
        cells = block.get("table_row", {}).get("cells", [])
        content = " | ".join(rich_text_to_str(cell) for cell in cells)
    else:
        content = f"[{btype}]"

    if content:
        return f"{prefix}{content}"
    return None


# ============================================================
# 命令实现
# ============================================================

def cmd_search(args):
    """搜索页面和数据库"""
    parser = argparse.ArgumentParser(prog='search', add_help=False)
    parser.add_argument('query', nargs='*')
    parser.add_argument('--type', '-t', choices=['page', 'database'], default=None)
    parser.add_argument('--limit', '-n', type=int, default=10)

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print("用法: search <关键词> [--type page|database] [--limit N]")
        return

    query = ' '.join(parsed.query) if parsed.query else ""
    data = {"page_size": parsed.limit}
    if query:
        data["query"] = query
    if parsed.type:
        data["filter"] = {"value": parsed.type, "property": "object"}

    result = api_request("POST", "search", data)
    results = result.get("results", [])

    if not results:
        print("  没有找到结果")
        return

    for item in results:
        obj_type = item.get("object")
        item_id = item.get("id", "")

        if obj_type == "page":
            props = item.get("properties", {})
            title = ""
            for p in props.values():
                if p.get("type") == "title":
                    title = rich_text_to_str(p.get("title", []))
                    break
            title = title or "未命名"
            print(f"  📄 {title}")
            print(f"     ID: {item_id}")

        elif obj_type == "database":
            title = rich_text_to_str(item.get("title", []))
            title = title or "未命名"
            print(f"  🗃️  {title}")
            print(f"     ID: {item_id}")

        url = item.get("url", "")
        if url:
            print(f"     🔗 {url}")
        print()

    print(f"共 {len(results)} 个结果")


def cmd_databases(args):
    """列出所有数据库"""
    data = {
        "filter": {"value": "database", "property": "object"},
        "page_size": 100
    }
    result = api_request("POST", "search", data)
    results = result.get("results", [])

    if not results:
        print("  没有可访问的数据库")
        print("  请确保在 Notion 中将数据库 Connect to 你的集成")
        return

    print("🗃️  数据库列表:\n")
    for db in results:
        title = rich_text_to_str(db.get("title", []))
        title = title or "未命名"
        db_id = db.get("id", "")
        print(f"  📊 {title}")
        print(f"     ID: {db_id}")

        # 显示属性列
        props = db.get("properties", {})
        if props:
            cols = [f"{name}({p['type']})" for name, p in list(props.items())[:6]]
            print(f"     列: {', '.join(cols)}")
        print()

    print(f"共 {len(results)} 个数据库")


def cmd_pages(args):
    """列出最近的页面"""
    parser = argparse.ArgumentParser(prog='pages', add_help=False)
    parser.add_argument('--limit', '-n', type=int, default=10)

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print("用法: pages [--limit N]")
        return

    data = {
        "filter": {"value": "page", "property": "object"},
        "page_size": parsed.limit,
        "sort": {"direction": "descending", "timestamp": "last_edited_time"}
    }
    result = api_request("POST", "search", data)
    results = result.get("results", [])

    if not results:
        print("  没有可访问的页面")
        return

    print("📄 最近页面:\n")
    for page in results:
        props = page.get("properties", {})
        title = ""
        for p in props.values():
            if p.get("type") == "title":
                title = rich_text_to_str(p.get("title", []))
                break
        title = title or "未命名"
        edited = page.get("last_edited_time", "")[:10]
        print(f"  📄 {title}  ({edited})")
        print(f"     ID: {page['id']}")

    print(f"\n共 {len(results)} 个页面")


def cmd_db(args):
    """查询数据库内容"""
    parser = argparse.ArgumentParser(prog='db', add_help=False)
    parser.add_argument('database_id')
    parser.add_argument('--limit', '-n', type=int, default=20)
    parser.add_argument('--filter', '-f', default=None, help='JSON 格式的 filter')
    parser.add_argument('--sort', '-s', default=None, help='排序字段名')
    parser.add_argument('--desc', action='store_true')

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print("用法: db <database_id> [--limit N] [--sort 字段名] [--desc]")
        return

    data = {"page_size": parsed.limit}
    if parsed.filter:
        try:
            data["filter"] = json.loads(parsed.filter)
        except json.JSONDecodeError:
            print("❌ filter 格式错误，需要 JSON")
            return
    if parsed.sort:
        data["sorts"] = [{"property": parsed.sort, "direction": "descending" if parsed.desc else "ascending"}]

    db_id = parsed.database_id.replace("-", "")
    result = api_request("POST", f"databases/{db_id}/query", data)
    rows = result.get("results", [])

    if not rows:
        print("  数据库为空")
        return

    # 收集列名
    all_props = {}
    for row in rows:
        for name, prop in row.get("properties", {}).items():
            if name not in all_props:
                all_props[name] = prop.get("type", "")

    # 找出 title 列优先显示
    title_col = None
    for name, ptype in all_props.items():
        if ptype == "title":
            title_col = name
            break

    print(f"📊 查询结果 ({len(rows)} 行):\n")

    for i, row in enumerate(rows, 1):
        props = row.get("properties", {})
        title_val = ""
        if title_col and title_col in props:
            title_val = format_property_value(props[title_col])

        print(f"  {i}. {title_val or '未命名'}")

        for name, prop in props.items():
            if name == title_col:
                continue
            val = format_property_value(prop)
            if val:
                print(f"     {name}: {val}")
        print()


def cmd_page(args):
    """读取页面内容"""
    parser = argparse.ArgumentParser(prog='page', add_help=False)
    parser.add_argument('page_id')

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print("用法: page <page_id>")
        return

    page_id = parsed.page_id.replace("-", "")

    # 获取页面属性
    page = api_request("GET", f"pages/{page_id}")
    props = page.get("properties", {})

    title = ""
    for p in props.values():
        if p.get("type") == "title":
            title = rich_text_to_str(p.get("title", []))
            break

    print(f"📄 {title or '未命名'}\n")

    # 显示属性
    for name, prop in props.items():
        if prop.get("type") == "title":
            continue
        val = format_property_value(prop)
        if val:
            print(f"  {name}: {val}")

    # 获取页面块内容
    result = api_request("GET", f"blocks/{page_id}/children?page_size=100")
    blocks = result.get("results", [])

    if blocks:
        print(f"\n{'─' * 40}\n")
        for block in blocks:
            text = block_to_text(block)
            if text:
                print(text)


def cmd_create(args):
    """在数据库中创建新行"""
    parser = argparse.ArgumentParser(prog='create', add_help=False)
    parser.add_argument('database_id')
    parser.add_argument('--title', '-t', required=True, help='标题列的值')
    parser.add_argument('--props', '-p', default=None, help='JSON 格式的其他属性')

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print('用法: create <database_id> --title "标题" [--props \'{"状态": "进行中"}\']')
        return

    db_id = parsed.database_id.replace("-", "")

    # 先获取数据库结构，找到 title 列名
    db_info = api_request("GET", f"databases/{db_id}")
    title_col = None
    for name, prop in db_info.get("properties", {}).items():
        if prop.get("type") == "title":
            title_col = name
            break

    if not title_col:
        print("❌ 数据库中未找到 title 列")
        return

    properties = {
        title_col: {
            "title": str_to_rich_text(parsed.title)
        }
    }

    # 解析额外属性
    if parsed.props:
        try:
            extra = json.loads(parsed.props)
        except json.JSONDecodeError:
            print("❌ props 格式错误，需要 JSON")
            return

        db_props = db_info.get("properties", {})
        for name, value in extra.items():
            if name not in db_props:
                print(f"⚠️ 跳过未知属性: {name}")
                continue

            ptype = db_props[name]["type"]
            if ptype == "rich_text":
                properties[name] = {"rich_text": str_to_rich_text(str(value))}
            elif ptype == "number":
                properties[name] = {"number": float(value)}
            elif ptype == "select":
                properties[name] = {"select": {"name": str(value)}}
            elif ptype == "multi_select":
                if isinstance(value, list):
                    properties[name] = {"multi_select": [{"name": v} for v in value]}
                else:
                    properties[name] = {"multi_select": [{"name": str(value)}]}
            elif ptype == "status":
                properties[name] = {"status": {"name": str(value)}}
            elif ptype == "checkbox":
                properties[name] = {"checkbox": bool(value)}
            elif ptype == "url":
                properties[name] = {"url": str(value)}
            elif ptype == "email":
                properties[name] = {"email": str(value)}
            elif ptype == "phone_number":
                properties[name] = {"phone_number": str(value)}
            elif ptype == "date":
                properties[name] = {"date": {"start": str(value)}}
            else:
                print(f"⚠️ 暂不支持设置 {ptype} 类型: {name}")

    data = {
        "parent": {"database_id": db_id},
        "properties": properties
    }

    result = api_request("POST", "pages", data)
    print(f"✅ 已创建: {parsed.title}")
    print(f"   ID: {result.get('id', '')}")
    url = result.get("url", "")
    if url:
        print(f"   🔗 {url}")


def cmd_append(args):
    """向页面追加内容"""
    parser = argparse.ArgumentParser(prog='append', add_help=False)
    parser.add_argument('page_id')
    parser.add_argument('text')
    parser.add_argument('--type', '-t', default='paragraph',
                       choices=['paragraph', 'heading_1', 'heading_2', 'heading_3',
                               'bulleted_list_item', 'numbered_list_item', 'to_do',
                               'quote', 'callout', 'divider', 'code'])
    parser.add_argument('--lang', default='plain text', help='代码块语言')

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print('用法: append <page_id> "内容" [--type paragraph|heading_1|...]')
        return

    page_id = parsed.page_id.replace("-", "")

    if parsed.type == "divider":
        block = {"object": "block", "type": "divider", "divider": {}}
    elif parsed.type == "code":
        block = {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": str_to_rich_text(parsed.text),
                "language": parsed.lang
            }
        }
    elif parsed.type == "to_do":
        block = {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": str_to_rich_text(parsed.text),
                "checked": False
            }
        }
    else:
        block = {
            "object": "block",
            "type": parsed.type,
            parsed.type: {
                "rich_text": str_to_rich_text(parsed.text)
            }
        }

    data = {"children": [block]}
    api_request("PATCH", f"blocks/{page_id}/children", data)
    print(f"✅ 已追加 [{parsed.type}] 到页面")


def cmd_update(args):
    """更新数据库中的行"""
    parser = argparse.ArgumentParser(prog='update', add_help=False)
    parser.add_argument('page_id')
    parser.add_argument('--props', '-p', required=True, help='JSON 格式的属性')

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print('用法: update <page_id> --props \'{"状态": "已完成"}\'')
        return

    page_id = parsed.page_id.replace("-", "")

    # 获取页面信息以确定属性类型
    page = api_request("GET", f"pages/{page_id}")
    page_props = page.get("properties", {})

    try:
        updates = json.loads(parsed.props)
    except json.JSONDecodeError:
        print("❌ props 格式错误，需要 JSON")
        return

    properties = {}
    for name, value in updates.items():
        if name not in page_props:
            print(f"⚠️ 跳过未知属性: {name}")
            continue

        ptype = page_props[name]["type"]
        if ptype == "title":
            properties[name] = {"title": str_to_rich_text(str(value))}
        elif ptype == "rich_text":
            properties[name] = {"rich_text": str_to_rich_text(str(value))}
        elif ptype == "number":
            properties[name] = {"number": float(value)}
        elif ptype == "select":
            properties[name] = {"select": {"name": str(value)}}
        elif ptype == "multi_select":
            if isinstance(value, list):
                properties[name] = {"multi_select": [{"name": v} for v in value]}
            else:
                properties[name] = {"multi_select": [{"name": str(value)}]}
        elif ptype == "status":
            properties[name] = {"status": {"name": str(value)}}
        elif ptype == "checkbox":
            properties[name] = {"checkbox": bool(value)}
        elif ptype == "url":
            properties[name] = {"url": str(value)}
        elif ptype == "email":
            properties[name] = {"email": str(value)}
        elif ptype == "date":
            properties[name] = {"date": {"start": str(value)}}
        else:
            print(f"⚠️ 暂不支持修改 {ptype} 类型: {name}")

    if not properties:
        print("❌ 没有可更新的属性")
        return

    data = {"properties": properties}
    api_request("PATCH", f"pages/{page_id}", data)
    print(f"✅ 已更新")


def show_help():
    print("""
📝 Notion 命令行工具

用法: python notion_tool.py <命令> [参数]

查询命令:
  search <关键词>              搜索页面和数据库
  databases                    列出所有数据库
  pages                        列出最近页面
  db <database_id>             查询数据库内容
  page <page_id>               读取页面内容

写入命令:
  create <db_id> -t "标题"     在数据库中创建新行
  append <page_id> "内容"      向页面追加内容
  update <page_id> -p '{}'     更新页面属性

查询选项:
  --limit, -n     结果数量 (默认 10-20)
  --type, -t      搜索类型: page / database
  --sort, -s      数据库排序字段
  --desc          降序排列
  --filter, -f    数据库过滤 (JSON)

写入选项:
  --title, -t     标题 (create)
  --props, -p     属性 JSON (create/update)
  --type, -t      块类型 (append): paragraph/heading_1/to_do/code 等

示例:
  search "项目"
  databases
  db abc123def --limit 10
  db abc123def --sort "状态" --desc
  create abc123def -t "新任务" -p '{"状态": "进行中"}'
  page abc123def
  append abc123def "会议纪要" --type heading_2
  update abc123def -p '{"状态": "已完成"}'

环境变量:
  NOTION_TOKEN    Internal Integration Token
""")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help', 'help'):
        show_help()
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == 'search':
        cmd_search(args)
    elif cmd == 'databases':
        cmd_databases(args)
    elif cmd == 'pages':
        cmd_pages(args)
    elif cmd == 'db':
        cmd_db(args)
    elif cmd == 'page':
        cmd_page(args)
    elif cmd == 'create':
        cmd_create(args)
    elif cmd == 'append':
        cmd_append(args)
    elif cmd == 'update':
        cmd_update(args)
    else:
        print(f"❌ 未知命令: {cmd}")
        show_help()


if __name__ == '__main__':
    main()
