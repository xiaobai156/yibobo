# -*- coding: utf-8 -*-
"""再抓两次，看 302/303 是否稳定。"""
import sys, time, re
from pathlib import Path
SHA = Path(r"C:\Users\Administrator\Desktop\每天工具\爬虫合集\杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c
sites = {s.name: s for s in c.load_sites(SHA / "sites.json")}
s = sites["雨果天气"]
PAT = re.compile(r"(\d{3})期[^【]{0,6}两波中特[^【]{0,4}[【\[]\s*([红蓝绿])波(?:防)?([红蓝绿])波")
for i in range(1, 4):
    docs = c.collect_documents_for_site(s, 302)
    txt = docs[0]
    found = {}
    for m in PAT.finditer(txt):
        found.setdefault(int(m.group(1)), (m.group(2), m.group(3)))
    print(f"第{i}次: 最新期号={sorted(found, reverse=True)[:4]}")
    for k in sorted(found, reverse=True)[:4]:
        a, b = found[k]
        print(f"   {k}: 【{a}波防{b}波】 -> 缺失={c.missing_wave_value(a+'波', b+'波')}")
    time.sleep(3)
