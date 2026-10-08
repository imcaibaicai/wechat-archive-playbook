"""
exporter.py — 把解密数据库中的会话消息导出为 Markdown 归档。

特性：
  - 跨多个分片 .decrypted.db 收集同一张会话表的消息
  - 可按起始关键词 / 起始时间戳截取
  - 每条消息导出为独立文件，文件名 = 具体发送时间
  - 同时生成按日期分组的汇总文档
"""

import os
import sqlite3
from datetime import datetime

try:  # 包内运行（python -m src.cli）
    from .content import clean_message_content, safe_decode
except ImportError:  # 扁平脚本运行（python scripts/cli.py）
    from content import clean_message_content, safe_decode  # type: ignore

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def collect_messages(decrypted_dir: str, table: str) -> list[dict]:
    """扫描目录下所有 .decrypted.db，汇总指定会话表的全部消息。"""
    messages = []
    for name in sorted(os.listdir(decrypted_dir)):
        if not name.endswith(".decrypted.db"):
            continue
        conn = sqlite3.connect(os.path.join(decrypted_dir, name))
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        if not cur.fetchone():
            conn.close()
            continue
        cur.execute(
            f"SELECT local_id, create_time, local_type, message_content FROM {table}"
        )
        for local_id, ctime, mtype, content in cur.fetchall():
            dt = datetime.fromtimestamp(ctime) if ctime > 0 else datetime.fromtimestamp(0)
            messages.append({
                "db": name,
                "local_id": local_id,
                "create_time": ctime,
                "datetime": dt,
                "type": mtype,
                "raw_text": safe_decode(content).strip(),
            })
        conn.close()
    messages.sort(key=lambda m: m["create_time"])
    return messages


def slice_from(messages: list[dict], keyword: str | None = None,
               since_ts: int | None = None) -> list[dict]:
    """按起始关键词或起始时间戳截取子集。"""
    if keyword:
        for i, m in enumerate(messages):
            if keyword in m["raw_text"]:
                return messages[i:]
        raise ValueError(f"keyword not found: {keyword!r}")
    if since_ts is not None:
        return [m for m in messages if m["create_time"] >= since_ts]
    return messages


def export(messages: list[dict], output_dir: str, consolidated_path: str | None = None) -> list[str]:
    """逐条导出独立 md 文件（按发送秒级时间命名），可选生成汇总文档。"""
    os.makedirs(output_dir, exist_ok=True)
    used: dict[str, int] = {}
    exported = []

    for idx, m in enumerate(messages):
        dt = m["datetime"]
        base = dt.strftime("%Y-%m-%d_%H-%M-%S")
        count = used.get(base, 0)
        used[base] = count + 1
        fname = f"{base}_{count}.md" if count else f"{base}.md"
        body = clean_message_content(m["type"], m["raw_text"])
        with open(os.path.join(output_dir, fname), "w", encoding="utf-8") as f:
            f.write(
                f"# 记录 - {dt.strftime('%Y年%m月%d日 %H:%M:%S')}\n\n"
                f"- **发送时间**：`{dt.strftime('%Y-%m-%d %H:%M:%S')}`\n"
                f"- **序号**：第 {idx + 1} 条 (本地 ID: `{m['local_id']}`)\n"
                f"- **来源分库**：`{m['db']}`\n\n---\n\n{body}\n"
            )
        exported.append(fname)

    print(f"[exporter] {len(exported)} files -> {output_dir}")

    if consolidated_path and messages:
        first, last = messages[0]["datetime"], messages[-1]["datetime"]
        with open(consolidated_path, "w", encoding="utf-8") as f:
            f.write(
                f"# 归档汇总\n\n"
                f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n"
                f"> 记录总数：{len(messages)} 条  \n"
                f"> 时间跨度：`{first.strftime('%Y-%m-%d %H:%M:%S')}` 至 "
                f"`{last.strftime('%Y-%m-%d %H:%M:%S')}`\n\n---\n"
            )
            cur_date = ""
            for idx, m in enumerate(messages):
                ds = m["datetime"].strftime("%Y-%m-%d")
                if ds != cur_date:
                    cur_date = ds
                    f.write(f"\n## {ds} ({WEEKDAYS[m['datetime'].weekday()]})\n\n")
                f.write(f"### {m['datetime'].strftime('%H:%M:%S')} (#{idx + 1})\n\n")
                f.write(f"{clean_message_content(m['type'], m['raw_text'])}\n\n---\n\n")
        print(f"[exporter] consolidated -> {consolidated_path}")
    return exported
