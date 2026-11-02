# -*- coding: utf-8 -*-
import sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c
sites = {s.name: s for s in c.load_sites(SHA / "sites.json")}
for name in ("澳彩传奇", "针锋相对", "失魂落魄", "清气若兰"):
    s = sites.get(name)
    docs = c.collect_documents_for_site(s, 303)
    cands = c.extract_primary_candidates(docs, s)
    ahead = [x for x in cands if x.issue > 303]
    print("=" * 10, name, "前向候选", len(ahead), flush=True)
    for x in ahead[:3]:
        print("   ", x.issue, x.value, "|", x.line, flush=True)
    drawn = [x for x in cands if x.issue <= 303]
    print("   其余 max =", max((x.issue for x in drawn), default=None), flush=True)
