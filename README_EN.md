# wechat-archive-playbook

**A local-first playbook and toolkit for archiving personal chat history** — SQLCipher 4 decryption · ZSTD content decoding · Markdown export

> 中文说明见 [README.md](README.md)。

## What this is

A **reproducible end-to-end playbook plus process scripts**: take the encrypted
sharded databases of a local instant-messaging client (Windows 4.x architecture),
decrypt them, decode the message bodies, and export everything into Markdown
files named by their exact send timestamps.

It is deliberately **not** a turnkey cracking tool:

- **No key-extraction code is included.** Keys are supplied by the user; the
  toolkit starts at "you already hold the key" — no memory scanning, no
  process instrumentation, no version-specific offsets;
- Every script is fully parameterized: no hardcoded account IDs, absolute
  paths, PIDs, or memory addresses;
- All private artifacts (key files, decrypted databases, diary exports) are
  excluded via `.gitignore`.

Because of that boundary, this repo is safe to publish, cite, and hand to
other agents: `src/` is clean data-interop code (aligned with the public
SQLCipher specification), and `docs/` is the methodology to reproduce the
whole pipeline.

## Features

- **SQLCipher 4 page-level decryption**: HMAC-SHA512 pre-verification
  (a wrong key never produces a garbage output file), per-page AES-256-CBC,
  automatic salt→key matching across sharded databases
- **Transparent ZSTD decoding**: magic-number detection, decompression,
  UTF-8/GBK fallback
- **XML payload cleaning**: shared links, file attachments and image
  placeholders rendered as readable Markdown
- **Timestamp-based archiving**: per-second file naming plus a consolidated
  document grouped by date
- **Session table resolution**: the `Msg_ + md5(session id)` rule and
  cross-shard merging

## Quick start

```bash
pip install -r requirements.txt

# 0. Self-test: build an encrypted db -> decrypt -> byte-exact round-trip
#    (no real data needed)
python tests/selftest.py

# 1. Verify a key matches a database (no output file written)
python -m src.cli verify --db message_0.db --key <64-hex>

# 2. Batch-decrypt every sharded database in a directory
python -m src.cli decrypt --dir ./db_storage --key-file keys.txt

# 3. Export a session to Markdown (files named by exact send time)
python -m src.cli export --dir ./decrypted_dbs --table Msg_<md5> \
    --keyword "a phrase from the first message" \
    --out ./export --consolidated ./archive.md
```

Full walkthrough, directory layout and table-name computation:
[docs/03-全链路流程.md](docs/03-全链路流程.md) (Chinese).

## Documentation index

| Document | Contents |
|----------|----------|
| [docs/01-存储架构.md](docs/01-存储架构.md) | Storage layout, encrypted file header, ZSTD, `Msg_<md5>` session-table rule (ZH) |
| [docs/02-密钥机制.md](docs/02-密钥机制.md) | SQLCipher 4 key derivation, salt→key mapping, user-supplied-key boundary (ZH) |
| [docs/03-全链路流程.md](docs/03-全链路流程.md) | Five-step runbook: backup → decrypt → locate → export (ZH) |
| [docs/04-排障与版本适配.md](docs/04-排障与版本适配.md) | 3.x→4.x differences, failure modes, offset-free adaptation method (ZH) |
| [USE_POLICY.md](USE_POLICY.md) | Use boundary and disclaimer (ZH) |
| [SKILL.md](SKILL.md) | Agent-facing skill description (ZH) |

## Repository layout

```
wechat-archive-playbook/
├── src/                    # Toolkit (no privacy hardcoding, version-agnostic)
│   ├── sqlcipher4.py       #   SQLCipher 4 decryption & key verification
│   ├── content.py          #   ZSTD decoding + XML payload cleaning
│   ├── exporter.py         #   Markdown exporter
│   └── cli.py              #   Command-line entry
├── docs/                   # Methodology (Chinese)
├── examples/               # Desensitized sample output
├── tests/selftest.py       # End-to-end self-test (build->decrypt->byte-exact round-trip)
├── USE_POLICY.md           # Use boundary (ZH)
├── SKILL.md                # Agent entry point (ZH)
└── requirements.txt
```

## Use boundary

For archiving **your own data on your own device** only.
See [USE_POLICY.md](USE_POLICY.md). This project does not provide, contain,
or intend to provide key extraction from, or access-control circumvention of,
any commercial software.

## License

MIT — see [LICENSE](LICENSE).
