"""
content.py — 消息内容解码：ZSTD 解压、编码回退、XML 载荷清洗。

解密后的数据库里，消息正文字段常见三种形态：
  1. ZSTD 压缩字节流（魔数 \\x28\\xb5\\x2f\\xfd）
  2. XML 结构化载荷（<appmsg> 分享/文件、<img> 图片占位）
  3. 纯 UTF-8 / GBK 文本
本模块把三种形态统一还原为可读字符串。
"""

import re
import xml.etree.ElementTree as ET

import zstandard

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
MAX_OUTPUT = 100 * 1024 * 1024


def decompress_zstd(data: bytes) -> bytes:
    """识别魔数并解压；非压缩数据原样返回。"""
    if not data or len(data) < 4 or data[:4] != ZSTD_MAGIC:
        return data
    try:
        return zstandard.ZstdDecompressor().decompress(data, max_output_size=MAX_OUTPUT)
    except Exception:
        return data


def safe_decode(data) -> str:
    """bytes -> str：先 ZSTD 解压，再 UTF-8，失败回退 GBK。"""
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, bytes):
        decompressed = decompress_zstd(data)
        for enc in ("utf-8", "gbk"):
            try:
                return decompressed.decode(enc)
            except UnicodeDecodeError:
                continue
    return ""


def clean_message_content(mtype: int, raw_text: str) -> str:
    """
    把原始消息文本清洗为 Markdown 友好的纯文本。

    :param mtype:    消息类型标识；1 一般为纯文本
    :param raw_text: safe_decode 之后的字符串
    """
    if not raw_text:
        return "[空消息]"
    if mtype == 1:
        return raw_text.strip()

    # 结构化 XML 载荷
    try:
        root = ET.fromstring(raw_text)
        appmsg = root.find(".//appmsg")
        if appmsg is not None:
            title = (appmsg.findtext("title") or "").strip()
            des = (appmsg.findtext("des") or "").strip()
            url = (appmsg.findtext("url") or "").strip()
            parts = []
            if title:
                parts.append(f"**[附件/链接]** {title}")
            if des and des != title:
                parts.append(f"> {des}")
            if url:
                parts.append(f"链接: {url}")
            return "\n\n".join(parts) if parts else "[分享/应用消息]"
        img = root.find(".//img")
        if img is not None:
            md5 = img.get("md5", "")
            info = f" (MD5: {md5[:8]}...)" if md5 else ""
            return f"[图片消息{info}]"
    except ET.ParseError:
        pass

    # 兜底：正则提取
    title_m = re.search(r"<title>(.*?)</title>", raw_text, re.S)
    if title_m:
        title = title_m.group(1).replace("&#x20;", " ")
        url_m = re.search(r"<url>(.*?)</url>", raw_text, re.S)
        url = url_m.group(1) if url_m else ""
        return f"**[附件/链接]** {title}" + (f"\n链接: {url}" if url else "")
    if "<img" in raw_text:
        return "[图片消息]"
    return raw_text.strip()
