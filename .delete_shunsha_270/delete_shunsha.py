# -*- coding: utf-8 -*-
"""注销站点「瞬杀一波」：sites.json 去登记 + recent_10_cache.json 去条目 + 270 失败清单去该行。

只动这三处，其余站点/期数逐字节不动；改动前原样备份到 .delete_shunsha_270\before\。
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\Desktop\每天工具\爬虫合集")
SHA = ROOT / "杀一波"
SITES = SHA / "sites.json"
CACHE = SHA / "recent_10_cache.json"
FAIL = ROOT / "七类数据统一归纳失败" / "270期-杀一波-失败.txt"
AUDIT = SHA / ".delete_shunsha_270"
BK = AUDIT / "before"
BK.mkdir(parents=True, exist_ok=True)

NAME = "瞬杀一波"
URL = "https://43666.886677a.app:2563/htm/bbs/top070.html"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def backup(path: Path) -> str:
    shutil.copy2(path, BK / path.name)
    return sha256(path.read_bytes())


print("=== 改动前 ===")
before = {}
for path in (SITES, CACHE, FAIL):
    before[path.name] = (path.stat().st_size, backup(path))
    print(f"{path.name}: {before[path.name][0]}B sha256 {before[path.name][1]}")

# 1) sites.json：删掉整条站点对象（含行尾逗号，保持其余格式/顺序）
block_sites = (
    '  {\r\n'
    f'    "name": "{NAME}",\r\n'
    f'    "url": "{URL}",\r\n'
    '    "pick": "bottom"\r\n'
    '  },\r\n'
).encode("utf-8")
sites_bytes = SITES.read_bytes()
assert sites_bytes.count(block_sites) == 1, f"sites 块匹配数={sites_bytes.count(block_sites)}"
atomic_write_bytes(SITES, sites_bytes.replace(block_sites, b""))

# 2) recent_10_cache.json：删掉该站条目（data 本就是 {}）
block_cache = (
    f'    "{NAME}": {{\r\n'
    f'      "url": "{URL}",\r\n'
    '      "pick": "bottom",\r\n'
    '      "data": {},\r\n'
    f'      "name": "{NAME}"\r\n'
    '    },\r\n'
).encode("utf-8")
cache_bytes = CACHE.read_bytes()
assert cache_bytes.count(block_cache) == 1, f"缓存块匹配数={cache_bytes.count(block_cache)}"
atomic_write_bytes(CACHE, cache_bytes.replace(block_cache, b""))

# 3) 270 失败清单：删掉该站行及其前导空行（只留仍未解决的 软妹味道）
fail_line = (
    f"{NAME} {URL} 失败原因: 未匹配到{NAME}专属解析格式: 期号下一行颜色\r\n"
).encode("utf-8")
fail_bytes = FAIL.read_bytes()
pattern = b"\r\n\r\n" + fail_line
assert fail_bytes.count(pattern) == 1, f"失败行匹配数={fail_bytes.count(pattern)}"
new_fail = fail_bytes.replace(pattern, b"\r\n")
atomic_write_bytes(FAIL, new_fail)

# 4) 校验
print("=== 改动后 ===")
sites = json.loads(SITES.read_text(encoding="utf-8"))
cache = json.loads(CACHE.read_text(encoding="utf-8"))
checks = []
checks.append(("sites.json 可解析且站点数 113→112", len(sites) == 112, f"{len(sites)} 站"))
checks.append((f"sites.json 无 {NAME}", all(s["name"] != NAME for s in sites), ""))
checks.append(("缓存站点数 113→112", len(cache["sites"]) == 112, f"{len(cache['sites'])} 站"))
checks.append((f"缓存无 {NAME}", NAME not in cache["sites"], ""))
checks.append(("失败清单只剩 软妹味道 一行", new_fail.count(b"\r\n") == 1 and new_fail.startswith(b"\xe8\xbd\xaf"), repr(new_fail[:40])))

sys.path.insert(0, str(SHA))
import sha_yibo_crawler as crawler  # noqa: E402

loaded = crawler.load_sites(SITES)
checks.append(("crawler.load_sites 得到 112 站", len(loaded) == 112, f"{len(loaded)} 站"))
checks.append((f"load_sites 不含 {NAME}", all(s.name != NAME for s in loaded), ""))

# 缓存合并路径真实跑一遍（写临时副本，不碰真实缓存）：确认 112 站且无该站
tmpdir = Path(tempfile.mkdtemp(prefix="cachecheck_"))
tmp_cache = tmpdir / "recent_10_cache.json"
shutil.copy2(CACHE, tmp_cache)
crawler.update_recent_cache(tmp_cache, 270, loaded, [], keep=10)
merged = json.loads(tmp_cache.read_text(encoding="utf-8"))
checks.append(("update_recent_cache 后仍 112 站且无该站",
               len(merged["sites"]) == 112 and NAME not in merged["sites"],
               f"{len(merged['sites'])} 站 / periods {len(merged['periods'])}"))
shutil.rmtree(tmpdir, ignore_errors=True)

for name, ok, extra in checks:
    print(("  [OK]   " if ok else "  [FAIL] ") + name + (f"  ({extra})" if extra else ""))
assert all(ok for _, ok, _ in checks), "校验未通过"

print("=== 文件哈希 ===")
for path in (SITES, CACHE, FAIL):
    data = path.read_bytes()
    print(f"{path.name}: {len(data)}B sha256 {sha256(data)}  (改动前 {before[path.name][0]}B {before[path.name][1]})")
print("=== 未改动确认 ===")
crawler_file = SHA / "sha_yibo_crawler.py"
print(f"sha_yibo_crawler.py: {crawler_file.stat().st_size}B sha256 {sha256(crawler_file.read_bytes())}")
print(f"备份目录: {BK}")
