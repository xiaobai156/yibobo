# -*- coding: utf-8 -*-
"""只读：提取南金东箭「两波中特」历史、反推缺失波色、与在册站判重。"""
import html, json, re, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

URL = "https://rujlvxn.ss1zj-ptamt-njsyyf.work:17455/topic/770539.html"
site = c.Site(name="南金东箭", url=URL, pick="top")
docs = c.collect_documents_for_site(site, 303)

def text_of(d):
    for a in ("text", "content", "html", "raw"):
        v = getattr(d, a, None)
        if isinstance(v, str) and v:
            return v
    return str(d)

TAG = re.compile(r"<[^>]+>")
ROW = re.compile(r"(\d{3})\s*期\s*[:：]\s*【两波中特】\s*〖\s*(红|蓝|绿)波\s*(红|蓝|绿)波\s*〗")

rows, seen = [], set()
for d in docs:
    plain = html.unescape(TAG.sub("", text_of(d)))
    for m in ROW.finditer(plain):
        issue = int(m.group(1))
        w1, w2 = m.group(2) + "波", m.group(3) + "波"
        if issue in seen:
            continue
        seen.add(issue)
        miss = c.missing_wave_value(w1, w2)
        rows.append((issue, w1, w2, miss))

rows.sort(key=lambda r: -r[0])
print("期数 =", len(rows), flush=True)
for issue, w1, w2, miss in rows:
    print(f"  {issue}: {w1}+{w2} -> 缺 {miss}", flush=True)

hist = {i: m for i, _, _, m in rows}
print("\n有效历史(反推成功) =", len([v for v in hist.values() if v]), flush=True)

# 与雨果天气对比
cache = json.loads((SHA / "recent_10_cache.json").read_text(encoding="utf-8"))
yg = cache["sites"].get("雨果天气", {})
ygd = {int(k): v for k, v in yg.get("data", {}).items()}
print("\n雨果天气缓存 =", dict(sorted(ygd.items(), reverse=True)), flush=True)
cmp = [(i, hist.get(i), ygd.get(i)) for i in sorted(set(hist) | set(ygd), reverse=True)]
print("期 | 南金东箭 | 雨果天气")
for i, a, b in cmp[:15]:
    flag = "" if (a == b) else "  <<不同"
    print(f"  {i}: {a} | {b}{flag}", flush=True)
same = sum(1 for i, a, b in cmp if a and b and a == b)
both = sum(1 for i, a, b in cmp if a and b)
print(f"共同期 {both} 个，一致 {same} 个", flush=True)
