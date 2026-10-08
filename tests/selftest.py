"""
selftest.py — 不依赖任何真实数据的端到端自检。

流程：按 SQLCipher 4 公开规范构造一个"加密数据库" ->
用 sqlcipher4.decrypt_db 解密 -> 逐字节比对还原结果；
另覆盖 verify_key 正/误密钥、ZSTD 解码、XML 清洗。

运行：python tests/selftest.py
"""

import hashlib
import hmac
import os
import sqlite3
import sys
import tempfile

_here = os.path.dirname(os.path.abspath(__file__))
# 兼容两种布局：仓库内 tests/ 对 src/，skill 内 tests/ 对 scripts/
for _cand in (os.path.join(_here, "..", "src"), os.path.join(_here, "..", "scripts")):
    if os.path.isdir(_cand):
        sys.path.insert(0, os.path.abspath(_cand))
        break

from Crypto.Cipher import AES  # noqa: E402

import content  # noqa: E402
import sqlcipher4  # noqa: E402

KEY = bytes.fromhex("00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff")


def make_plain_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE t(a TEXT, b INTEGER)")
    conn.executemany("INSERT INTO t VALUES(?, ?)",
                     [("hello 你好", 1), ("zstd-magic-test", 2), ("row3", 3)])
    conn.commit()
    conn.close()


def encrypt_as_sqlcipher4(plain_path: str, out_path: str) -> list[bytes]:
    """
    按 docs/02 的公开规范把明文 SQLite 写成 SQLCipher 4 容器：
      文件    = salt(16) + [ct(4000) + iv(16) + mac(64)] + [ct(4016) + iv + mac] + ...
      ct(4000)= AES(明文页1 的 [16:4016]，即头部 16 字节被 salt 顶替)
      ct(4016)= AES(明文页N 的 [0:4016]，SQLite 视角可用页长)
      mac     = HMAC(ct || iv || pgno 小端 4 字节)
    返回每页的 reserve 区（iv+mac）列表，供期望值计算。
    """
    with open(plain_path, "rb") as f:
        blob = f.read()
    salt = os.urandom(16)
    mac_salt = bytes(x ^ 0x3A for x in salt)
    mac_key = hashlib.pbkdf2_hmac("sha512", KEY, mac_salt, 2, 32)

    reserves: list[bytes] = []
    out = bytearray(salt)

    def emit(region: bytes, pgno: int) -> None:
        iv = os.urandom(16)
        ct = AES.new(KEY, AES.MODE_CBC, iv).encrypt(region)
        mac = hmac.new(mac_key, digestmod="sha512")
        # SQLCipher 默认按本机字节序拼页码；x86/x64 为小端
        mac.update(ct + iv + pgno.to_bytes(4, "little"))
        reserves.append(iv + mac.digest())
        out.extend(ct + reserves[-1])

    npages = max(1, (len(blob) + 4095) // 4096)
    emit(blob[16:4016].ljust(4000, b"\x00"), 1)          # 页1：跳过头部 16 字节
    for pgno in range(2, npages + 1):
        start = (pgno - 1) * 4096
        emit(blob[start:start + 4016].ljust(4016, b"\x00"), pgno)
    with open(out_path, "wb") as f:
        f.write(bytes(out))
    return reserves


def expected_plaintext(plain_path: str, reserves: list[bytes]) -> bytes:
    """按上述布局推算 decrypt_db 应输出的字节：页1 = 头部16 + 明文[16:4016] + reserve。"""
    with open(plain_path, "rb") as f:
        blob = f.read()
    npages = max(1, (len(blob) + 4095) // 4096)
    parts = [blob[0:4016], reserves[0]]
    for pgno in range(2, npages + 1):
        start = (pgno - 1) * 4096
        parts.append(blob[start:start + 4016])
        parts.append(reserves[pgno - 1])
    return b"".join(parts)


def main() -> int:
    failures = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        plain = os.path.join(tmp, "plain.db")
        enc = os.path.join(tmp, "enc.db")
        dec = os.path.join(tmp, "enc.decrypted.db")
        make_plain_db(plain)
        encrypt_as_sqlcipher4(plain, enc)

        print("[1] SQLCipher 4 round-trip")
        reserves = encrypt_as_sqlcipher4(plain, enc)
        result = sqlcipher4.decrypt_db(enc, KEY, dec)
        check("decrypt_db returns output path", result == dec)
        if result:
            with open(dec, "rb") as f:
                got = f.read()
            want = expected_plaintext(plain, reserves)
            check("decrypted bytes == expected plaintext", got == want,
                  f"{len(got)} bytes")
            check("output starts with SQLite magic",
                  got[:16] == b"SQLite format 3\x00")

        print("[2] key verification")
        check("correct key verifies", sqlcipher4.verify_key(enc, KEY))
        wrong = bytes(32)
        check("wrong key rejected", not sqlcipher4.verify_key(enc, wrong))
        bad_out = os.path.join(tmp, "bad.decrypted.db")
        check("decrypt with wrong key returns None",
              sqlcipher4.decrypt_db(enc, wrong, bad_out) is None
              and not os.path.exists(bad_out))

        print("[3] content decoding")
        import zstandard
        compressed = zstandard.ZstdCompressor().compress("日记正文 test 123".encode())
        check("zstd round-trip",
              content.safe_decode(compressed) == "日记正文 test 123")
        check("plain utf-8 passthrough",
              content.safe_decode("你好".encode()) == "你好")
        xml = ('<msg><appmsg><title>示例文章</title><des>摘要</des>'
               '<url>https://example.com</url></appmsg></msg>')
        cleaned = content.clean_message_content(49, xml)
        check("appmsg xml cleaned", "示例文章" in cleaned and "example.com" in cleaned)
        img = '<msg><img md5="abcdef0123456789"/></msg>'
        check("img placeholder", content.clean_message_content(3, img).startswith("[图片消息"))

    print()
    if failures:
        print(f"SELFTEST FAILED: {len(failures)} check(s): {failures}")
        return 1
    print("SELFTEST PASSED: all checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
