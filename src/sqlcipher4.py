"""
sqlcipher4.py — SQLCipher 4 加密数据库的页面级解密与密钥校验。

适用场景：本地 SQLite 数据库采用 SQLCipher 4 加密
（AES-256-CBC + HMAC-SHA512，page size 4096，reserve 80 字节）。

前提：调用方已经合法持有目标数据库的密钥（hex 字符串）。
本模块只负责"给定密钥 -> 解密/校验"，不包含任何密钥获取逻辑。

算法依据 SQLCipher 4 公开规范（https://github.com/sqlcipher/sqlcipher）：
  - 文件头 16 字节为 salt
  - mac_salt  = salt XOR 0x3a
  - mac_key   = PBKDF2-HMAC-SHA512(key, mac_salt, rounds=2, dklen=32)
  - 每页尾部 reserve 区 = IV(16) + HMAC(64)，共 80 字节
  - 页面 1 前 16 字节明文为 "SQLite format 3\x00"
"""

import hashlib
import hmac
import os
import struct

from Crypto.Cipher import AES

KEY_SZ = 32
PAGE_SZ = 4096
SALT_SZ = 16
IV_SZ = 16
HMAC_SZ = 64
RESERVE_SZ = (IV_SZ + HMAC_SZ + 15) // 16 * 16  # = 80
SQLITE_FILE_HEADER = b"SQLite format 3\x00"


def _page_mac_ok(page: bytes, salt: bytes, rawkey: bytes, pgno: int = 1) -> bool:
    """
    校验某一页的 HMAC，用于在不写盘的情况下验证密钥是否正确。

    HMAC 输入 = ciphertext || IV || pgno(4 字节)。
    页码按 SQLCipher 默认的本机字节序拼接（x86/x64 为小端，
    见 sqlcipher.c sqlcipher_page_hmac）。本模块只校验页面 1。
    """
    mac_salt = bytes(x ^ 0x3A for x in salt)
    mac_key = hashlib.pbkdf2_hmac("sha512", rawkey, mac_salt, 2, KEY_SZ)
    mac = hmac.new(mac_key, digestmod="sha512")
    mac.update(page[:-RESERVE_SZ + IV_SZ])          # ciphertext + IV
    mac.update(struct.pack("<I", pgno))             # 小端页码
    return mac.digest() == page[-RESERVE_SZ + IV_SZ:][:HMAC_SZ]


def verify_key(db_path: str, rawkey: bytes) -> bool:
    """只校验密钥是否匹配该数据库，不产出解密文件。"""
    with open(db_path, "rb") as f:
        blob = f.read(PAGE_SZ)
    if len(blob) < PAGE_SZ:
        return False
    return _page_mac_ok(blob[SALT_SZ:PAGE_SZ], blob[:SALT_SZ], rawkey)


def decrypt_db(db_path: str, rawkey: bytes, output_path: str | None = None) -> str | None:
    """
    解密单个 SQLCipher 4 数据库为标准 SQLite 文件。

    :param db_path:     加密数据库路径
    :param rawkey:      32 字节原始密钥（bytes.fromhex(hex_key) 得到）
    :param output_path: 输出路径；缺省时把 xxx.db 写成 xxx.decrypted.db
    :return:            成功返回输出路径，密钥不匹配返回 None
    """
    if output_path is None:
        output_path = db_path[:-3] + ".decrypted.db" if db_path.endswith(".db") \
            else db_path + ".decrypted.db"

    with open(db_path, "rb") as f:
        blob = f.read()
    if len(blob) < PAGE_SZ:
        return None

    salt = blob[:SALT_SZ]
    page1 = blob[SALT_SZ:PAGE_SZ]
    if not _page_mac_ok(page1, salt, rawkey):
        return None

    pages = [page1] + [blob[i:i + PAGE_SZ] for i in range(PAGE_SZ, len(blob), PAGE_SZ)]
    with open(output_path, "wb") as f:
        f.write(SQLITE_FILE_HEADER)
        for page in pages:
            # 第 1 页盐后仅 4080 字节；末页可能不足一页，至少需 reserve + 一个密文块
            if len(page) < RESERVE_SZ + 16:
                break
            iv = page[-RESERVE_SZ:][:IV_SZ]
            cipher = page[:-RESERVE_SZ]
            f.write(AES.new(rawkey, AES.MODE_CBC, iv).decrypt(cipher))
            f.write(page[-RESERVE_SZ:])  # 原样保留 reserve 区（IV+HMAC）
    return output_path


def find_db_files(base_dir: str) -> list[str]:
    """递归收集目录下所有待解密的 .db 文件（跳过已解密产物）。"""
    out = []
    for root, _dirs, files in os.walk(base_dir):
        for name in files:
            if name.endswith(".db") and not name.endswith(".decrypted.db"):
                out.append(os.path.join(root, name))
    return out


def auto_decrypt(base_dir: str, keys_hex: list[str]) -> tuple[int, int]:
    """
    批量解密：对每个 .db 依次尝试 keys_hex 中的密钥，命中即写盘。

    多密钥是必需的——分片数据库可能各自持有独立 salt 与派生密钥，
    单密钥无法覆盖全部分库。
    """
    db_files = find_db_files(base_dir)
    print(f"[sqlcipher4] found {len(db_files)} encrypted database files")
    success = failed = 0
    for db_path in db_files:
        rel = os.path.relpath(db_path, base_dir)
        out_path = db_path[:-3] + ".decrypted.db"
        if os.path.exists(out_path):
            continue
        for hex_key in keys_hex:
            try:
                rawkey = bytes.fromhex(hex_key.strip())
            except ValueError:
                continue
            if len(rawkey) != KEY_SZ:
                continue
            if decrypt_db(db_path, rawkey, out_path):
                print(f"  [OK] {rel}")
                success += 1
                break
        else:
            print(f"  [FAIL] {rel}")
            failed += 1
    print(f"[sqlcipher4] done: {success} decrypted, {failed} failed")
    return success, failed
