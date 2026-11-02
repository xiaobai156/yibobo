# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c
URL = "https://xaglnyad.vjs6a-uv2o4-cxagtq.work:17477/topic/453196.html"
site = c.Site("清气若兰", URL, "top", keyword="双波中特")
hist = c.build_site_history(c.extract_focus_candidates(c.collect_documents_for_site(site, 303), "双波中特"), "top")
cache = json.loads((SHA / "recent_10_cache.json").read_text(encoding="utf-8"))
periods = [int(p) for p in cache["periods"]]
for name in ("针锋相对", "失魂落魄", "珠光宝气", "招财猫"):
    d = {int(k): v for k, v in cache["sites"][name]["data"].items()}
    print("=" * 14, name, flush=True)
    for p in periods:
        a, b = hist.get(p), d.get(p)
        mark = "同" if a and b and a == b else "异"
        print(f"   {p}: 本站={a} 对方={b} {mark}", flush=True)
