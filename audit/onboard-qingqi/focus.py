# -*- coding: utf-8 -*-
import sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c
URL = "https://xaglnyad.vjs6a-uv2o4-cxagtq.work:17477/topic/453196.html"
site = c.Site("清气若兰", URL, "top", keyword="双波中特")
docs = c.collect_documents_for_site(site, 303)
for fn_name in ("extract_focus_candidates",):
    fn = getattr(c, fn_name, None)
    if fn is None:
        print(fn_name, "不存在"); continue
    cands = fn(docs, "双波中特")
    print(fn_name, "候选 =", len(cands), flush=True)
    for x in cands[:6]:
        print("   ", x.order, x.issue, x.value, flush=True)
    if cands:
        print("303 ->", c.select_candidate_with_reason(cands, 303, "top"), flush=True)
        print("302 ->", c.select_candidate_with_reason(cands, 302, "top"), flush=True)
        h = c.build_site_history(cands, "top")
        print("历史", len(h), "最新6", [(k, h[k]) for k in sorted(h, reverse=True)[:6]], flush=True)
