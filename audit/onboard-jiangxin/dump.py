# -*- coding: utf-8 -*-
"""导出文档，找栏目与数据锚点。"""
import re, sys
from pathlib import Path

SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

URL = "https://jjhxjml.o7l2u-l7v36-xooewt.work:17466/topic/768581.html"
OUT = SHA / "audit" / "onboard-jiangxin" / "out"
OUT.mkdir(parents=True, exist_ok=True)

site = c.Site(name="匠心独具", url=URL, pick="bottom")
docs = c.collect_documents_for_site(site, 303)

def text_of(d):
    for attr in ("text", "content", "html", "raw"):
        v = getattr(d, attr, None)
        if isinstance(v, str) and v:
            return v
    return str(d)

keys = ["一波", "绝杀", "杀一", "波色", "红波", "蓝波", "绿波"]
found = {}
for i, d in enumerate(docs):
    t = text_of(d)
    for k in keys:
        if k in t:
            found.setdefault(k, []).append(i)

for k, v in found.items():
    print(k, "->", len(v), v[:12], flush=True)

# 打印含「一波」的前几个
for i in found.get("一波", [])[:5]:
    t = text_of(docs[i])
    print("=" * 20, "doc", i, "len", len(t), flush=True)
    print(t[:1200], flush=True)
    (OUT / f"doc{i}.txt").write_text(t, encoding="utf-8")
