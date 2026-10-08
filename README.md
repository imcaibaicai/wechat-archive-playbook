# wechat-archive-playbook

**本地聊天记录全链路归档方案与工具组件** — SQLCipher 4 解密 · ZSTD 内容解码 · Markdown 归档

> **English**: [README_EN.md](README_EN.md)

> English: A local-first playbook and toolkit for archiving personal chat
> history stored in SQLCipher 4 encrypted databases (WCDB-style sharded
> layout, ZSTD-compressed message bodies) into readable Markdown.
> Keys are supplied by the user; this repo contains no key-extraction code.

## 这是什么

一套**可复现的完整方案 + 过程化脚本**：把本地即时通讯客户端
（Windows 4.x 架构）加密分片数据库中的个人聊天记录，
解密、解码、导出为按发送时间命名的 Markdown 归档。

它刻意地**不是**一个开箱即用的破解工具：

- 不内置任何从第三方进程提取密钥的功能——密钥由使用者自行提供，
  工具只负责"给定密钥 → 校验 → 解密 → 导出"；
- 不含任何版本特定的内存地址、偏移、PID 硬编码；
- 所有隐私数据（密钥文件、解密库、日记产物）均被 `.gitignore` 排除。

因此它可以被放心地公开、引用、交给其他 Agent 参考：
`src/` 是干净的数据互操作代码（与 SQLCipher 官方规范一致），
`docs/` 是把整件事复现出来的方法论。

## 功能特性

- **SQLCipher 4 页面级解密**：HMAC-SHA512 前置校验（密钥错了不会写出坏文件）、
  逐页 AES-256-CBC、多分片库 salt→key 自动匹配
- **ZSTD 透明解码**：魔数识别 + 解压 + UTF-8/GBK 编码回退
- **XML 载荷清洗**：分享链接、文件、图片占位消息还原为可读 Markdown
- **按发送时间归档**：秒级时间命名的独立文件 + 按日期分组的汇总文档
- **会话表定位**：`Msg_ + md5(会话标识)` 规则与跨分片库合并查询

## 快速开始

```bash
pip install -r requirements.txt

# 0. 自检：构造加密库 -> 解密 -> 字节级往返（无需任何真实数据）
python tests/selftest.py

# 1. 校验密钥与数据库是否匹配（不写盘）
python -m src.cli verify --db message_0.db --key <64位hex>

# 2. 批量解密目录下所有分片库
python -m src.cli decrypt --dir ./db_storage --key-file keys.txt

# 3. 导出会话为 Markdown（文件名为具体发送时间）
python -m src.cli export --dir ./decrypted_dbs --table Msg_<md5> \
    --keyword "起始消息的一段文本" --out ./export --consolidated ./archive.md
```

完整流程、目录布局、表名计算见 [docs/03-全链路流程.md](docs/03-全链路流程.md)。

## 文档索引

| 文档 | 内容 |
|------|------|
| [docs/01-存储架构.md](docs/01-存储架构.md) | 数据目录布局、加密文件头、ZSTD、`Msg_<md5>` 会话表规则 |
| [docs/02-密钥机制.md](docs/02-密钥机制.md) | SQLCipher 4 派生算法、salt→key 映射、用户自备密钥边界 |
| [docs/03-全链路流程.md](docs/03-全链路流程.md) | 备份→解密→定位→导出 五步操作手册 |
| [docs/04-排障与版本适配.md](docs/04-排障与版本适配.md) | 3.x→4.x 差异、常见失败、适配新版本的通用判定法 |
| [USE_POLICY.md](USE_POLICY.md) | 使用边界与免责声明（务必阅读） |
| [SKILL.md](SKILL.md) | 供 Agent 引用的技能说明：何时参考本仓库、按什么顺序读 |

## 目录结构

```
wechat-archive-playbook/
├── src/                    # 工具组件（无隐私硬编码，版本无关）
│   ├── sqlcipher4.py       #   SQLCipher 4 解密与密钥校验
│   ├── content.py          #   ZSTD 解码 + XML 载荷清洗
│   ├── exporter.py         #   Markdown 导出器
│   └── cli.py              #   命令行入口
├── docs/                   # 全链路方法论
├── examples/               # 脱敏示例输出
├── tests/selftest.py       # 端到端自检（构造加密库→解密→字节级往返）
├── USE_POLICY.md           # 使用边界
├── SKILL.md                # Agent 参考入口
└── requirements.txt
```

## 使用边界

仅限处理**你自己账号、你自己设备上**的个人数据备份与归档。
详见 [USE_POLICY.md](USE_POLICY.md)。本项目不提供、不包含、
也无意提供针对任何商业软件的密钥提取或绕过访问控制的功能。

## 许可

MIT，见 [LICENSE](LICENSE)。
