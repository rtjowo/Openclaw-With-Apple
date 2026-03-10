#!/usr/bin/env python3
"""
Gmail 命令行工具 (IMAP/SMTP)

通过 IMAP 读取邮件，SMTP 发送邮件。使用 Google 应用专用密码认证。

用法: python gmail_tool.py [inbox|read|search|send|labels|count] [参数]

环境变量:
  GMAIL_USERNAME     - Gmail 邮箱地址
  GMAIL_APP_PASSWORD - Google 应用专用密码

应用专用密码获取:
  1. 访问 https://myaccount.google.com/apppasswords
  2. 选择应用 → 生成密码
  3. 复制 16 位密码（格式: xxxx xxxx xxxx xxxx）
  注意: 需要先开启两步验证
"""

import sys
import os
import imaplib
import smtplib
import email
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime, timedelta
import argparse
import re

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def get_credentials():
    username = os.environ.get('GMAIL_USERNAME')
    password = os.environ.get('GMAIL_APP_PASSWORD')

    if not username:
        print("❌ 未设置 GMAIL_USERNAME")
        print("   export GMAIL_USERNAME=\"your@gmail.com\"")
        sys.exit(1)
    if not password:
        print("❌ 未设置 GMAIL_APP_PASSWORD")
        print("   export GMAIL_APP_PASSWORD=\"xxxx xxxx xxxx xxxx\"")
        print("")
        print("   获取方式:")
        print("   1. 访问 https://myaccount.google.com/apppasswords")
        print("   2. 生成应用专用密码")
        sys.exit(1)

    return username, password


def get_imap():
    username, password = get_credentials()
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(username, password)
        return mail
    except imaplib.IMAP4.error as e:
        print(f"❌ 登录失败: {e}")
        print("   请检查应用专用密码是否正确")
        sys.exit(1)


def decode_str(s):
    """解码邮件头部字段"""
    if s is None:
        return ""
    parts = decode_header(s)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or 'utf-8', errors='replace'))
        else:
            result.append(str(part))
    return ''.join(result)


def get_body(msg):
    """提取邮件正文"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
                    break
                except Exception:
                    pass
            elif ctype == "text/html" and not body:
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    html = payload.decode(charset, errors='replace')
                    # 简单去 HTML 标签
                    body = re.sub(r'<[^>]+>', '', html)
                    body = re.sub(r'\s+', ' ', body).strip()
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            body = payload.decode(charset, errors='replace')
        except Exception:
            body = str(msg.get_payload())

    return body.strip()


def format_date(date_str):
    """格式化邮件日期"""
    if not date_str:
        return ""
    try:
        parsed = email.utils.parsedate_to_datetime(date_str)
        return parsed.strftime("%m-%d %H:%M")
    except Exception:
        return date_str[:16]


def fetch_messages(mail, folder="INBOX", limit=10, search_criteria="ALL"):
    """获取邮件列表"""
    mail.select(folder, readonly=True)
    _, data = mail.search(None, search_criteria)
    ids = data[0].split()

    if not ids:
        return []

    # 取最新的 N 封
    ids = ids[-limit:]
    ids.reverse()

    messages = []
    for mid in ids:
        _, data = mail.fetch(mid, "(RFC822)")
        raw = data[0][1]
        msg = email.message_from_bytes(raw)

        messages.append({
            'id': mid.decode(),
            'from': decode_str(msg.get('From', '')),
            'to': decode_str(msg.get('To', '')),
            'subject': decode_str(msg.get('Subject', '')),
            'date': format_date(msg.get('Date', '')),
            'body': get_body(msg),
            'msg': msg
        })

    return messages


def cmd_inbox(args):
    """查看收件箱"""
    parser = argparse.ArgumentParser(prog='inbox', add_help=False)
    parser.add_argument('--limit', '-n', type=int, default=10)
    parser.add_argument('--folder', '-f', default='INBOX')

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print("用法: inbox [--limit N] [--folder INBOX]")
        return

    mail = get_imap()
    messages = fetch_messages(mail, folder=parsed.folder, limit=parsed.limit)
    mail.logout()

    if not messages:
        print("  收件箱为空")
        return

    print(f"📬 {parsed.folder} (最近 {len(messages)} 封):\n")
    for i, m in enumerate(messages, 1):
        # 提取发件人名称
        sender = m['from']
        match = re.search(r'"?([^"<]+)"?\s*<', sender)
        sender_name = match.group(1).strip() if match else sender[:30]

        subject = m['subject'] or "(无主题)"
        print(f"  {i:2}. [{m['date']}] {sender_name}")
        print(f"      {subject}")


def cmd_read(args):
    """读取邮件内容"""
    parser = argparse.ArgumentParser(prog='read', add_help=False)
    parser.add_argument('index', type=int, help='邮件编号')
    parser.add_argument('--folder', '-f', default='INBOX')
    parser.add_argument('--limit', '-n', type=int, default=20)

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print("用法: read <编号> [--folder INBOX]")
        return

    mail = get_imap()
    messages = fetch_messages(mail, folder=parsed.folder, limit=parsed.limit)
    mail.logout()

    idx = parsed.index - 1
    if idx < 0 or idx >= len(messages):
        print(f"❌ 编号超出范围 (1-{len(messages)})")
        return

    m = messages[idx]
    print(f"📧 {m['subject'] or '(无主题)'}\n")
    print(f"  发件人: {m['from']}")
    print(f"  收件人: {m['to']}")
    print(f"  时  间: {m['date']}")
    print(f"\n{'─' * 50}\n")

    body = m['body']
    if len(body) > 3000:
        body = body[:3000] + "\n\n... (内容已截断)"
    print(body)


def cmd_search(args):
    """搜索邮件"""
    parser = argparse.ArgumentParser(prog='search', add_help=False)
    parser.add_argument('query', nargs='+')
    parser.add_argument('--limit', '-n', type=int, default=10)
    parser.add_argument('--from', dest='from_addr', default=None)
    parser.add_argument('--since', default=None, help='起始日期 YYYY-MM-DD')

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print("用法: search <关键词> [--from 发件人] [--since YYYY-MM-DD] [--limit N]")
        return

    # 构建 IMAP 搜索条件
    criteria_parts = []
    query_text = ' '.join(parsed.query)

    # Gmail 支持 X-GM-RAW 扩展搜索
    criteria_parts.append(f'X-GM-RAW "{query_text}"')

    if parsed.from_addr:
        criteria_parts.append(f'FROM "{parsed.from_addr}"')
    if parsed.since:
        try:
            d = datetime.strptime(parsed.since, "%Y-%m-%d")
            criteria_parts.append(f'SINCE {d.strftime("%d-%b-%Y")}')
        except ValueError:
            print(f"❌ 日期格式错误: {parsed.since}")
            return

    search_str = ' '.join(criteria_parts) if criteria_parts else 'ALL'

    mail = get_imap()
    messages = fetch_messages(mail, limit=parsed.limit, search_criteria=search_str)
    mail.logout()

    if not messages:
        print(f"  未找到: {query_text}")
        return

    print(f"🔍 搜索: {query_text} ({len(messages)} 封)\n")
    for i, m in enumerate(messages, 1):
        sender = m['from']
        match = re.search(r'"?([^"<]+)"?\s*<', sender)
        sender_name = match.group(1).strip() if match else sender[:30]
        print(f"  {i:2}. [{m['date']}] {sender_name}")
        print(f"      {m['subject'] or '(无主题)'}")


def cmd_send(args):
    """发送邮件"""
    parser = argparse.ArgumentParser(prog='send', add_help=False)
    parser.add_argument('--to', '-t', required=True)
    parser.add_argument('--subject', '-s', required=True)
    parser.add_argument('--body', '-b', required=True)
    parser.add_argument('--cc', default=None)
    parser.add_argument('--html', action='store_true')

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print('用法: send --to "a@b.com" --subject "主题" --body "内容" [--cc "c@d.com"]')
        return

    username, password = get_credentials()

    msg = MIMEMultipart()
    msg['From'] = username
    msg['To'] = parsed.to
    msg['Subject'] = parsed.subject
    if parsed.cc:
        msg['Cc'] = parsed.cc

    content_type = 'html' if parsed.html else 'plain'
    msg.attach(MIMEText(parsed.body, content_type, 'utf-8'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(username, password)

        recipients = [parsed.to]
        if parsed.cc:
            recipients += [addr.strip() for addr in parsed.cc.split(',')]

        server.sendmail(username, recipients, msg.as_string())
        server.quit()

        print(f"✅ 已发送")
        print(f"   收件人: {parsed.to}")
        print(f"   主  题: {parsed.subject}")
        if parsed.cc:
            print(f"   抄  送: {parsed.cc}")
    except Exception as e:
        print(f"❌ 发送失败: {e}")


def cmd_labels(args):
    """列出 Gmail 标签（文件夹）"""
    mail = get_imap()
    _, data = mail.list()
    mail.logout()

    print("🏷️  Gmail 标签:\n")
    for item in data:
        decoded = item.decode()
        # 提取标签名
        match = re.search(r'"/" (.+)$', decoded)
        if match:
            label = match.group(1).strip('"')
            print(f"  📁 {label}")


def cmd_count(args):
    """统计邮件数量"""
    parser = argparse.ArgumentParser(prog='count', add_help=False)
    parser.add_argument('--folder', '-f', default='INBOX')

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print("用法: count [--folder INBOX]")
        return

    mail = get_imap()
    mail.select(parsed.folder, readonly=True)
    _, data = mail.search(None, 'ALL')
    total = len(data[0].split()) if data[0] else 0

    _, unseen_data = mail.search(None, 'UNSEEN')
    unseen = len(unseen_data[0].split()) if unseen_data[0] else 0

    mail.logout()

    print(f"📬 {parsed.folder}: {total} 封邮件, {unseen} 封未读")


def show_help():
    print("""
📧 Gmail 命令行工具 (IMAP/SMTP)

用法: python gmail_tool.py <命令> [参数]

命令:
  inbox                        查看收件箱
  read <编号>                  读取邮件内容
  search <关键词>              搜索邮件
  send --to --subject --body   发送邮件
  labels                       列出所有标签
  count                        统计邮件数量

选项:
  --limit, -n    数量 (默认 10)
  --folder, -f   文件夹/标签 (默认 INBOX)
  --from         按发件人搜索
  --since        起始日期 YYYY-MM-DD
  --cc           抄送
  --html         发送 HTML 邮件

示例:
  inbox
  inbox --limit 20
  read 1
  search "报告" --since 2026-01-01
  send --to "a@b.com" --subject "测试" --body "你好"
  labels
  count

环境变量:
  GMAIL_USERNAME      Gmail 邮箱
  GMAIL_APP_PASSWORD  应用专用密码

应用专用密码获取:
  1. 访问 https://myaccount.google.com/apppasswords
  2. 生成密码（需先开启两步验证）
""")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help', 'help'):
        show_help()
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == 'inbox':
        cmd_inbox(args)
    elif cmd == 'read':
        cmd_read(args)
    elif cmd == 'search':
        cmd_search(args)
    elif cmd == 'send':
        cmd_send(args)
    elif cmd == 'labels':
        cmd_labels(args)
    elif cmd == 'count':
        cmd_count(args)
    else:
        print(f"❌ 未知命令: {cmd}")
        show_help()


if __name__ == '__main__':
    main()
