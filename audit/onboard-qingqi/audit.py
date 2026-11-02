# -*- coding: utf-8 -*-
"""清气若兰：反推缺失波色 + 与在册 99 站判重。"""
import html, json, re, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

URL = "https://xaglnyad.vjs6a-uv2o4-cxagtq.work:17477/topic/453196.html"
site = c.Site("清气若兰", URL, "top")
docs = c.collect_documents_for_site(site, 303)

def text_of(d):
    for a in ("text", "content", "html", "raw"):
        v = getattr(d, a, None)
        if isinstance(v, str) and v:
            return v
    return str(d)
TAG = re.compile(r"<[^>]+>")
ROW = re.compile(r"(\d{3})\s*期\s*双波中特\s*《\s*(红|蓝|绿)波\s*(红|蓝|绿)波\s*》\s*开\s*([^准错]{0,10}?)\s*(准|错)")

hist, pairs, conflict = {}, {}, []
for d in docs:
    plain = html.unescape(TAG.sub("", text_of(d)))
    for m in ROW.finditer(plain):
        issue = int(m.group(1))
        w1, w2 = m.group(2) + "波", m.group(3) + "波"
        if issue in pairs:
            if pairs[issue] != (w1, w2):
                conflict.append((issue, pairs[issue], (w1, w2)))
            continue
        pairs[issue] = (w1, w2)
        hist[issue] = c.missing_wave_value(w1, w2)

print("期数 =", len(hist), "| 冲突 =", conflict or "无", flush=True)
print("最新 10 期 =", [(k, pairs[k], hist[k]) for k in sorted(hist, reverse=True)[:10]], flush=True)
print("最旧 3 期 =", [(k, pairs[k], hist[k]) for k in sorted(hist)[:3]], flush=True)
print("有效反推 =", sum(1 for v in hist.values() if v), "/", len(hist), flush=True)
gaps = [(a, b) for a, b in zip(sorted(hist), sorted(hist)[1:]) if b - a != 1]
print("断档 =", gaps[:8], "共", len(gaps), flush=True)

cache = json.loads((SHA / "recent_10_cache.json").read_text(encoding="utf-8"))
have = [p for p in sorted(hist, reverse=True) if hist[p]]
print("\n判重窗口 =", have, flush=True)
print("本站窗口值 =", [hist[p] for p in have], flush=True)

full, part = [], []
for name, e in cache["sites"].items():
    d = {int(k): v for k, v in e["data"].items()}
    common = [(p, hist[p], d[p]) for p in have if p in d]
    same = [x for x in common if x[1] == x[2]]
    if common and len(same) == len(common) == len(have):
        full.append(name)
    elif len(same) >= 3:
        part.append((name, len(common), len(same), same))

print("完全一致 =", full or "无", flush=True)
print("重合>=3期 =", len(part), flush=True)
for n, nc, ns, sm in sorted(part, key=lambda x: (-x[2], -x[1]))[:8]:
    print(f"   {n}: 共同{nc} 一致{ns} {sm}", flush=True)
