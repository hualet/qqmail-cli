# AGENTS.md

## 项目概述

腾讯企业邮箱 IMAP 命令行客户端。纯标准库 IMAP 通信 + Click CLI，无第三方 IMAP 库。

## 运行命令

```bash
uv sync          # 安装依赖
uv run main.py <command>  # 运行 CLI
```

无测试套件、无 lint/typecheck 配置。

## 架构

- `main.py` — Click CLI 入口，命令：`check`, `folders`, `search`, `body`, `download`
- `imap_client.py` — IMAP 通信层，模块级加载 `.env`，纯标准库 `imaplib`

## 关键实现细节

- 腾讯企业邮箱 IMAP 的 `SEARCH FROM`/`SEARCH SUBJECT` 服务端有缺陷（返回全部结果），因此 `search` 命令只用服务端 `SINCE`/`BEFORE` 做日期过滤，再分批拉取头部字段在客户端做二次过滤（`_batch_fetch_and_filter`），每批 30 封（`BATCH_SIZE`）
- 中文文件夹名使用 Modified UTF-7 编码，`mutf7_decode()` 做解码
- Python ≥ 3.13，依赖仅有 `click` 和 `python-dotenv`

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
