# -*- coding: utf-8 -*-
"""看 雨果天气 抓到的原文里 302/303 到底有没有。"""
import sys, json, re
from pathlib import Path
SHA = Path(r"C:\Users\Administrator\Desktop\每天工具\爬虫合集\杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c
sites = {s.name: s for s in c.load_sites(SHA / "sites.json")}
s = sites["雨果天气"]
docs = c.collect_documents_for_site(s, 302)
d = docs[0]
Path(SHA / "audit/fix-302b/doc0.txt").write_text(d, encoding="utf-8")
print("文档长度:", len(d))
for kw in ["302", "303", "两波中特"]:
    print(f"  [{kw}] 出现 {d.count(kw)} 次")
lines = [l.strip() for l in d.splitlines() if l.strip()]
print("\n含 302 的行:")
for l in [x for x in lines if "302" in x][:10]:
    print("   ", l[:150])
print("\n含 303 的行:")
for l in [x for x in lines if "303" in x][:10]:
    print("   ", l[:150])
print("\n含 两波中特 的前 8 行:")
for l in [x for x in lines if "两波中特" in x][:8]:
    print("   ", l[:150])
