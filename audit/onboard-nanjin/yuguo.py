# -*- coding: utf-8 -*-
"""只读：导出雨果天气原始两波行，与南金东箭对照。"""
import html, json, re, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

cache = json.loads((SHA / "recent_10_cache.json").read_text(encoding="utf-8"))
url = cache["sites"]["雨果天气"]["url"]
print("雨果天气 url =", url, flush=True)
site = c.Site(name="雨果天气", url=url, pick="top", keyword="两波中特")
docs = c.collect_documents_for_site(site, 302)

def text_of(d):
    for a in ("text", "content", "html", "raw"):
        v = getattr(d, a, None)
        if isinstance(v, str) and v:
            return v
    return str(d)

TAG = re.compile(r"<[^>]+>")
n = 0
for i, d in enumerate(docs):
    plain = html.unescape(TAG.sub("", text_of(d)))
    if "两波中特" not in plain:
        continue
    n += 1
    lines = [l.strip() for l in plain.splitlines() if l.strip()]
    keep = [l for l in lines if "两波中特" in l]
    print("=" * 20, "doc", i, "命中行", len(keep), flush=True)
    for l in keep[:12]:
        print("   ", l, flush=True)
    if n >= 3:
        break
