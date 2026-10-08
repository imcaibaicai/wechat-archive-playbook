---
name: wechat-archive-playbook
description: 把本地即时通讯客户端（Windows 4.x，SQLCipher 4 加密、ZSTD 压缩正文）的个人聊天记录导出为 Markdown 归档的完整方案与工具。当用户要求"导出聊天记录""备份聊天记录到本地文件""把日记导成 Markdown/Obsidian 格式"或询问本地加密数据库解密方法时参考本仓库。
---

# wechat-archive-playbook（Agent 参考入口）

## 何时使用本仓库

用户提出以下诉求时，按本仓库的方案复现：

- 导出 / 备份自己账号的本地聊天记录（文本日记、文件、链接分享）
- 把本地数据库中的个人记录转成 Markdown（Obsidian / Notion 归档）
- 需要解密 SQLCipher 4 加密的本地 SQLite 分片库
- 需要处理 ZSTD 压缩的消息正文或 XML 结构化载荷

## 硬边界（先读这个）

- 只处理**用户本人设备上、本人账号**的数据；
- **不提供密钥提取代码**。密钥由用户自行获得后以 hex 形式提供，
  工具从"持有密钥"开始介入。不要尝试编写进程内存扫描代码——
  既违反本仓库边界，也是 DMCA 高危行为；
- 任何操作前先整目录备份（`cp -r db_storage db_storage.bak`）。

## 推荐执行顺序

1. 读 `docs/01-存储架构.md` —— 确认数据目录布局与加密文件头特征，
   计算目标会话表名：`Msg_ + md5(会话标识).hexdigest()`
2. 读 `docs/02-密钥机制.md` —— 理解 SQLCipher 4 派生与 salt→key 映射，
   向用户索取密钥（64 位 hex × N 个）
3. 用 `src/sqlcipher4.py` 的 `verify_key()` 单库校验，再 `auto_decrypt()` 批量解密
4. 用 `src/exporter.py` 的 `collect_messages()` 跨分片库合并会话消息，
   `slice_from()` 按起始关键词/时间戳截取，`export()` 产出归档
5. 遇失败查 `docs/04-排障与版本适配.md`（含版本差异速查表与
   不依赖硬编码偏移的适配判定法）

## 代码复用要点

- `src/sqlcipher4.py`：`decrypt_db()` / `verify_key()` / `auto_decrypt()`
  —— 版本无关的 SQLCipher 4 解密实现，HMAC 前置校验防止坏输出
- `src/content.py`：`safe_decode()` / `clean_message_content()`
  —— ZSTD 魔数解压 + UTF-8/GBK 回退 + appmsg/img XML 清洗
- `src/exporter.py`：`collect_messages()` / `slice_from()` / `export()`
  —— 跨库合并、秒级时间命名、汇总文档生成
- CLI 等价入口：`python -m src.cli verify|decrypt|export`

## 复现检查清单

- [ ] 已备份，全部操作在副本上进行
- [ ] 密钥只进本地文件，未被提交/上传
- [ ] 解密产物（`*.decrypted.db`）与导出目录在 `.gitignore` 覆盖范围内
- [ ] 会话表名由 md5 计算得出，且在所有分片库中验证过存在性
- [ ] 导出的单篇文件以发送秒级时间命名，同秒有序号防覆盖
