# AGENTS.md

## 项目概述

腾讯企业邮箱 IMAP 命令行客户端。纯标准库 IMAP 通信 + Click CLI，无第三方 IMAP 库。

## 运行命令

```bash
uv sync                # 安装依赖
uv sync --extra dev    # 安装含 lint 工具的开发依赖
uv run main.py <command>  # 运行 CLI
uv run ruff check qqmail_cli/  # lint 检查
uv run ruff check qqmail_cli/ --fix  # lint 自动修复
```

无测试套件。

## 架构

- `main.py` — Click CLI 入口，命令：`login`, `folders`, `mails`, `mail`, `attachments`
- `imap_client.py` — IMAP 通信层，模块级加载 `.env`，纯标准库 `imaplib`

## 关键实现细节

- 中文文件夹名使用 Modified UTF-7 编码，`mutf7_decode()` 做解码
- 所有命令输出 JSON，`--compact` 全局选项控制格式化
- `mail` 命令默认去除转发/回复的历史邮件内容，`--raw` 显示完整内容；支持三种引用格式：deepin-mail `forward-content`、腾讯邮箱 `includetail`、纯文本 `原始邮件`
- Python ≥ 3.10，依赖仅有 `click` 和 `python-dotenv`

## 环境配置

运行前需在项目根目录创建 `.env`：

```
IMAP_HOST=imap.exmail.qq.com
IMAP_PORT=993
IMAP_USER=...
IMAP_PASSWORD=...
```

## Git 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：`type(scope): description`，如 `fix(search): 修复日期过滤边界问题`。提交必须包含 body，交代变更内容、解决了什么问题或新增了什么功能等。

提交前必须用 gitleaks 扫描敏感信息泄漏：

```bash
docker run -v $(pwd):/repo ghcr.io/gitleaks/gitleaks:latest detect --source /repo --no-git
```

扫描无泄漏才可提交。

## 注意事项

- 不要在代码或文档中包含真实的公司/个人信息（邮箱、部门名等）
- `.env` 已在 `.gitignore` 中，不会提交
