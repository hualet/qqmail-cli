# qqmail-cli

腾讯企业邮箱 IMAP 命令行客户端，用于浏览邮件、查看正文、下载附件。所有输出均为 JSON 格式。

## 核心亮点

- JSON 输出 — 所有命令输出结构化 JSON，默认格式化，`--compact` 紧凑输出
- 零配置登录 — `.env` 文件管理账号密码，一条命令验证连通性
- 中文文件夹名自动解码 — Modified UTF-7 编码的文件夹名自动解码
- 纯标准库 IMAP 通信 — 不依赖第三方 IMAP 库

## 安装

依赖 [uv](https://docs.astral.sh/uv/) 管理 Python 环境和依赖：

```bash
uv sync
```

安装后可直接使用 `qqmail` 命令：

```bash
qqmail login
```

也可通过 `uv run main.py` 执行。

## 配置

在项目根目录创建 `.env` 文件：

```env
IMAP_HOST=imap.exmail.qq.com
IMAP_PORT=993
IMAP_USER=your_email@example.com
IMAP_PASSWORD=your_password_or_app_token
```

## 使用方法

所有命令默认输出格式化 JSON，加 `--compact` 输出紧凑 JSON。

### 验证登录

```bash
qqmail login
```

### 列举邮箱文件夹

```bash
qqmail folders
```

### 浏览邮件（分页）

```bash
# 查看 INBOX 第一页（默认每页 20 封）
qqmail mails

# 指定文件夹和页码
qqmail mails --folder "Sent Messages" --page 2

# 调整每页数量
qqmail mails --size 50
```

### 查看邮件详情

```bash
qqmail mail 1555

# 查看完整内容（含转发的历史邮件）
qqmail mail 1555 --raw

# 指定文件夹
qqmail mail 1555 --folder "Sent Messages"
```

输出包含：`id`、`from`、`to`、`cc`、`subject`、`date`、`body`、`attachments`。

### 操作附件

```bash
# 列出附件
qqmail attachments list 1555

# 下载全部附件
qqmail attachments download 1555 -o /tmp/attachments

# 只下载指定附件
qqmail attachments download 1555 -f "周报.xlsx" -o /tmp/attachments
```

## 命令速查

| 命令 | 说明 |
|------|------|
| `login` | 验证登录信息 |
| `folders` | 列举邮箱文件夹 |
| `mails` | 浏览邮件（`--folder`、`--page`、`--size`） |
| `mail <id>` | 获取邮件详情（`--raw` 含历史邮件） |
| `attachments list <id>` | 列出邮件附件 |
| `attachments download <id>` | 下载附件（`-f` 指定单个，`-o` 目录） |

全局选项：`--compact` 紧凑 JSON 输出。

## 许可证

MIT License
