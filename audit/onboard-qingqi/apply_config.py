# -*- coding: utf-8 -*-
"""特例接入 清气若兰：写 sites.json + 注册解析器名单。"""
import json, re
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")

NAME = "清气若兰"
URL = "https://xaglnyad.vjs6a-uv2o4-cxagtq.work:17477/topic/453196.html"

# 1) sites.json
p = SHA / "sites.json"
sites = json.loads(p.read_text(encoding="utf-8"))
if any(s["name"] == NAME for s in sites):
    print("已存在，跳过 sites.json")
else:
    sites.append({"name": NAME, "url": URL, "pick": "top", "keyword": "双波中特"})
    p.write_text(json.dumps(sites, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("sites.json 站点数 =", len(sites))

# 2) 注册到 REGISTERED_FOCUS_SITE_NAMES
q = SHA / "sha_yibo_crawler.py"
src = q.read_text(encoding="utf-8")
if f'"{NAME}"' in src:
    print("解析器名单已含该站，跳过")
else:
    anchor = '    "雨果天气",\n'
    assert src.count(anchor) == 1, src.count(anchor)
    src = src.replace(anchor, anchor + f'    "{NAME}",\n', 1)
    q.write_text(src, encoding="utf-8")
    print("已加入 REGISTERED_FOCUS_SITE_NAMES")

# 复核
sites2 = json.loads(p.read_text(encoding="utf-8"))
print("复核 sites.json:", [s for s in sites2 if s["name"] == NAME], "总数", len(sites2))
