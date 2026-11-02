# -*- coding: utf-8 -*-
"""杀一波 281 期「重复站」封存：用户点名封存 12 站（每组缓存近 10 期与其保留站逐期完全一致）。

落盘：
1) sites.json：按原始文本块精确删除这 12 条（不重排、不改行尾、不动其他条目）
2) recent_10_cache.json：按原始文本块精确删除这 12 条（其余条目/期号/updated_at 逐字节不动）
3) archived_sites.json：新建可恢复封存清单（原始字段 + archive_tag + duplicate_of + 封存时缓存快照）
4) 改动前原样备份到 .archive_dupgroups_281/before/

所有断言失败即中止（文本级校验 + 结构级校验 + 爬虫自身加载/合并路径校验）。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHA = HERE.parent
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c  # noqa: E402

SITES = SHA / "sites.json"
CACHE = SHA / "recent_10_cache.json"
ARCHIVE = SHA / "archived_sites.json"
BK = HERE / "before"
BK.mkdir(parents=True, exist_ok=True)

TARGETS = {
    "长乐未央": "婷容修态",
    "六彩圣君": "婷容修态",
    "身强体壮": "婷容修态",
    "平特网": "井井有条",
    "踏雪": "井井有条",
    "窃窃私语": "远赴相思",
    "自强不息": "远赴相思",
    "金吊桶": "广东八二站",
    "二肖四码": "无视一切",
    "玄机阁": "玄机",
    "红姐论坛": "目瞪口呆",
    "白虎": "鸿运",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def backup(path: Path) -> tuple[int, str]:
    if not (BK / path.name).exists():
        shutil.copy2(path, BK / path.name)
    data = path.read_bytes()
    return len(data), sha256(data)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    tmp = path.parent / ("." + path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def json_object_block(text: str, key_prefix: str) -> str:
    """抽取对象起始行（含该行前导缩进）到对象结束（含尾随逗号与换行）的原文块。

    key_prefix 用于定位对象；开括号可能与本行同排（cache 的 `    "名称": {`），
    也可能在上一行（sites.json 的 `  {\\r\\n    "name": ...`），两种都要支持。
    返回前断言块内确实包含 key_prefix，避免抽到相邻条目。
    """
    start = text.index(key_prefix)
    line_end = text.find("\n", start)
    if "{" in text[start:line_end]:
        brace = text.index("{", start)
        obj_start = text.rfind("\n", 0, brace) + 1
    else:
        brace = text.rfind("{", 0, start)
        assert brace != -1, f"找不到对象开括号: {key_prefix}"
        obj_start = text.rfind("\n", 0, brace) + 1
        assert text[obj_start : brace + 1].strip() == "{", repr(text[obj_start : brace + 1])
    depth = 0
    i = brace
    while True:
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    j = i + 1
    if text.startswith(",", j):
        j += 1
    if text.startswith("\r\n", j):
        j += 2
    elif text.startswith("\n", j):
        j += 1
    block = text[obj_start:j]
    assert key_prefix in block, f"抽取块不含关键字: {key_prefix!r} -> {block[:80]!r}"
    return block


def strip_comma_before_close(text: str) -> tuple[str, tuple[str, str] | None]:
    """若闭合括号前残留逗号则删除；返回(新文本, (旧行, 新行) 或 None)。"""
    idx = text.rfind("]")
    k = idx - 1
    while text[k] in " \r\n":
        k -= 1
    if text[k] != ",":
        return text, None
    line_start = text.rfind("\n", 0, k) + 1
    line_end = text.find("\n", k)
    old_line = text[line_start:line_end].rstrip("\r\n")
    new_text = text[:k] + text[k + 1 :]
    new_line = new_text[line_start:line_end].rstrip("\r\n")
    return new_text, (old_line, new_line)


print("=== 改动前 ===")
before = {p.name: backup(p) for p in (SITES, CACHE)}
for name, (size, digest) in before.items():
    print(f"{name}: {size}B sha256 {digest}")

sites_text = SITES.read_bytes().decode("utf-8")
cache_text = CACHE.read_bytes().decode("utf-8")
sites = json.loads(sites_text)
cache = json.loads(cache_text)
assert len(sites) == 112, len(sites)
assert len(cache["sites"]) == 112, len(cache["sites"])

# --- 0) 断言：目标存在且唯一；封存站与其保留站缓存窗口逐期完全一致 ---
periods = [int(p) for p in cache["periods"]]
for name, partner in TARGETS.items():
    assert sum(1 for s in sites if s["name"] == name) == 1, f"sites.json 中 {name} 不唯一"
    assert name in cache["sites"], f"缓存缺 {name}"
    assert partner in cache["sites"], f"缓存缺保留站 {partner}"
    assert partner not in TARGETS, f"保留站 {partner} 也在封存名单"
    ad = {int(k): v for k, v in cache["sites"][name]["data"].items()}
    pd = {int(k): v for k, v in cache["sites"][partner]["data"].items()}
    assert all(p in ad for p in periods), f"{name} 缓存窗口不齐"
    assert all(p in pd for p in periods), f"{partner} 缓存窗口不齐"
    assert [ad[p] for p in periods] == [pd[p] for p in periods], f"{name} 与 {partner} 并非逐期完全一致"
print(f"窗口 {periods[0]}→{periods[-1]}：{len(TARGETS)} 站与其保留站逐期完全一致 ✓")

# --- 1) sites.json：精确文本块删除 ---
removed_site_blocks: list[str] = []
sites_after = sites_text
for name in TARGETS:
    block = json_object_block(sites_text, f'    "name": "{name}",')
    assert sites_after.count(block) == 1, f"sites.json {name} 块匹配数={sites_after.count(block)}"
    sites_after = sites_after.replace(block, "", 1)
    removed_site_blocks.append(block)
sites_after, site_comma_fix = strip_comma_before_close(sites_after)
sites_after_bytes = sites_after.encode("utf-8")

sites_new = json.loads(sites_after)
assert len(sites_new) == 100, len(sites_new)
assert [s["name"] for s in sites_new] == [s["name"] for s in sites if s["name"] not in TARGETS], "顺序或内容变化"
for s in sites:
    if s["name"] not in TARGETS:
        assert s in sites_new, f"未封存站点内容变化: {s['name']}"

# --- 2) recent_10_cache.json：精确文本块删除 ---
removed_cache_blocks: list[str] = []
cache_after = cache_text
for name in TARGETS:
    block = json_object_block(cache_text, f'    "{name}": {{')
    assert cache_after.count(block) == 1, f"缓存 {name} 块匹配数={cache_after.count(block)}"
    cache_after = cache_after.replace(block, "", 1)
    removed_cache_blocks.append(block)
cache_after, cache_comma_fix = strip_comma_before_close(cache_after)
cache_after_bytes = cache_after.encode("utf-8")

cache_new = json.loads(cache_after)
expected_cache = {
    "updated_at": cache["updated_at"],
    "periods": cache["periods"],
    "sites": {k: v for k, v in cache["sites"].items() if k not in TARGETS},
}
assert cache_new == expected_cache, "缓存结构校验失败"
assert list(cache_new["sites"]) == [k for k in cache["sites"] if k not in TARGETS], "缓存站点顺序变化"
assert len(cache_new["sites"]) == 100, len(cache_new["sites"])

# 文本级校验：除这 12 个块（+至多一处尾逗号修正）外无任何改动
for label, old_text, new_text, blocks, fix in (
    ("sites.json", sites_text, sites_after, removed_site_blocks, site_comma_fix),
    ("cache", cache_text, cache_after, removed_cache_blocks, cache_comma_fix),
):
    removed = Counter(old_text.split("\r\n")) - Counter(new_text.split("\r\n"))
    added = Counter(new_text.split("\r\n")) - Counter(old_text.split("\r\n"))
    allowed_removed = Counter()
    for b in blocks:
        allowed_removed.update(b.rstrip("\r\n").split("\r\n") if b.endswith("\r\n") else b.split("\r\n"))
    if fix is not None:
        allowed_removed.update([fix[0]])
    unexpected_removed = removed - allowed_removed
    added_allowed = Counter({fix[1]: 1}) if fix is not None else Counter()
    unexpected_added = added - added_allowed
    assert not unexpected_removed, f"{label} 计划外删除: {list(unexpected_removed)[:5]}"
    assert not unexpected_added, f"{label} 计划外新增: {list(unexpected_added)[:5]}"
    print(f"{label}: 删除 {sum(removed.values())} 行（计划外 0）；新增 {sum(added.values())} 行（尾逗号修正 {fix})")

# --- 3) 写盘 ---
atomic_write_bytes(SITES, sites_after_bytes)
atomic_write_bytes(CACHE, cache_after_bytes)

if ARCHIVE.exists():
    archived = json.loads(ARCHIVE.read_text(encoding="utf-8"))
else:
    archived = {
        "archived_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "reason": "用户点名封存：缓存近 10 期与保留站逐期完全一致（重复站），不再抓取/不写入/不更新缓存",
        "period_window": periods,
        "sites": [],
    }
existing = {item["name"] for item in archived["sites"]}
for name, partner in TARGETS.items():
    assert name not in existing, f"封存清单已存在 {name}"
    entry = dict(next(s for s in sites if s["name"] == name))
    entry["archive_tag"] = f"dup-of:{partner}"
    entry["duplicate_of"] = partner
    entry["archived_period"] = periods[0]
    entry["cache_data"] = dict(cache["sites"][name]["data"])
    archived["sites"].append(entry)
ARCHIVE.write_text(json.dumps(archived, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
print(f"封存清单 {ARCHIVE.name}: {len(archived['sites'])} 条")

# --- 4) 终态校验（含爬虫自身加载/缓存合并路径） ---
loaded = c.load_sites(SITES)
assert len(loaded) == 100, len(loaded)
assert not ({s.name for s in loaded} & set(TARGETS)), "load_sites 仍含封存站"
cache_final = json.loads(CACHE.read_text(encoding="utf-8"))
for name in TARGETS:
    assert name not in cache_final["sites"], name
assert cache_final["periods"] == cache["periods"], "期号变化"
assert cache_final["updated_at"] == cache["updated_at"], "updated_at 变化"
for name, entry in cache["sites"].items():
    if name not in TARGETS:
        assert cache_final["sites"][name] == entry, f"未封存站点缓存变化: {name}"

tmpdir = Path(tempfile.mkdtemp(prefix="archive_cachecheck_"))
tmp_cache = tmpdir / "recent_10_cache.json"
shutil.copy2(CACHE, tmp_cache)
c.update_recent_cache(tmp_cache, periods[0], loaded, [], keep=10)
merged = json.loads(tmp_cache.read_text(encoding="utf-8"))
assert len(merged["sites"]) == 100 and not (set(merged["sites"]) & set(TARGETS)), "合并路径仍带封存站"
assert merged["periods"] == cache["periods"], "合并后期号变化"
shutil.rmtree(tmpdir, ignore_errors=True)

after = {p.name: (p.stat().st_size, sha256(p.read_bytes())) for p in (SITES, CACHE)}
print("=== 改动后 ===")
for name, (size, digest) in after.items():
    print(f"{name}: {size}B sha256 {digest}  (改动前 {before[name][0]}B {before[name][1]})")
print("archived_sites.json:", ARCHIVE.stat().st_size, "B")
print(f"站点 112 → 100；缓存站点 112 → 100；期号 {cache['periods'][0]}→{cache['periods'][-1]} 未变")
print("全部断言通过")
