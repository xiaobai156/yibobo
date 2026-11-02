# -*- coding: utf-8 -*-
"""只读勘察：清气若兰（顶部）。"""
import html, re, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

URL = "https://xaglnyad.vjs6a-uv2o4-cxagtq.work:17477/topic/453196.html"
OUT = SHA / "audit" / "onboard-qingqi" / "out"
OUT.mkdir(parents=True, exist_ok=True)

site = c.Site("清气若兰", URL, "top")
docs = c.collect_documents_for_site(site, 303)
print("docs =", len(docs), flush=True)

def text_of(d):
    for a in ("text", "content", "html", "raw"):
        v = getattr(d, a, None)
        if isinstance(v, str) and v:
            return v
    return str(d)
TAG = re.compile(r"<[^>]+>")

keys = ["绝杀一波", "一波", "两波中特", "波色", "红波", "蓝波"]
hit = {}
for i, d in enumerate(docs):
    plain = html.unescape(TAG.sub("", text_of(d)))
    for k in keys:
        if k in plain:
            hit.setdefault(k, []).append(i)
for k, v in hit.items():
    print(k, "->", len(v), v[:8], flush=True)

show = hit.get("绝杀一波") or hit.get("一波") or hit.get("两波中特") or []
for i in show[:3]:
    plain = html.unescape(TAG.sub("", text_of(docs[i])))
    (OUT / f"q{i}.txt").write_text(plain, encoding="utf-8")
    print("=" * 22, "doc", i, flush=True)
    print(plain[:1400], flush=True)
