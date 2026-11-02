# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c
URL = "https://xaglnyad.vjs6a-uv2o4-cxagtq.work:17477/topic/453196.html"
site = c.Site("清气若兰", URL, "top", keyword="双波中特")
docs = c.collect_documents_for_site(site, 303)
cands = c.extract_focus_candidates(docs, "双波中特")
hist = c.build_site_history(cands, "top")
cache = json.loads((SHA / "recent_10_cache.json").read_text(encoding="utf-8"))
periods = [int(p) for p in cache["periods"]]
mine = {p: hist.get(p) for p in periods}
print("本站窗口 =", [(p, mine[p]) for p in periods], flush=True)

rows = []
for name, e in cache["sites"].items():
    d = {int(k): v for k, v in e["data"].items()}
    same = sum(1 for p in periods if mine.get(p) and d.get(p) and mine[p] == d[p])
    run = mx = 0
    for p in periods:
        if mine.get(p) and d.get(p) and mine[p] == d[p]:
            run += 1; mx = max(mx, run)
        else:
            run = 0
    rows.append((mx, same, name))
rows.sort(reverse=True)
print("最长连续一致 TOP5 =", rows[:5], flush=True)
print("一致期数 TOP5 =", sorted(rows, key=lambda r: -r[1])[:5], flush=True)
print("触发『连续>=6期重复』的站 =", [r for r in rows if r[0] >= 6] or "无", flush=True)
print("10期全等 =", [r for r in rows if r[1] == 10] or "无", flush=True)
