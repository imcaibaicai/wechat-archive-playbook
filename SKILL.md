---
name: wechat-archive-playbook
description: 本地即时通讯客户端（SQLCipher 4 数据库、ZSTD 压缩流）个人聊天记录解析与 Markdown 离线归档工具。当用户需要离线导出个人聊天记录、备份文件传输助手日记笔记为 Markdown、解密本地 SQLCipher 数据库或解析 ZSTD 消息正文时参考本指南。
---

# wechat-archive-playbook（Agent 执行指南）

## 适用场景

当用户提出以下需求时，参考本方案执行：

- **个人记录导出**：将本地即时通讯客户端会话（如文件传输助手、个人笔记、重要对话）批量导出为清晰排版的 Markdown；
- **知识库集成**：将导出的聊天记录按发送时间归档，导入 Obsidian、Notion 或本地知识库；
- **本地数据库解析**：解密符合 SQLCipher 4 规范（AES-256-CBC + HMAC-SHA512）的分片 SQLite 数据库；
- **正文流还原**：处理 Zstandard (ZSTD) 压缩流与 XML 结构化消息（分享链接、引用、附件卡片）。

## 前置要求与安全规范

1. **先做备份**：在执行任何解密或转换前，必须确保目标数据库目录已有完整离线备份；
2. **密钥输入**：本工具链解密逻辑基于用户显式提供的 64 位 Hex 密钥，不包含运行时内存扫描或进程探测逻辑；
3. **隐私防护**：生成的明文数据库（`*.decrypted.db`）与 Markdown 日记产物均属私有个人数据，务必保持在 `.gitignore` 保护范围内。

## 标准执行流程

1. **查阅存储架构**：阅读 `docs/01-存储架构.md`，确认数据存储目录，计算会话表名（`Msg_ + md5(会话标识)`）；
2. **确认密钥与规范**：阅读 `docs/02-密钥机制.md`，获取用户提供的目标数据库 64 位 Hex 密钥；
3. **环境自检（可选）**：运行 `python tests/selftest.py` 验证环境依赖与解密/解码管线正常；
4. **单库验证与批量解密**：
   - 验证密钥匹配：`python -m src.cli verify --db <path_to_db> --key <hex_key>`
   - 批量解密分片库：`python -m src.cli decrypt --dir <db_dir> --key-file keys.txt`
5. **提取并导出 Markdown**：
   - 调用 `python -m src.cli export --dir <decrypted_dir> --table <table_name> --out <export_dir> --consolidated <archive_path>`
   - 支持 `--keyword`（按起始文本截取）与 `--since`（按时间戳截取）；
6. **异常排查**：若遇问题参阅 `docs/04-排障与版本适配.md`。

## 模块代码复用

- `src/sqlcipher4.py`：标准 SQLCipher 4 页面解密（`decrypt_db`）与密钥校验（`verify_key`）；
- `src/content.py`：ZSTD 流透明解压（`decompress_zstd`）、编码兼容解码（`safe_decode`）与 XML 卡片清洗（`clean_message_content`）；
- `src/exporter.py`：跨分片库会话合并（`collect_messages`）、时间线切片（`slice_from`）与 Markdown 文件生成（`export`）；
- `src/cli.py`：封装了 `verify`、`decrypt`、`export` 子命令的统一 CLI 入口。
