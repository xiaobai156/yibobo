# -*- coding: utf-8 -*-
"""只读勘察：南金东箭（顶部），确认栏目、历史、与雨果天气 302 的关系。"""
import html, re, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

URL = "https://rujlvxn.ss1zj-ptamt-njsyyf.work:17455/topic/770539.html"
OUT = SHA / "audit" / "onboard-nanjin" / "out"
OUT.mkdir(parents=True, exist_ok=True)

site = c.Site(name="南金东箭", url=URL, pick="top")
docs = c.collect_documents_for_site(site, 303)
print("docs =", len(docs), flush=True)

def text_of(d):
    for a in ("text", "content", "html", "raw"):
        v = getattr(d, a, None)
        if isinstance(v, str) and v:
            return v
    return str(d)

TAG = re.compile(r"<[^>]+>")
keys = ["两波中特", "中特", "波色", "反推", "一波", "红波"]
hit = {}
for i, d in enumerate(docs):
    plain = html.unescape(TAG.sub("", text_of(d)))
    for k in keys:
        if k in plain:
            hit.setdefault(k, []).append(i)
for k, v in hit.items():
    print(k, "->", len(v), v[:10], flush=True)

for i in hit.get("两波中特", hit.get("中特", []))[:4]:
    plain = html.unescape(TAG.sub("", text_of(docs[i])))
    (OUT / f"p{i}.txt").write_text(plain, encoding="utf-8")
    print("=" * 22, "doc", i, flush=True)
    print(plain[:1200], flush=True)
