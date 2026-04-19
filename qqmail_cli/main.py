import sys
from datetime import date, timedelta

import click

from . import imap_client


def parse_date(value):
    if value is None:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            from datetime import datetime
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise click.BadParameter(f"无法解析日期: {value}，支持格式: YYYY-MM-DD, YYYYMMDD, YYYY/MM/DD")


@click.group()
def cli():
    """腾讯企业邮箱 IMAP 客户端工具"""
    pass


@cli.command()
def check():
    """检查登录信息是否正确"""
    try:
        user = imap_client.check_login()
        click.echo(f"登录成功: {user}")
    except Exception as e:
        click.echo(f"登录失败: {e}", err=True)
        sys.exit(1)


@cli.command("folders")
def list_folders():
    """列举邮箱文件夹"""
    folders = imap_client.list_folders()
    if not folders:
        click.echo("没有找到文件夹")
        return
    for f in folders:
        display = f["display"]
        raw = f["name"]
        if display != raw:
            click.echo(f"  {display}  ({raw})")
        else:
            click.echo(f"  {display}")


@cli.command()
@click.option("--since", required=True, help="起始日期 (YYYY-MM-DD)，必填")
@click.option("--before", default=None, help="结束日期 (YYYY-MM-DD)，可选")
@click.option("--from", "from_addr", default=None, help="发件人过滤")
@click.option("--subject", default=None, help="主题关键词过滤")
@click.option("--folder", default="INBOX", help="邮箱文件夹 (默认 INBOX)")
@click.option("--limit", default=10, help="返回结果数量 (默认 10)")
def search(since, before, from_addr, subject, folder, limit):
    """搜索邮件 (必须指定时间范围 --since)"""
    since_date = parse_date(since)
    before_date = parse_date(before) if before else None

    click.echo(f"搜索条件: SINCE {since_date}", nl=False)
    if before_date:
        click.echo(f", BEFORE {before_date}", nl=False)
    if from_addr:
        click.echo(f", FROM {from_addr}", nl=False)
    if subject:
        click.echo(f", SUBJECT 含「{subject}」", nl=False)
    click.echo(f", 文件夹: {folder}")

    try:
        results = imap_client.search_messages(
            since=since_date,
            before=before_date,
            from_addr=from_addr,
            subject=subject,
            folder=folder,
            limit=limit,
        )
    except Exception as e:
        click.echo(f"搜索失败: {e}", err=True)
        sys.exit(1)

    if not results:
        click.echo("没有匹配的邮件")
        return

    click.echo(f"\n共 {len(results)} 封匹配邮件:\n")
    for m in results:
        click.echo(f"--- ID: {m['id']} ---")
        click.echo(f"  主题: {m['subject']}")
        click.echo(f"  发件人: {m['from']}")
        click.echo(f"  日期: {m['date']}")
        click.echo()


@cli.command()
@click.argument("msg_id")
@click.option("--folder", default="INBOX", help="邮箱文件夹 (默认 INBOX)")
@click.option("--raw", "show_raw", is_flag=True, help="显示完整内容 (含转发/引用的历史邮件)")
def body(msg_id, folder, show_raw):
    """获取邮件正文内容 (默认去除转发的历史邮件)"""
    try:
        raw = imap_client.fetch_body(msg_id, folder=folder)
        msg = __import__("email").message_from_bytes(raw)

        from_str = imap_client.decode_str(msg.get("From", ""))
        subject = imap_client.decode_str(msg.get("Subject", ""))
        date_str = imap_client.decode_str(msg.get("Date", ""))

        click.echo(f"主题: {subject}")
        click.echo(f"发件人: {from_str}")
        click.echo(f"日期: {date_str}")
        click.echo()

        text_parts = []
        html_parts = []
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp:
                continue
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                text_parts.append(payload.decode(charset, errors="replace"))
            elif ct == "text/html":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                html_parts.append(payload.decode(charset, errors="replace"))

        if not show_raw:
            text_parts = [_strip_forwarded(t) for t in text_parts]
            html_parts = [_strip_forwarded(h) for h in html_parts]

        parts = html_parts or text_parts
        if parts:
            for p in parts:
                click.echo(p)
        else:
            click.echo("(无正文内容)")

    except Exception as e:
        click.echo(f"获取失败: {e}", err=True)
        sys.exit(1)


def _strip_forwarded(content):
    html_marker = '<div class="forward-content"'
    text_marker = "----------------------------原始邮件----------------------------"
    html_idx = content.find(html_marker)
    text_idx = content.find(text_marker)
    candidates = [i for i in (html_idx, text_idx) if i > 0]
    if candidates:
        return content[:min(candidates)].rstrip()
    return content


@cli.command()
@click.argument("msg_id")
@click.option("--folder", default="INBOX", help="邮箱文件夹 (默认 INBOX)")
@click.option("--output", "-o", required=True, help="附件下载目录路径")
def download(msg_id, folder, output):
    """下载邮件附件"""
    try:
        attachments = imap_client.list_attachments(msg_id, folder=folder)
        if not attachments:
            click.echo("该邮件没有附件")
            return

        click.echo(f"找到 {len(attachments)} 个附件:")
        for a in attachments:
            click.echo(f"  {a['filename']} ({a['size']} bytes, {a['content_type']})")

        downloaded = imap_client.download_attachments(msg_id, output, folder=folder)
        click.echo(f"\n已下载 {len(downloaded)} 个附件到 {output}:")
        for f in downloaded:
            click.echo(f"  {f}")

    except Exception as e:
        click.echo(f"下载失败: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
