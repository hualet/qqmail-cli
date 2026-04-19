import base64
import email
import imaplib
import os
from contextlib import contextmanager, suppress
from email.header import decode_header
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

IMAP_HOST = os.getenv("IMAP_HOST", "imap.exmail.qq.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")

BATCH_SIZE = 30


def decode_str(raw):
    if raw is None:
        return ""
    parts = decode_header(raw)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def mutf7_decode(s):
    result = []
    i = 0
    while i < len(s):
        if s[i] == "&" and i + 1 < len(s) and s[i + 1] == "-":
            result.append("&")
            i += 2
        elif s[i] == "&":
            j = s.index("-", i)
            b64 = s[i + 1 : j]
            padded = b64 + "=" * (4 - len(b64) % 4) if len(b64) % 4 else b64
            raw = base64.b64decode(padded)
            result.append(raw.decode("utf-16-be"))
            i = j + 1
        else:
            result.append(s[i])
            i += 1
    return "".join(result)


@contextmanager
def imap_connect():
    if not IMAP_USER or not IMAP_PASSWORD:
        raise click_error("请在 .env 文件中配置 IMAP_USER 和 IMAP_PASSWORD")

    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    try:
        conn.login(IMAP_USER, IMAP_PASSWORD)
        yield conn
    finally:
        with suppress(Exception):
            conn.logout()


def click_error(msg):
    import click
    return click.ClickException(msg)


def check_login():
    with imap_connect():
        return IMAP_USER


def list_folders():
    with imap_connect() as conn:
        status, folders = conn.list()
        if status != "OK":
            raise click_error("获取文件夹列表失败")
        result = []
        for f in folders:
            decoded = f.decode() if isinstance(f, bytes) else f
            parts = decoded.split('"/"')
            if len(parts) == 2:
                flags = parts[0].strip()
                name = parts[1].strip().strip('"')
            else:
                flags = ""
                name = decoded.strip()
            result.append({"flags": flags, "name": name, "display": mutf7_decode(name)})
        return result


def search_messages(since, before=None, from_addr=None, subject=None, folder="INBOX", limit=10):
    with imap_connect() as conn:
        status, _ = conn.select(folder, readonly=True)
        if status != "OK":
            raise click_error(f"无法打开文件夹: {folder}")

        since_str = since.strftime("%d-%b-%Y")
        criteria = ["SINCE", since_str]
        if before:
            criteria += ["BEFORE", before.strftime("%d-%b-%Y")]

        _, data = conn.search(None, *criteria)
        since_ids = data[0].split()

        if not since_ids:
            return []

        matched = _batch_fetch_and_filter(conn, since_ids, from_addr, subject)
        return matched[-limit:]


def _batch_fetch_and_filter(conn, msg_ids, from_addr=None, subject=None):
    matched = []
    for i in range(0, len(msg_ids), BATCH_SIZE):
        batch = msg_ids[i : i + BATCH_SIZE]
        range_str = ",".join(mid.decode() for mid in batch)
        _, resp = conn.fetch(
            range_str, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])"
        )
        for item in resp:
            if not isinstance(item, tuple):
                continue
            msg_id_raw = item[0]
            header_raw = item[1]
            mid = msg_id_raw.split()[0].decode()
            msg = email.message_from_bytes(header_raw)
            from_str = decode_str(msg.get("From", ""))
            subject_str = decode_str(msg.get("Subject", ""))
            date_str = decode_str(msg.get("Date", ""))

            if from_addr and from_addr.lower() not in from_str.lower():
                continue
            if subject and subject not in subject_str:
                continue

            matched.append(
                {
                    "id": mid,
                    "subject": subject_str,
                    "from": from_str,
                    "date": date_str,
                }
            )
    return matched


def fetch_body(msg_id, folder="INBOX"):
    with imap_connect() as conn:
        status, _ = conn.select(folder, readonly=True)
        if status != "OK":
            raise click_error(f"无法打开文件夹: {folder}")

        _, resp = conn.fetch(msg_id, "(RFC822)")
        for item in resp:
            if isinstance(item, tuple) and b"RFC822" in item[0]:
                return item[1]

    raise click_error(f"未找到邮件 ID: {msg_id}")


def list_attachments(msg_id, folder="INBOX"):
    with imap_connect() as conn:
        status, _ = conn.select(folder, readonly=True)
        if status != "OK":
            raise click_error(f"无法打开文件夹: {folder}")

        _, resp = conn.fetch(msg_id, "(RFC822)")
        for item in resp:
            if isinstance(item, tuple) and b"RFC822" in item[0]:
                msg = email.message_from_bytes(item[1])
                attachments = []
                for part in msg.walk():
                    cd = part.get("Content-Disposition", "")
                    if "attachment" in cd or "filename" in part.get("Content-Type", ""):
                        filename = part.get_filename()
                        if filename:
                            filename = decode_str(filename)
                            attachments.append({
                                "filename": filename,
                                "size": len(part.get_payload(decode=True) or b""),
                                "content_type": part.get_content_type(),
                            })
                return attachments

    raise click_error(f"未找到邮件 ID: {msg_id}")


def download_attachments(msg_id, output_dir, folder="INBOX", filename=None):
    with imap_connect() as conn:
        status, _ = conn.select(folder, readonly=True)
        if status != "OK":
            raise click_error(f"无法打开文件夹: {folder}")

        _, resp = conn.fetch(msg_id, "(RFC822)")
        for item in resp:
            if isinstance(item, tuple) and b"RFC822" in item[0]:
                msg = email.message_from_bytes(item[1])
                out_path = Path(output_dir)
                out_path.mkdir(parents=True, exist_ok=True)
                downloaded = []
                for part in msg.walk():
                    att_name = part.get_filename()
                    if not att_name:
                        if "attachment" not in part.get("Content-Disposition", ""):
                            continue
                        att_name = "unnamed_attachment"
                    att_name = decode_str(att_name)
                    if filename and att_name != filename:
                        continue
                    payload = part.get_payload(decode=True)
                    if payload is None:
                        continue
                    filepath = out_path / att_name
                    filepath.write_bytes(payload)
                    downloaded.append({"filename": att_name, "size": len(payload), "path": str(filepath)})
                return downloaded

    raise click_error(f"未找到邮件 ID: {msg_id}")


def get_message_count(folder="INBOX"):
    with imap_connect() as conn:
        status, data = conn.select(folder, readonly=True)
        if status != "OK":
            raise click_error(f"无法打开文件夹: {folder}")
        return int(data[0])


def fetch_headers_range(folder, start, end):
    with imap_connect() as conn:
        status, _ = conn.select(folder, readonly=True)
        if status != "OK":
            raise click_error(f"无法打开文件夹: {folder}")

        range_str = f"{start}:{end}"
        _, resp = conn.fetch(range_str, "(BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT DATE)])")

        results = []
        for item in resp:
            if not isinstance(item, tuple):
                continue
            seq_num = item[0].split()[0].decode()
            try:
                int(seq_num)
            except ValueError:
                continue
            msg = email.message_from_bytes(item[1])
            results.append({
                "id": seq_num,
                "from": decode_str(msg.get("From", "")),
                "subject": decode_str(msg.get("Subject", "")),
                "date": decode_str(msg.get("Date", "")),
            })

        results.sort(key=lambda x: int(x["id"]), reverse=True)
        return results
