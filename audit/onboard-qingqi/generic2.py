# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c
URL = "https://xaglnyad.vjs6a-uv2o4-cxagtq.work:17477/topic/453196.html"
for kw in ("双波中特", "一波", None):
    site = c.Site("清气若兰", URL, "top", keyword=kw)
    docs = c.collect_documents_for_site(site, 303)
    cands = c.extract_primary_candidates(docs, site)
    print(f"keyword={kw!r} docs={len(docs)} 候选={len(cands)}", flush=True)
    if cands:
        for x in cands[:5]:
            print("   ", x.order, x.issue, x.value, flush=True)
        print("   303 ->", c.select_candidate_with_reason(cands, 303, "top"), flush=True)
