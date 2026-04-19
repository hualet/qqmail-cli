import email as email_lib
import json
import math
import os
import sys

import click

from . import imap_client


def _json_out(ctx, data):
    indent = None if ctx.obj.get("compact") else 2
    click.echo(json.dumps(data, ensure_ascii=False, indent=indent))


def _strip_forwarded(content):
    markers = [
        '<div class="forward-content"',
        '<includetail>',
        "----------------------------原始邮件----------------------------",
    ]
    candidates = [content.find(m) for m in markers]
    candidates = [i for i in candidates if i > 0]
    if candidates:
        return content[:min(candidates)].rstrip()
    return content


@click.group()
@click.option("--compact", is_flag=True, help="紧凑 JSON 输出（不格式化）")
@click.pass_context
def cli(ctx, compact):
    """腾讯企业邮箱 IMAP 客户端工具"""
    ctx.ensure_object(dict)
    ctx.obj["compact"] = compact


@cli.command()
@click.pass_context
def login(ctx):
    """验证登录信息"""
    try:
        conn = imap_client.imap_connect()
        with conn:
            pass
        _json_out(ctx, {"status": "ok", "user": os.getenv("IMAP_USER", "")})
    except Exception as e:
        _json_out(ctx, {"error": str(e)})
        sys.exit(1)


@cli.command()
@click.pass_context
def folders(ctx):
    """列举邮箱文件夹"""
    try:
        result = imap_client.list_folders()
        _json_out(ctx, result)
    except Exception as e:
        _json_out(ctx, {"error": str(e)})
        sys.exit(1)


@cli.command()
@click.option("--folder", default="INBOX", help="邮箱文件夹 (默认 INBOX)")
@click.option("--page", default=1, type=int, help="页码 (从 1 开始)")
@click.option("--size", default=20, type=int, help="每页数量 (默认 20)")
@click.pass_context
def mails(ctx, folder, page, size):
    """列举邮件 (分页，按时间倒序)"""
    try:
        total = imap_client.get_message_count(folder)
        total_pages = math.ceil(total / size) if total > 0 else 0

        result = {
            "folder": folder,
            "page": page,
            "page_size": size,
            "total": total,
            "total_pages": total_pages,
            "mails": [],
        }

        if total > 0 and page <= total_pages:
            end = total - (page - 1) * size
            start = max(1, end - size + 1)
            result["mails"] = imap_client.fetch_headers_range(folder, start, end)

        _json_out(ctx, result)
    except Exception as e:
        _json_out(ctx, {"error": str(e)})
        sys.exit(1)


@cli.command()
@click.argument("msg_id")
@click.option("--folder", default="INBOX", help="邮箱文件夹 (默认 INBOX)")
@click.option("--raw", is_flag=True, help="显示完整内容 (含转发的历史邮件)")
@click.pass_context
def mail(ctx, msg_id, folder, raw):
    """获取邮件详情"""
    try:
        raw_data = imap_client.fetch_body(msg_id, folder=folder)
        msg = email_lib.message_from_bytes(raw_data)

        body = ""
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp:
                continue
            if ct == "text/html":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")
                break
            elif ct == "text/plain" and not body:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")

        if not raw:
            body = _strip_forwarded(body)

        attachments = imap_client.list_attachments(msg_id, folder=folder)

        _json_out(ctx, {
            "id": msg_id,
            "from": imap_client.decode_str(msg.get("From", "")),
            "to": imap_client.decode_str(msg.get("To", "")),
            "cc": imap_client.decode_str(msg.get("Cc", "")),
            "subject": imap_client.decode_str(msg.get("Subject", "")),
            "date": imap_client.decode_str(msg.get("Date", "")),
            "body": body,
            "attachments": attachments,
        })
    except Exception as e:
        _json_out(ctx, {"error": str(e)})
        sys.exit(1)


@cli.group(invoke_without_command=True)
@click.pass_context
def attachments(ctx):
    """操作邮件附件"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@attachments.command("list")
@click.argument("msg_id")
@click.option("--folder", default="INBOX", help="邮箱文件夹 (默认 INBOX)")
@click.pass_context
def attachments_list(ctx, msg_id, folder):
    """列出邮件附件"""
    try:
        result = imap_client.list_attachments(msg_id, folder=folder)
        _json_out(ctx, result)
    except Exception as e:
        _json_out(ctx, {"error": str(e)})
        sys.exit(1)


@attachments.command()
@click.argument("msg_id")
@click.option("--folder", default="INBOX", help="邮箱文件夹 (默认 INBOX)")
@click.option("-f", "--filename", default=None, help="指定下载单个附件（文件名）")
@click.option("-o", "--output", default=".", help="保存目录")
@click.pass_context
def download(ctx, msg_id, folder, filename, output):
    """下载邮件附件（默认下载全部，-f 指定单个）"""
    try:
        saved = imap_client.download_attachments(msg_id, output, folder=folder, filename=filename)
        if filename and not saved:
            _json_out(ctx, {"error": f"未找到附件: {filename}"})
            sys.exit(1)
        _json_out(ctx, {"downloaded": saved})
    except Exception as e:
        _json_out(ctx, {"error": str(e)})
        sys.exit(1)


if __name__ == "__main__":
    cli()
