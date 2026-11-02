# -*- coding: utf-8 -*-
import re, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

site = {s.name: s for s in c.load_sites(SHA / "sites.json")}["满目河山"]
docs = c.collect_documents_for_site(site, 304)
txt = docs[0].text if hasattr(docs[0], "text") else str(docs[0])
out = SHA / "audit" / "fix-304" / "page304.html"
out.write_text(txt, encoding="utf-8")
print("saved", out, len(txt), flush=True)

for m in re.finditer(r"30[0-9]\s*期", txt):
    print("命中期号:", txt[max(0, m.start()-20):m.start()+120].replace("\n", " "), flush=True)
print("--- 含'双波中特'上下文 ---", flush=True)
for m in re.finditer(r"双波中特", txt):
    print(repr(txt[max(0, m.start()-90):m.start()+140]), flush=True)
