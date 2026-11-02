# -*- coding: utf-8 -*-
"""清气若兰 303 期写入：缓存 + 303 期成功TXT 重建。"""
import json, sys
from collections import Counter
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

PERIOD = 303
sites = c.load_sites(SHA / "sites.json")
name = "清气若兰"
site = {s.name: s for s in sites}[name]
res, err = c.crawl_site(site, PERIOD)
assert res is not None, err
print("抓取 =", res, flush=True)

c.update_recent_cache(c.DEFAULT_CACHE_FILE, PERIOD, sites, [c.SuccessResult(res.name, res.value, site.url)])
cache = json.loads(c.DEFAULT_CACHE_FILE.read_text(encoding="utf-8"))
print("缓存站点数 =", len(cache["sites"]), "| periods =", cache["periods"], flush=True)
print("清气若兰 303 =", cache["sites"][name]["data"].get("303"), flush=True)

# 从缓存重建 303 期 TXT
periods = [int(p) for p in cache["periods"]]
results = []
for key, entry in cache["sites"].items():
    value = entry.get("data", {}).get(str(PERIOD))
    if value:
        results.append(c.SuccessResult(entry["name"], value, entry.get("url")))
out = c.DEFAULT_OUTPUT_DIR / f"{PERIOD}期-一波.txt"
c.write_success_results(out, results)
merged = c.parse_success_results(out.read_text(encoding="utf-8"))
print("TXT 条数 =", len(merged), "| 排行 =", Counter(r.value for r in merged), flush=True)
print("含清气若兰 =", [(r.name, r.value) for r in merged if r.name == name], flush=True)
