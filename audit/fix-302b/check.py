# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path
SHA = Path(r"C:\Users\Administrator\Desktop\每天工具\爬虫合集\杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

print("=== missing_wave_value 语义测试 ===")
for a, b in [("蓝波","红波"), ("绿波","红波"), ("蓝波","蓝波"), ("红波","红波"), ("绿波","绿波")]:
    print(f"  {a} + {b} -> {c.missing_wave_value(a, b)}")

print("\n=== 雨果天气 正常抓取 vs 渲染兜底 ===")
sites = {s.name: s for s in c.load_sites(SHA / "sites.json")}
s = sites["雨果天气"]
d1 = c.collect_documents_for_site(s, 302)
print("  collect_documents_for_site:", len(d1), [len(x) for x in d1])
d2 = c.collect_rendered_documents(s.url)
print("  collect_rendered_documents:", len(d2), [len(x) for x in d2])
for tag, docs in [("normal", d1), ("rendered", d2)]:
    cands = c.extract_primary_candidates(docs, s)
    found = {}
    for x in cands:
        found.setdefault(x.issue, x.value)
    print(f"  {tag}: 候选={len(cands)} 最新={sorted(found, reverse=True)[:5]} 302={found.get(302)} 303={found.get(303)}")

cache = json.loads((SHA / "recent_10_cache.json").read_text(encoding="utf-8"))
print("\n  缓存 雨果天气:", dict(sorted(cache["sites"]["雨果天气"]["data"].items(), key=lambda kv:-int(kv[0]))))
