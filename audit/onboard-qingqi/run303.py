# -*- coding: utf-8 -*-
"""清气若兰 303 期正式跑：真实入口 crawl_site -> 缓存 -> 303 期 TXT 重建。"""
import json, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

NAME = "清气若兰"
PERIOD = 303
sites = c.load_sites(SHA / "sites.json")
print("站点数 =", len(sites), flush=True)
site = {s.name: s for s in sites}[NAME]
print("配置 =", site.name, site.url, "pick=", site.pick, "keyword=", site.keyword, flush=True)

result, error = c.crawl_site(site, PERIOD)
print("结果 =", result, "| 错误 =", error, flush=True)
if result is None:
    raise SystemExit("抓取未通过，不写入")
