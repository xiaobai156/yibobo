# -*- coding: utf-8 -*-
import sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

sites = {s.name: s for s in c.load_sites(SHA / "sites.json")}
site = sites["满目河山"]
print("pick =", site.pick, "| keyword =", getattr(site, "keyword", None), flush=True)

docs = c.collect_documents_for_site(site, 304)
print("docs =", len(docs), flush=True)
for i, d in enumerate(docs):
    txt = d.text if hasattr(d, "text") else str(d)
    print(f"--- doc{i} len={len(txt)} url={getattr(d,'url','')}", flush=True)
    print(txt[:1500], flush=True)
    if i >= 2:
        break

cands = c.extract_primary_candidates(docs, site)
print("候选数 =", len(cands), flush=True)
for x in cands[:15]:
    print(f"  order={x.order} issue={x.issue} value={x.value} line={x.line!r}", flush=True)
print("select(bottom) ->", c.select_candidate_with_reason(cands, 304, site.pick), flush=True)
