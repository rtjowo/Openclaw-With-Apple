#!/usr/bin/env python3
"""
Outlook / Microsoft 365 邮件命令行工具 (IMAP/SMTP)

通过 IMAP 读取邮件，SMTP 发送邮件。支持 Outlook.com 和 Microsoft 365 企业邮箱。

用法: python outlook_tool.py [inbox|read|search|send|folders|count] [参数]

环境变量:
  OUTLOOK_USERNAME     - 邮箱地址 (xxx@outlook.com / xxx@hotmail.com / 企业邮箱)
  OUTLOOK_PASSWORD     - 密码或应用专用密码

认证说明:
  - Outlook.com / Hotmail: 直接使用账户密码，或在安全设置中生成应用密码
  - Microsoft 365 企业邮箱: 需管理员启用 IMAP，可能需要应用密码
  - 如开启了两步验证，必须使用应用密码:
    https://account.live.com/proofs/AppPassword
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
from datetime import datetime
import argparse
import re

# Outlook.com / Hotmail
IMAP_SERVER = "outlook.office365.com"
IMAP_PORT = 993
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587


def get_credentials():
    username = os.environ.get('OUTLOOK_USERNAME')
    password = os.environ.get('OUTLOOK_PASSWORD')

    if not username:
        print("❌ 未设置 OUTLOOK_USERNAME")
        print("   export OUTLOOK_USERNAME=\"your@outlook.com\"")
        sys.exit(1)
    if not password:
        print("❌ 未设置 OUTLOOK_PASSWORD")
        print("   export OUTLOOK_PASSWORD=\"your_password\"")
        print("")
        print("   如开启两步验证，需使用应用密码:")
        print("   https://account.live.com/proofs/AppPassword")
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
        print("   请检查密码/应用密码是否正确")
        print("   企业邮箱需确认管理员已启用 IMAP")
        sys.exit(1)


def decode_str(s):
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
    if not date_str:
        return ""
    try:
        parsed = email.utils.parsedate_to_datetime(date_str)
        return parsed.strftime("%m-%d %H:%M")
    except Exception:
        return date_str[:16]


def fetch_messages(mail, folder="INBOX", limit=10, search_criteria="ALL"):
    mail.select(folder, readonly=True)
    _, data = mail.search(None, search_criteria)
    ids = data[0].split()

    if not ids:
        return []

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
        sender = m['from']
        match = re.search(r'"?([^"<]+)"?\s*<', sender)
        sender_name = match.group(1).strip() if match else sender[:30]

        subject = m['subject'] or "(无主题)"
        print(f"  {i:2}. [{m['date']}] {sender_name}")
        print(f"      {subject}")


def cmd_read(args):
    parser = argparse.ArgumentParser(prog='read', add_help=False)
    parser.add_argument('index', type=int)
    parser.add_argument('--folder', '-f', default='INBOX')
    parser.add_argument('--limit', '-n', type=int, default=20)

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print("用法: read <编号>")
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
    parser = argparse.ArgumentParser(prog='search', add_help=False)
    parser.add_argument('query', nargs='+')
    parser.add_argument('--limit', '-n', type=int, default=10)
    parser.add_argument('--from', dest='from_addr', default=None)
    parser.add_argument('--since', default=None)

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print("用法: search <关键词> [--from 发件人] [--since YYYY-MM-DD]")
        return

    query_text = ' '.join(parsed.query)
    criteria_parts = []

    # 标准 IMAP 搜索
    criteria_parts.append(f'SUBJECT "{query_text}"')

    if parsed.from_addr:
        criteria_parts.append(f'FROM "{parsed.from_addr}"')
    if parsed.since:
        try:
            d = datetime.strptime(parsed.since, "%Y-%m-%d")
            criteria_parts.append(f'SINCE {d.strftime("%d-%b-%Y")}')
        except ValueError:
            print(f"❌ 日期格式错误: {parsed.since}")
            return

    search_str = ' '.join(criteria_parts)

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
    parser = argparse.ArgumentParser(prog='send', add_help=False)
    parser.add_argument('--to', '-t', required=True)
    parser.add_argument('--subject', '-s', required=True)
    parser.add_argument('--body', '-b', required=True)
    parser.add_argument('--cc', default=None)
    parser.add_argument('--html', action='store_true')

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        print('用法: send --to "a@b.com" --subject "主题" --body "内容"')
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
    except Exception as e:
        print(f"❌ 发送失败: {e}")


def cmd_folders(args):
    mail = get_imap()
    _, data = mail.list()
    mail.logout()

    print("📁 邮箱文件夹:\n")
    for item in data:
        decoded = item.decode()
        match = re.search(r'"[/.]" (.+)$', decoded)
        if match:
            folder = match.group(1).strip('"')
            print(f"  📁 {folder}")


def cmd_count(args):
    parser = argparse.ArgumentParser(prog='count', add_help=False)
    parser.add_argument('--folder', '-f', default='INBOX')

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
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
📧 Outlook 邮件命令行工具 (IMAP/SMTP)

用法: python outlook_tool.py <命令> [参数]

命令:
  inbox                        查看收件箱
  read <编号>                  读取邮件内容
  search <关键词>              搜索邮件
  send --to --subject --body   发送邮件
  folders                      列出文件夹
  count                        统计邮件数量

选项:
  --limit, -n    数量 (默认 10)
  --folder, -f   文件夹 (默认 INBOX)
  --from         按发件人搜索
  --since        起始日期 YYYY-MM-DD
  --cc           抄送
  --html         发送 HTML 邮件

示例:
  inbox
  read 1
  search "报告" --since 2026-01-01
  send --to "a@b.com" --subject "测试" --body "你好"

环境变量:
  OUTLOOK_USERNAME   邮箱地址
  OUTLOOK_PASSWORD   密码或应用密码

应用密码 (开启两步验证时):
  https://account.live.com/proofs/AppPassword
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
    elif cmd == 'folders':
        cmd_folders(args)
    elif cmd == 'count':
        cmd_count(args)
    else:
        print(f"❌ 未知命令: {cmd}")
        show_help()


if __name__ == '__main__':
    main()
