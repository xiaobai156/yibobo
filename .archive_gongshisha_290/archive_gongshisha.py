# -*- coding: utf-8 -*-
"""封存 公式杀（用户点名授权，2026-10-17）。

背景：公式杀节点自 287 期起连续 4 天不可达（ERR_CONNECTION_CLOSED / SSL EOF / ERR_TIMED_OUT），
同 :16677 平台对照站正常，缓存停 281~286，用户点名封存。

动作（仅三处，均先备份到 .archive_gongshisha_290\\before\\，不写 .bak）：
1. sites.json：按原文文本块精确删除「公式杀」条目（100 → 99），其余条目逐字节不变。
2. recent_10_cache.json：仅移除 「公式杀」站点条目（100 → 99），periods / updated_at 不变。
3. archived_sites.json：追加 公式杀 记录（原有 12 条不动），保存其缓存快照与封存原因。

封存后：不抓取、不写入、不更新缓存；恢复需用户再次点名授权。
"""
from __future__ import annotations

import json
import shutil
import sys
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHA = HERE.parent
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c  # noqa: E402

NAME = "公式杀"
PERIOD = 290
BEFORE = HERE / "before"
SITES = SHA / "sites.json"
CACHE = SHA / "recent_10_cache.json"
ARCHIVED = SHA / "archived_sites.json"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    BEFORE.mkdir(parents=True, exist_ok=True)
    for path in (SITES, CACHE, ARCHIVED):
        shutil.copy2(path, BEFORE / path.name)
    print("== 前态 ==")
    for path in (SITES, CACHE, ARCHIVED):
        print(f"  {path.name}: size={path.stat().st_size} sha={digest(path)}")

    sites_text = SITES.read_text(encoding="utf-8")
    cache_before = json.loads(CACHE.read_text(encoding="utf-8"))
    archived_before = json.loads(ARCHIVED.read_text(encoding="utf-8"))
    sites_before = json.loads(sites_text)

    target_lines = [i for i, line in enumerate(sites_text.splitlines()) if line.strip() == f'"name": "{NAME}",']
    assert len(target_lines) == 1, f"sites.json 中 {NAME} 条目数异常: {len(target_lines)}"
    name_idx = target_lines[0]
    lines = sites_text.splitlines(keepends=True)
    start = None
    for i in range(name_idx, -1, -1):
        if lines[i].strip() == "{":
            start = i
            break
    assert start is not None, "未找到条目起始大括号"
    end = None
    for i in range(name_idx, len(lines)):
        if lines[i].strip() in ("},", "}"):
            end = i
            break
    assert end is not None, "未找到条目结束大括号"
    block = "".join(lines[start : end + 1])
    assert NAME in block and '"url": "https://tetinte.nzxzd-cfket-xtgznp.xyz:16677/"' in block, block
    assert block.count(NAME) == 1, block
    print(f"\n== sites.json 删除块（行 {start + 1}-{end + 1}）==\n{block}")

    remaining = sites_text[: sum(len(x) for x in lines[:start])] + "".join(lines[end + 1 :])
    sites_after = json.loads(remaining)
    assert len(sites_before) == 100 and len(sites_after) == 99, (len(sites_before), len(sites_after))
    assert [s["name"] for s in sites_after] == [s["name"] for s in sites_before if s["name"] != NAME]
    assert not [s for s in sites_after if s["name"] == NAME]
    SITES.write_text(remaining, encoding="utf-8")

    old_entry = cache_before["sites"].pop(NAME)
    assert NAME not in cache_before["sites"] and len(cache_before["sites"]) == 99
    c.atomic_write_json(CACHE, cache_before)

    cache_after = json.loads(CACHE.read_text(encoding="utf-8"))
    assert cache_after["periods"] == cache_before["periods"] and cache_after["updated_at"] == cache_before["updated_at"]
    assert len(cache_after["sites"]) == 99 and NAME not in cache_after["sites"]

    archived_after = json.loads(json.dumps(archived_before, ensure_ascii=False))
    assert all(s["name"] != NAME for s in archived_after["sites"]), "公式杀 已在封存清单中"
    archived_after["sites"].append(
        {
            "name": NAME,
            "url": old_entry["url"],
            "pick": old_entry["pick"],
            "archive_tag": "node-unreachable",
            "archive_reason": (
                "节点自 287 期起连续 4 天不可达（ERR_CONNECTION_CLOSED / SSL EOF / ERR_TIMED_OUT，"
                "同 :16677 平台对照站正常），用户点名封存，恢复需再次授权"
            ),
            "unreachable_since": 287,
            "last_success_period": max(int(k) for k in old_entry["data"]),
            "missing_periods": sorted({*range(287, PERIOD + 1)} - {int(k) for k in old_entry["data"]}),
            "archived_period": PERIOD,
            "cache_data": old_entry["data"],
        }
    )
    ARCHIVED.write_text(json.dumps(archived_after, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n== 后态 ==")
    for path in (SITES, CACHE, ARCHIVED):
        print(f"  {path.name}: size={path.stat().st_size} sha={digest(path)}")
    print(f"  sites.json 站点数: {len(sites_before)} -> {len(sites_after)}")
    print(f"  cache 站点数: 100 -> {len(cache_after['sites'])}；periods={cache_after['periods']} updated_at={cache_after['updated_at']}")
    print(f"  archived_sites.json 条目数: {len(archived_before['sites'])} -> {len(archived_after['sites'])}")
    print(f"  公式杀 缓存快照: {old_entry['data']}")


if __name__ == "__main__":
    main()
