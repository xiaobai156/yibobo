# -*- coding: utf-8 -*-
"""只读：检查 sites.json 是否有重名，并定位删除后顺序比对的首个差异。"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

SHA = Path(__file__).resolve().parent.parent
sites = json.loads((SHA / "sites.json").read_text(encoding="utf-8"))
names = [s["name"] for s in sites]
dup = {k: v for k, v in Counter(names).items() if v > 1}
print("总条数", len(sites), "唯一名", len(set(names)), "重名:", dup)

TARGETS = {"长乐未央", "六彩圣君", "身强体壮", "平特网", "踏雪", "窃窃私语",
           "自强不息", "金吊桶", "二肖四码", "玄机阁", "红姐论坛", "白虎"}
expected = [n for n in names if n not in TARGETS]
print("expected 长度", len(expected))

# 与 dry-run 相同逻辑
import sys  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
text = (SHA / "sites.json").read_bytes().decode("utf-8")


def json_object_block(t, key_prefix):
    start = t.index(key_prefix)
    brace = t.index("{", start)
    line_start = t.rfind("\n", 0, brace) + 1
    depth = 0
    i = brace
    while True:
        ch = t[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    j = i + 1
    if t.startswith(",", j):
        j += 1
    if t.startswith("\r\n", j):
        j += 2
    elif t.startswith("\n", j):
        j += 1
    return t[line_start:j]


after = text
for name in TARGETS:
    blk = json_object_block(text, f'    "name": "{name}",')
    after = after.replace(blk, "", 1)
got = [s["name"] for s in json.loads(after)]
print("got 长度", len(got))
if got != expected:
    for i, (a, b) in enumerate(zip(got, expected)):
        if a != b:
            print("首个差异 idx", i, "got", a, "expected", b)
            print("got 前 8:", got[max(0, i - 3): i + 4])
            print("exp 前 8:", expected[max(0, i - 3): i + 4])
            break
    else:
        print("长度不同：got", len(got), "expected", len(expected))
        print("got 尾部:", got[-5:])
        print("exp 尾部:", expected[-5:])
