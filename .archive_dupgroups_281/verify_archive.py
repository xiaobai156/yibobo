# -*- coding: utf-8 -*-
"""封存独立复验（只读）：以 .archive_dupgroups_281/before 为基准，核对现状与封存清单。

不写任何正式文件。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHA = HERE.parent
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c  # noqa: E402

BK = HERE / "before"
SITES = SHA / "sites.json"
CACHE = SHA / "recent_10_cache.json"
ARCHIVE = SHA / "archived_sites.json"

TARGETS = {
    "长乐未央": "婷容修态", "六彩圣君": "婷容修态", "身强体壮": "婷容修态",
    "平特网": "井井有条", "踏雪": "井井有条",
    "窃窃私语": "远赴相思", "自强不息": "远赴相思",
    "金吊桶": "广东八二站", "二肖四码": "无视一切", "玄机阁": "玄机",
    "红姐论坛": "目瞪口呆", "白虎": "鸿运",
}

ok = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global ok
    assert condition, f"{label} FAIL {detail}"
    ok += 1
    print(f"OK  {label}", flush=True)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def strip_comma_before_close(text: str) -> str:
    idx = text.rfind("]")
    k = idx - 1
    while text[k] in " \r\n":
        k -= 1
    return text[:k] + text[k + 1 :] if text[k] == "," else text


def block_of(text: str, key_prefix: str) -> str:
    start = text.index(key_prefix)
    line_end = text.find("\n", start)
    if "{" in text[start:line_end]:
        brace = text.index("{", start)
        obj_start = text.rfind("\n", 0, brace) + 1
    else:
        brace = text.rfind("{", 0, start)
        obj_start = text.rfind("\n", 0, brace) + 1
    depth, i = 0, brace
    while True:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
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
    blk = text[obj_start:j]
    assert key_prefix in blk
    return blk


# --- 1) 备份存在 ---
check("备份存在 sites/cache", (BK / "sites.json").exists() and (BK / "recent_10_cache.json").exists())

old_sites_text = (BK / "sites.json").read_bytes().decode("utf-8")
old_cache_text = (BK / "recent_10_cache.json").read_bytes().decode("utf-8")
old_sites = json.loads(old_sites_text)
old_cache = json.loads(old_cache_text)
check("备份为封存前状态（112 站含全部目标）", len(old_sites) == 112 and all(n in old_cache["sites"] for n in TARGETS))
check("备份缓存站点 112", len(old_cache["sites"]) == 112)

# --- 2) sites.json：文本级 = 原文删掉 12 块 ---
sites_text = SITES.read_bytes().decode("utf-8")
expected_sites = old_sites_text
for name in TARGETS:
    expected_sites = expected_sites.replace(block_of(old_sites_text, f'    "name": "{name}",'), "", 1)
expected_sites = strip_comma_before_close(expected_sites)
check("sites.json 逐字节 == 原文删掉这 12 条", sites_text == expected_sites)
new_sites = json.loads(sites_text)
check("sites.json 100 站", len(new_sites) == 100, str(len(new_sites)))
check("sites.json 无封存站", not ({s["name"] for s in new_sites} & set(TARGETS)))
kept = [s for s in old_sites if s["name"] not in TARGETS]
check("其余 100 站内容与顺序完全未变", new_sites == kept)
check("行尾形态未变（裸 LF 计数相同）",
      sites_text.count("\n") - sites_text.count("\r\n") == old_sites_text.count("\n") - old_sites_text.count("\r\n"))

# --- 3) recent_10_cache.json：文本级 = 原文删掉 12 块 ---
cache_text = CACHE.read_bytes().decode("utf-8")
expected_cache = old_cache_text
for name in TARGETS:
    expected_cache = expected_cache.replace(block_of(old_cache_text, f'    "{name}": {{'), "", 1)
expected_cache = strip_comma_before_close(expected_cache)
check("缓存逐字节 == 原文删掉这 12 条", cache_text == expected_cache)
new_cache = json.loads(cache_text)
check("缓存 100 站", len(new_cache["sites"]) == 100, str(len(new_cache["sites"])))
check("缓存期号未变", new_cache["periods"] == old_cache["periods"] == [281, 280, 279, 278, 277, 276, 275, 274, 273, 272])
check("缓存 updated_at 未变", new_cache["updated_at"] == old_cache["updated_at"])
check("缓存无封存站", not (set(new_cache["sites"]) & set(TARGETS)))
check("其余站点缓存逐字段未变",
      all(new_cache["sites"][k] == v for k, v in old_cache["sites"].items() if k not in TARGETS))
check("缓存格式仍可被爬虫 writer 复现",
      cache_text == json.dumps(new_cache, ensure_ascii=False, indent=2).replace("\n", "\r\n"))

# --- 4) 封存清单 ---
archived = json.loads(ARCHIVE.read_text(encoding="utf-8"))
check("封存清单 12 条", len(archived["sites"]) == 12, str(len(archived["sites"])))
check("封存清单站点名与名单一致", {i["name"] for i in archived["sites"]} == set(TARGETS))
for item in archived["sites"]:
    name = item["name"]
    partner = TARGETS[name]
    origin = next(s for s in old_sites if s["name"] == name)
    check(f"{name}: 原始字段完整保留", all(item.get(k) == v for k, v in origin.items()), str(item))
    check(f"{name}: archive_tag/duplicate_of 正确",
          item["archive_tag"] == f"dup-of:{partner}" and item["duplicate_of"] == partner)
    check(f"{name}: 缓存快照 == 封存前缓存", item["cache_data"] == old_cache["sites"][name]["data"])
    check(f"{name}: 快照与保留站 {partner} 逐期全等",
          item["cache_data"] == new_cache["sites"][partner]["data"],
          f'{item["cache_data"]} vs {new_cache["sites"][partner]["data"]}')

# --- 5) 爬虫自身路径 ---
loaded = c.load_sites(SITES)
check("load_sites 100 站且无封存站", len(loaded) == 100 and not ({s.name for s in loaded} & set(TARGETS)))
tmpdir = Path(tempfile.mkdtemp(prefix="verify_archive_"))
tmp_cache = tmpdir / "recent_10_cache.json"
shutil.copy2(CACHE, tmp_cache)
c.update_recent_cache(tmp_cache, 281, loaded, [], keep=10)
merged = json.loads(tmp_cache.read_text(encoding="utf-8"))
check("缓存合并路径仍 100 站、无封存站、期号不变",
      len(merged["sites"]) == 100 and not (set(merged["sites"]) & set(TARGETS)) and merged["periods"] == new_cache["periods"])
shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n全部 {ok} 项复验通过")
print("sites.json", SITES.stat().st_size, sha(SITES))
print("recent_10_cache.json", CACHE.stat().st_size, sha(CACHE))
print("archived_sites.json", ARCHIVE.stat().st_size, sha(ARCHIVE))
