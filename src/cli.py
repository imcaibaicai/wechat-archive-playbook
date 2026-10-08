"""
cli.py — 命令行入口。

用法示例：
  # 1) 校验单个密钥是否匹配某数据库（不写盘）
  python -m src.cli verify --db message_0.db --key <64位hex>

  # 2) 批量解密：密钥来自文件（每行一个 64 位 hex）或命令行
  python -m src.cli decrypt --dir ./db_storage --key-file keys.txt

  # 3) 导出：指定会话表，可按起始关键词 / 起始时间戳截取
  python -m src.cli export --dir ./decrypted_dbs --table Msg_<md5> \
      --keyword "某段起始文本" --out ./export --consolidated ./汇总.md

会话表名规则见 docs/01-存储架构.md（表名 = "Msg_" + 会话标识的 MD5）。
"""

import argparse
import sys

from . import exporter, sqlcipher4


def load_keys(args) -> list[str]:
    keys: list[str] = []
    if args.key_file:
        with open(args.key_file, encoding="utf-8") as f:
            keys += [ln.strip() for ln in f if ln.strip()]
    if args.keys:
        keys += [k.strip() for k in args.keys.split(",") if k.strip()]
    return keys


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="wechat-archive-playbook",
                                description="本地加密数据库解密与 Markdown 归档工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("verify", help="校验密钥是否匹配某数据库")
    pv.add_argument("--db", required=True)
    pv.add_argument("--key", required=True, help="64 位 hex 密钥")

    pd = sub.add_parser("decrypt", help="批量解密目录下的加密数据库")
    pd.add_argument("--dir", required=True, help="加密数据库所在目录")
    pd.add_argument("--key-file", help="密钥文件，每行一个 hex")
    pd.add_argument("--keys", help="逗号分隔的 hex 密钥列表")

    pe = sub.add_parser("export", help="导出会话消息为 Markdown")
    pe.add_argument("--dir", required=True, help="解密后数据库目录")
    pe.add_argument("--table", required=True, help="会话表名，如 Msg_<md5>")
    pe.add_argument("--keyword", help="从包含该关键词的消息起导出")
    pe.add_argument("--since", type=int, help="从该 Unix 时间戳（秒）起导出")
    pe.add_argument("--out", required=True, help="独立文件输出目录")
    pe.add_argument("--consolidated", help="汇总文档输出路径")

    args = p.parse_args(argv)

    if args.cmd == "verify":
        ok = sqlcipher4.verify_key(args.db, bytes.fromhex(args.key))
        print("[verify] key MATCH" if ok else "[verify] key mismatch")
        return 0 if ok else 1

    if args.cmd == "decrypt":
        keys = load_keys(args)
        if not keys:
            print("error: 需要 --key-file 或 --keys 提供至少一个密钥", file=sys.stderr)
            return 2
        sqlcipher4.auto_decrypt(args.dir, keys)
        return 0

    if args.cmd == "export":
        msgs = exporter.collect_messages(args.dir, args.table)
        if not msgs:
            print(f"error: 在 {args.dir} 的表 {args.table} 中没有消息", file=sys.stderr)
            return 2
        msgs = exporter.slice_from(msgs, keyword=args.keyword, since_ts=args.since)
        exporter.export(msgs, args.out, args.consolidated)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
