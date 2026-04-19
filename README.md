# qqmail-cli

腾讯企业邮箱 IMAP 命令行客户端，用于搜索邮件、查看正文、下载附件。

## 核心亮点

- 零配置登录 — `.env` 文件管理账号密码，一条命令验证连通性
- 智能搜索兼容 — 腾讯企业邮箱 IMAP 的 `FROM`/`SUBJECT` 搜索存在服务端缺陷，本工具采用 `SINCE` 日期搜索 + 本地二次过滤的策略绕过，确保结果准确
- 中文文件夹名自动解码 — Modified UTF-7 编码的文件夹名（如 `&UXZO1mWHTvZZOQ-`）自动解码为中文（如 `其他文件夹`）
- 纯标准库 IMAP 通信 — 不依赖第三方 IMAP 库，减少兼容性问题
- 分批拉取 — 大量邮件自动分批请求，避免超时

## 安装

依赖 [uv](https://docs.astral.sh/uv/) 管理 Python 环境和依赖：

```bash
cd python-script
uv sync
```

## 配置

在项目根目录创建 `.env` 文件：

```env
IMAP_HOST=imap.exmail.qq.com
IMAP_PORT=993
IMAP_USER=your_email@example.com
IMAP_PASSWORD=your_password_or_app_token
```

## 使用方法

所有命令通过 `uv run main.py` 执行：

### 检查登录

```bash
uv run main.py check
```

### 列举邮箱文件夹

```bash
uv run main.py folders
```

输出示例：

```
  其他文件夹  (&UXZO1mWHTvZZOQ-)
  Deleted Messages
  Drafts
  Sent Messages
  INBOX
```

### 搜索邮件

`--since` 为必填参数，用于限定时间范围。`--from` 和 `--subject` 为可选的二次过滤条件。

```bash
# 搜索本周所有邮件
uv run main.py search --since 2026-04-13

# 按发件人过滤
uv run main.py search --since 2026-04-13 --from sender@example.com

# 按主题关键词过滤
uv run main.py search --since 2026-04-13 --subject 周报

# 组合过滤 + 限制数量
uv run main.py search --since 2026-04-13 --before 2026-04-20 \
  --from sender@example.com --subject 周报 --limit 5

# 指定文件夹
uv run main.py search --since 2026-04-01 --folder "Sent Messages"
```

输出示例：

```
搜索条件: SINCE 2026-04-13, FROM sender@example.com, SUBJECT 含「周报」, 文件夹: INBOX

共 1 封匹配邮件:

--- ID: 1555 ---
  主题: 项目周报 (2026.4.18)
  发件人: sender@example.com <sender@example.com>
  日期: Sat, 18 Apr 2026 14:58:04 +0800
```

### 获取邮件正文

使用 `search` 获取到的邮件 ID 来查看正文内容：

```bash
uv run main.py body 1555
```

正文按 MIME 结构输出纯文本和 HTML 两个部分。指定文件夹：

```bash
uv run main.py body 1555 --folder "Sent Messages"
```

### 下载附件

```bash
# 下载到指定目录
uv run main.py download 1555 -o /tmp/attachments
```

输出示例：

```
找到 2 个附件:
  周报.xlsx (15360 bytes, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
  截图.png (82456 bytes, image/png)

已下载 2 个附件到 /tmp/attachments:
  /tmp/attachments/周报.xlsx
  /tmp/attachments/截图.png
```

## 命令速查

| 命令 | 说明 |
|------|------|
| `check` | 验证登录信息 |
| `folders` | 列举邮箱文件夹 |
| `search` | 搜索邮件（`--since` 必填） |
| `body <msg_id>` | 获取邮件正文 |
| `download <msg_id>` | 下载邮件附件（`-o` 指定目录） |

## 已知问题

腾讯企业邮箱 IMAP 服务端的 `SEARCH FROM` 和 `SEARCH SUBJECT` 指令无法正确过滤结果（返回全部邮件），本工具通过以下策略绕过：

1. 使用服务端可靠的 `SINCE`/`BEFORE` 日期搜索缩小范围
2. 批量拉取候选邮件的头部字段
3. 在客户端本地完成发件人和主题的过滤

## 许可证

MIT License
