# wechat-archive-playbook

**本地聊天记录离线归档工具集与技术指南** — SQLCipher 4 解析 · Zstandard 内容解码 · Markdown 结构化导出

> **English**: [README_EN.md](README_EN.md)

---

## 项目介绍

`wechat-archive-playbook` 是一个用于解析与导出本地聊天数据库的离线归档工具链。

在现代桌面客户端架构中，本地数据通常采用模块化分库、SQLCipher 4 分页加密以及 Zstandard (ZSTD) 压缩正文存储。本项目提供了一套完整的数据库解密、内容解析与格式转换方案，帮助用户将个人聊天记录、文件传输助手便签等数据无损导出为清晰排版的 Markdown 文档，便于离线检索、长期保存或导入至 Obsidian、Notion 等知识库工具中。

## 核心特性

- **标准解密与完整性校验**：遵循标准 SQLCipher 4 规范，基于 HMAC-SHA512 前置完整性校验与 AES-256-CBC 逐页解密，支持多分片库多 Salt 批量匹配；
- **透明解压缩与内容还原**：自动识别 ZSTD 压缩流魔数并解压，兼容 UTF-8 与 GBK 编码回退；
- **结构化富文本清洗**：智能解析卡片分享、链接、图文占位及文件附件等 XML 载荷，格式化为易读的 Markdown 引用和链接；
- **时间线归档导出**：支持按秒级发送时间命名导出单篇 Markdown 记录，并可同步生成按日期聚合的时间线长文档；
- **会话映射与跨库聚合**：内置会话标识 MD5 表名计算规则，自动跨所有分片数据文件聚合提取完整会话流；
- **解耦设计与离线运行**：数据转换逻辑与运行环境完全解耦，全部运算均在本地离线执行，无任何外部网络请求。

## 设计说明

本项目专注于**数据格式解析与内容转换层**：

1. **输入参数**：解密模块接收用户显式提供的 64 位 Hex 密钥（通过命令行参数或本地文本文件传入）；
2. **流程解耦**：工具链不绑定特定客户端运行状态，所有操作均直接在本地数据库文件副本上执行；
3. **数据安全**：本地数据库副本、解密产物及生成的个人日记文档均已加入 `.gitignore`，避免本地数据意外上传。

## 快速开始

### 1. 环境准备

```bash
pip install -r requirements.txt
```

### 2. 运行端到端自检（可选）

运行内置自检脚本，在内存中构建测试数据库验证解密与解码链路：

```bash
python tests/selftest.py
```

### 3. 校验密钥

验证指定的 64 位 Hex 密钥是否能匹配目标数据库（仅做校验，不写盘）：

```bash
python -m src.cli verify --db message_0.db --key <64位Hex密钥>
```

### 4. 批量解密数据库

将指定目录下的所有分片数据库批量解密为标准 SQLite 文件（生成同名 `.decrypted.db`）：

```bash
python -m src.cli decrypt --dir ./db_storage --key-file keys.txt
```

### 5. 导出会话为 Markdown

根据会话表名提取消息并导出为按时间命名的 Markdown 归档文件：

```bash
python -m src.cli export --dir ./decrypted_dbs --table Msg_<md5> \
    --keyword "起始消息文本" \
    --out ./export --consolidated ./archive.md
```

> 会话表名计算方法及详细分步说明，请参阅 [docs/03-全链路流程.md](docs/03-全链路流程.md)。

## 技术文档

| 文档 | 说明 |
| :--- | :--- |
| [docs/01-存储架构.md](docs/01-存储架构.md) | 本地分片存储布局、数据库头部格式、ZSTD 压缩流及会话表名映射机制 |
| [docs/02-密钥机制.md](docs/02-密钥机制.md) | SQLCipher 4 页面级加密算法、Salt 与派生密钥映射原理 |
| [docs/03-全链路流程.md](docs/03-全链路流程.md) | 备份、解密、会话定位与 Markdown 导出的标准操作手册 |
| [docs/04-排障与版本适配.md](docs/04-排障与版本适配.md) | 常见错误排查指南及跨版本结构变更适配建议 |
| [SKILL.md](SKILL.md) | 供 AI Agent / 自动化脚本参考的技能调用规范 |

## 目录结构

```text
wechat-archive-playbook/
├── src/                    # 核心转换工具集
│   ├── sqlcipher4.py       #   SQLCipher 4 页面解密与校验
│   ├── content.py          #   ZSTD 流解压与 XML 载荷清洗
│   ├── exporter.py         #   Markdown 结构化导出器
│   └── cli.py              #   命令行入口
├── docs/                   # 技术方案与参考手册
├── examples/               # 示例输出文档
├── tests/selftest.py       # 端到端无真实数据自检测试
├── LICENSE                 # MIT 开源协议
├── SKILL.md                # Agent 调用指南
└── requirements.txt        # 依赖声明
```

## 免责声明

本项目仅供个人技术学习、研究以及合法个人自有数据的离线备份与迁移使用。使用本项目时，请确保您对目标数据拥有合法所有权与访问权。作者与贡献者不对使用本工具产生的任何数据损失或合规问题承担责任。

## 开源协议

本项目遵循 [MIT License](LICENSE)。
