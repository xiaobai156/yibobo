# -*- coding: utf-8 -*-
import sys
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
for i in [33, 34, 35, 40, 44]:
    t = text_of(docs[i])
    (OUT / f"d{i}.txt").write_text(t, encoding="utf-8")
    print("=" * 25, "doc", i, "len", len(t), flush=True)
    print(t[:1500], flush=True)
