# -*- coding: utf-8 -*-
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
def text_of(d):
    for a in ("text", "content", "html", "raw"):
        v = getattr(d, a, None)
        if isinstance(v, str) and v:
            return v
    return str(d)
TAG = re.compile(r"<[^>]+>")
for i in [41, 42, 44, 47]:
    plain = html.unescape(TAG.sub("", text_of(docs[i])))
    (OUT / f"d{i}.txt").write_text(plain, encoding="utf-8")
    print("=" * 24, "doc", i, "len", len(plain), flush=True)
    print(plain[:1600], flush=True)
