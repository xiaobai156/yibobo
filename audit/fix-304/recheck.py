# -*- coding: utf-8 -*-
import re, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

site = {s.name: s for s in c.load_sites(SHA / "sites.json")}["满目河山"]
for i in (1, 2):
    docs = c.collect_documents_for_site(site, 304)
    txt = docs[0].text if hasattr(docs[0], "text") else str(docs[0])
    title = re.search(r"<h1>(.*?)</h1>", txt, re.S)
    issues = re.findall(r"(\d{3})期[:：]（双波中特）", txt)
    print(f"第{i}次: 标题={title.group(1).strip() if title else None} | 双波中特期号={issues} | len={len(txt)}", flush=True)
