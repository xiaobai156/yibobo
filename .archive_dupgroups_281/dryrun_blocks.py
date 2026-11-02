# -*- coding: utf-8 -*-
"""只读 dry-run：验证封存脚本的原文块抽取与删除结果（不写任何文件）。

helper 与 archive_dupgroups.py 保持同源实现，避免 import 会执行写盘主流程。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

SHA = Path(__file__).resolve().parent.parent

TARGETS = [
    "长乐未央", "六彩圣君", "身强体壮", "平特网", "踏雪", "窃窃私语",
    "自强不息", "金吊桶", "二肖四码", "玄机阁", "红姐论坛", "白虎",
]


def json_object_block(text: str, key_prefix: str) -> str:
    start = text.index(key_prefix)
    line_end = text.find("\n", start)
    if "{" in text[start:line_end]:
        brace = text.index("{", start)
        obj_start = text.rfind("\n", 0, brace) + 1
    else:
        brace = text.rfind("{", 0, start)
        assert brace != -1, key_prefix
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


def strip_comma_before_close(text: str):
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


sites_text = (SHA / "sites.json").read_bytes().decode("utf-8")
cache_text = (SHA / "recent_10_cache.json").read_bytes().decode("utf-8")

sites_after = sites_text
for name in TARGETS:
    block = json_object_block(sites_text, f'    "name": "{name}",')
    print(f"sites {name}: {len(block)}B 匹配={sites_after.count(block)} 首行={block.splitlines()[0]!r} 末行={block.splitlines()[-1]!r}")
    sites_after = sites_after.replace(block, "", 1)
sites_after2, fix = strip_comma_before_close(sites_after)
sn = json.loads(sites_after2)
print("sites 删除后:", len(sn), "站；尾逗号修正:", fix)

cache_after = cache_text
for name in TARGETS:
    block = json_object_block(cache_text, f'    "{name}": {{')
    print(f"cache {name}: {len(block)}B 匹配={cache_after.count(block)} 首行={block.splitlines()[0]!r} 末行={block.splitlines()[-1]!r}")
    cache_after = cache_after.replace(block, "", 1)
cache_after2, fix2 = strip_comma_before_close(cache_after)
cn = json.loads(cache_after2)
print("cache 删除后:", len(cn["sites"]), "站；periods 未变:", cn["periods"] == json.loads(cache_text)["periods"], "；尾逗号修正:", fix2)

removed = Counter(sites_text.split("\r\n")) - Counter(sites_after2.split("\r\n"))
added = Counter(sites_after2.split("\r\n")) - Counter(sites_text.split("\r\n"))
print("sites 文本差: removed", sum(removed.values()), "added", sum(added.values()), dict(added))
removed2 = Counter(cache_text.split("\r\n")) - Counter(cache_after2.split("\r\n"))
added2 = Counter(cache_after2.split("\r\n")) - Counter(cache_text.split("\r\n"))
print("cache 文本差: removed", sum(removed2.values()), "added", sum(added2.values()), dict(added2))
print("未封存站点逐一未变:", all(cn["sites"][k] == json.loads(cache_text)["sites"][k] for k in cn["sites"]))
print("sites 顺序保持:", [s["name"] for s in sn] == [s["name"] for s in json.loads(sites_text) if s["name"] not in TARGETS])
