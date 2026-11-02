# -*- coding: utf-8 -*-
"""302 期剩余失败站 雨果天气 只读验证。"""
import sys, time, json
from pathlib import Path
SHA = Path(r"C:\Users\Administrator\Desktop\每天工具\爬虫合集\杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

PERIOD = 302
sites = {s.name: s for s in c.load_sites(SHA / "sites.json")}
cache = json.loads((SHA / "recent_10_cache.json").read_text(encoding="utf-8"))
name = "雨果天气"
s = sites[name]
cached = cache["sites"][name]["data"]
print(f"### {name}  pick={s.pick} kw={s.keyword}")
print(f"   url={s.url}")
print(f"   缓存: {dict(sorted(cached.items(), key=lambda kv:-int(kv[0])))}")

for attempt in (1, 2, 3):
    t0 = time.time()
    try:
        docs = c.collect_documents_for_site(s, PERIOD)
        cands = c.extract_primary_candidates(docs, s)
        found = {}
        for x in cands:
            found.setdefault(x.issue, x.value)
        hits = [x for x in cands if x.issue == PERIOD]
        ok = sum(1 for k, v in cached.items() if found.get(int(k)) == v)
        print(f"\n   第{attempt}次 OK {round(time.time()-t0,1)}s docs={len(docs)} 候选={len(cands)}")
        print(f"     302 = {[x.value for x in hits] or '仍无'}")
        print(f"     页面最新期号: {sorted(found, reverse=True)[:12]}")
        print(f"     历史一致 {ok}/{len(cached)}")
        for k in sorted(cached, key=lambda x:-int(x)):
            pv = found.get(int(k))
            print(f"       {k}: 缓存={cached[k]:3} 页面={str(pv):4} {'OK' if pv==cached[k] else '≠'}")
        break
    except Exception as exc:
        print(f"   第{attempt}次 失败 {round(time.time()-t0,1)}s {type(exc).__name__}: {str(exc).splitlines()[0][:120]}")
        if attempt < 3: time.sleep(5)
print("\nDONE")
