# -*- coding: utf-8 -*-
"""确认抓取是否受 period 参数影响（SPA 可能按 period 导航）。"""
import sys, re
from pathlib import Path
SHA = Path(r"C:\Users\Administrator\Desktop\每天工具\爬虫合集\杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c
sites = {s.name: s for s in c.load_sites(SHA / "sites.json")}
s = sites["雨果天气"]
PAT = re.compile(r"(\d{3})期[^【]{0,6}两波中特[^【]{0,4}[【\[]\s*([红蓝绿])波(?:防)?([红蓝绿])波")
for p in (301, 302, 303):
    docs = c.collect_documents_for_site(s, p)
    txt = docs[0]
    found = {}
    for m in PAT.finditer(txt):
        found.setdefault(int(m.group(1)), (m.group(2), m.group(3)))
    top = sorted(found, reverse=True)[:3]
    detail = ", ".join(f"{k}=【{found[k][0]}防{found[k][1]}】" for k in top)
    print(f"period={p}: docs={len(docs)} len={len(txt)} 最新={top}  {detail}")
