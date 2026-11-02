# -*- coding: utf-8 -*-
"""只读勘察：新站「匠心独具」身份、栏目、历史、判重。不写配置/缓存/输出。"""
import json
import sys
from collections import Counter
from pathlib import Path

SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

URL = "https://jjhxjml.o7l2u-l7v36-xooewt.work:17466/topic/768581.html"
PERIOD = 303

site = c.Site(name="匠心独具", url=URL, pick="bottom")
print("strict =", c.is_strict_region(site), flush=True)

docs = c.collect_documents_for_site(site, PERIOD)
print("docs =", len(docs), flush=True)
title = None
for d in docs:
    t = getattr(d, "title", None)
    if t:
        title = t
        break
print("title =", title, flush=True)

# 找栏目锚点
import re
hits = []
for i, d in enumerate(docs):
    txt = getattr(d, "text", "") or ""
    if "绝杀一波" in txt:
        hits.append((i, len(txt)))
print("含『绝杀一波』的 doc:", hits[:10], flush=True)

cands = c.extract_primary_candidates(docs, site)
print("候选数 =", len(cands), flush=True)
for x in cands[:20]:
    print(f"  order={x.order} issue={x.issue} value={x.value} line={x.line[:60]!r}", flush=True)

if cands:
    print("目标期裁决 bottom:", c.select_candidate_with_reason(cands, PERIOD, "bottom"), flush=True)
    print("目标期裁决 top   :", c.select_candidate_with_reason(cands, PERIOD, "top"), flush=True)
    hist = c.build_site_history(cands, "bottom")
    print("历史(bottom) =", dict(sorted(hist.items(), reverse=True)), flush=True)
