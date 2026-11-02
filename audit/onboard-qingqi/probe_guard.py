# -*- coding: utf-8 -*-
import sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c
sites = {s.name: s for s in c.load_sites(SHA / "sites.json")}
for name in ("澳彩传奇", "雨果天气", "针锋相对", "失魂落魄"):
    s = sites.get(name)
    if not s:
        print(name, "不在册"); continue
    docs = c.collect_documents_for_site(s, 303)
    cands = c.extract_primary_candidates(docs, s)
    issues = [x.issue for x in cands]
    print(f"{name}: 候选 {len(cands)} max={max(issues) if issues else None} min={min(issues) if issues else None} "
          f"stale={c._looks_like_stale_year_block(issues, 303)}", flush=True)
    got, why = c.crawl_site(s, 303)
    print("   crawl_site ->", got, "|", why, flush=True)
