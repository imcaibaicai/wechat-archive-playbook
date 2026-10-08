# wechat-archive-playbook

**Offline Archiving Toolkit and Playbook for Local Chat Databases** — SQLCipher 4 Decryption · Zstandard Decompression · Markdown Export

> Chinese documentation: [README.md](README.md)

---

## Overview

`wechat-archive-playbook` is an offline toolkit and playbook designed for parsing and exporting local chat history databases.

In modern desktop messaging client architectures, data is often stored using modular sharded databases, SQLCipher 4 page-level encryption, and Zstandard (ZSTD) compressed message bodies. This project provides an end-to-end workflow and reusable scripts to decrypt database shards, decode message content, and convert conversation logs into clean, readable Markdown files suitable for long-term storage or import into knowledge management tools like Obsidian and Notion.

## Features

- **Standard SQLCipher 4 Decryption**: Follows the official SQLCipher 4 specification with HMAC-SHA512 integrity verification and per-page AES-256-CBC decryption, supporting multi-salt batch operations across shards;
- **Transparent Decompression**: Automatic ZSTD magic byte detection and decompression, with fallback support for UTF-8 and GBK encodings;
- **Rich Message Parsing**: Cleans and formats structured XML payloads (cards, shared links, image placeholders, and file attachments) into clean Markdown quotes and links;
- **Timeline-based Exporting**: Exports messages into individual Markdown notes named by exact second-level timestamps, with optional consolidated timeline files grouped by date;
- **Session Resolution & Shard Merging**: Computes session table names via MD5 hashing and automatically aggregates messages spanning multiple database shards;
- **Fully Offline & Decoupled**: Operates purely on local database files with no external network requests or dependencies on specific client runtimes.

## Design Architecture

This project focuses on the **data parsing and format transformation layer**:

1. **Explicit Key Input**: Decryption routines accept user-supplied 64-character hexadecimal keys via CLI flags or local key files;
2. **Decoupled Workflow**: Scripts operate directly on database file copies and do not interact with active processes;
3. **Data Privacy**: Local database files, decrypted outputs, and generated personal notes are excluded by default via `.gitignore` to prevent unintended leakage.

## Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Run Self-Test (Optional)

Verify the complete decryption and decoding pipeline using a synthesized in-memory test database (requires no real user data):

```bash
python tests/selftest.py
```

### 3. Verify Database Key

Test whether a given 64-hex key matches an encrypted database shard (verification only; writes no files):

```bash
python -m src.cli verify --db message_0.db --key <64-hex-key>
```

### 4. Batch Decrypt Database Shards

Batch decrypt encrypted `.db` files into standard SQLite format (`.decrypted.db`):

```bash
python -m src.cli decrypt --dir ./db_storage --key-file keys.txt
```

### 5. Export Conversation to Markdown

Extract and format messages for a specific session table into Markdown files:

```bash
python -m src.cli export --dir ./decrypted_dbs --table Msg_<md5> \
    --keyword "initial search phrase" \
    --out ./export --consolidated ./archive.md
```

> For table-name computation and detailed step-by-step guidance, see [docs/03-全链路流程.md](docs/03-全链路流程.md).

## Documentation

| Document | Description |
| :--- | :--- |
| [docs/01-存储架构.md](docs/01-存储架构.md) | Storage layout, database headers, ZSTD compression, and session table mapping |
| [docs/02-密钥机制.md](docs/02-密钥机制.md) | SQLCipher 4 page encryption, salt handling, and key derivation principles |
| [docs/03-全链路流程.md](docs/03-全链路流程.md) | Complete step-by-step guide: backup, decrypt, locate, and export |
| [docs/04-排障与版本适配.md](docs/04-排障与版本适配.md) | Troubleshooting guide and version adaptation notes |
| [SKILL.md](SKILL.md) | Specification guide for AI agents and automated workflows |

## Repository Structure

```text
wechat-archive-playbook/
├── src/                    # Core transformation scripts
│   ├── sqlcipher4.py       #   SQLCipher 4 page decryption & verification
│   ├── content.py          #   ZSTD decompression & XML cleaning
│   ├── exporter.py         #   Markdown structured exporter
│   └── cli.py              #   CLI entry point
├── docs/                   # Methodological documentation
├── examples/               # Sample output documents
├── tests/selftest.py       # Standalone end-to-end self-test
├── LICENSE                 # MIT License
├── SKILL.md                # Agent instruction guide
└── requirements.txt        # Python dependencies
```

## Disclaimer

This project is intended strictly for personal technical research, study, and offline backup/migration of personal data. Users are responsible for ensuring they have lawful access to the data they process. The authors and contributors assume no liability for any data loss or misuse resulting from this software.

## License

This project is licensed under the [MIT License](LICENSE).
