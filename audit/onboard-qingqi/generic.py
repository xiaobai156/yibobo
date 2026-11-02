# -*- coding: utf-8 -*-
"""验证通用解析器能否直接吃下 双波中特《红波绿波》格式。"""
import json, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

URL = "https://xaglnyad.vjs6a-uv2o4-cxagtq.work:17477/topic/453196.html"
site = c.Site("清气若兰", URL, "top")
docs = c.collect_documents_for_site(site, 303)
cands = c.extract_primary_candidates(docs, site)
print("通用解析候选 =", len(cands), flush=True)
for x in cands[:8]:
    print(f"  order={x.order} {x.issue} = {x.value}", flush=True)
for p in (304, 303, 302, 301, 300):
    print(p, "->", c.select_candidate_with_reason(cands, p, "top"), flush=True)
hist = c.build_site_history(cands, "top")
print("历史条数 =", len(hist), flush=True)
print("最新 6 =", [(k, hist[k]) for k in sorted(hist, reverse=True)[:6]], flush=True)

# 最长连续一致
cache = json.loads((SHA / "recent_10_cache.json").read_text(encoding="utf-8"))
periods = [int(p) for p in cache["periods"]]
mine = {p: hist.get(p) for p in periods}
best = (0, None)
for name, e in cache["sites"].items():
    d = {int(k): v for k, v in e["data"].items()}
    run = mx = 0
    for p in periods:
        if mine.get(p) and d.get(p) and mine[p] == d[p]:
            run += 1; mx = max(mx, run)
        else:
            run = 0
    if mx > best[0]:
        best = (mx, name)
print("最长连续一致 =", best, flush=True)
