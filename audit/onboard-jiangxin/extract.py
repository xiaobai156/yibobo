# -*- coding: utf-8 -*-
"""只读：提取匠心独具「绝杀一波」全部历史 + 与在册 99 站判重。"""
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

URL = "https://jjhxjml.o7l2u-l7v36-xooewt.work:17466/topic/768581.html"
TARGET = 303

site = c.Site(name="匠心独具", url=URL, pick="bottom")
docs = c.collect_documents_for_site(site, TARGET)

def text_of(d):
    for attr in ("text", "content", "html", "raw"):
        v = getattr(d, attr, None)
        if isinstance(v, str) and v:
            return v
    return str(d)

TAG = re.compile(r"<[^>]+>")
ROW = re.compile(r"(\d{3})\s*期\s*绝杀一波\s*[（(]\s*(红|蓝|绿)\s*波\s*[）)]")

order = 0
rows = []
seen = set()
for d in docs:
    plain = html.unescape(TAG.sub("", text_of(d)))
    for m in ROW.finditer(plain):
        issue, val = int(m.group(1)), m.group(2) + "波"
        key = (issue, val)
        if key in seen:
            continue
        seen.add(key)
        rows.append((order, issue, val))
        order += 1

print("原始行数 =", len(rows), flush=True)
hist = {}
conflict = []
for order_i, issue, val in rows:
    if issue in hist and hist[issue] != val:
        conflict.append((issue, hist[issue], val))
    hist[issue] = val

print("期数 =", len(hist), flush=True)
print("冲突 =", conflict or "无", flush=True)
print("最新 12 期 =", [(k, hist[k]) for k in sorted(hist, reverse=True)[:12]], flush=True)
print("最旧 3 期 =", [(k, hist[k]) for k in sorted(hist)[:3]], flush=True)
print("目标期 %d = %s" % (TARGET, hist.get(TARGET)), flush=True)

# 连续性
issues = sorted(hist)
gaps = [(a, b) for a, b in zip(issues, issues[1:]) if b - a != 1]
print("不连续处 =", gaps[:10], "共", len(gaps), flush=True)

# 判重：与缓存 99 站近 10 期比对
cache = json.loads((SHA / "recent_10_cache.json").read_text(encoding="utf-8"))
periods = [int(p) for p in cache["periods"]]
mine = tuple(hist.get(p) for p in periods)
print("\n本站窗口 %s = %s" % (periods, mine), flush=True)

dup_full, dup_part = [], []
for name, e in cache["sites"].items():
    d = {int(k): v for k, v in e["data"].items()}
    theirs = tuple(d.get(p) for p in periods)
    common = [(p, mine[i], theirs[i]) for i, p in enumerate(periods)
              if mine[i] and theirs[i] and mine[i] == theirs[i]]
    if all(mine[i] and theirs[i] and mine[i] == theirs[i] for i in range(len(periods))):
        dup_full.append(name)
    elif len(common) >= 3:
        dup_part.append((name, len(common), common))

print("完全一致(10期全等) =", dup_full or "无", flush=True)
print("部分重合>=3期 =", len(dup_part), flush=True)
for n, k, cm in sorted(dup_part, key=lambda x: -x[1])[:8]:
    print("   ", n, k, cm, flush=True)
