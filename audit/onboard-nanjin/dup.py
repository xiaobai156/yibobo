# -*- coding: utf-8 -*-
"""南金东箭 判重：反推缺失波色后与在册 99 站比对。"""
import html, json, re, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

def text_of(d):
    for a in ("text", "content", "html", "raw"):
        v = getattr(d, a, None)
        if isinstance(v, str) and v:
            return v
    return str(d)
TAG = re.compile(r"<[^>]+>")
NJ_RE = re.compile(r"(\d{3})\s*期\s*[:：]\s*【两波中特】\s*〖\s*(红|蓝|绿)波\s*(红|蓝|绿)波\s*〗")

site = c.Site("南金东箭", "https://rujlvxn.ss1zj-ptamt-njsyyf.work:17455/topic/770539.html", "top")
docs = c.collect_documents_for_site(site, 303)
hist = {}
for d in docs:
    plain = html.unescape(TAG.sub("", text_of(d)))
    for m in NJ_RE.finditer(plain):
        issue = int(m.group(1))
        if issue in hist:
            continue
        hist[issue] = c.missing_wave_value(m.group(2) + "波", m.group(3) + "波")

print("历史 =", dict(sorted(hist.items(), reverse=True)), flush=True)
print("有效 =", sum(1 for v in hist.values() if v), "/", len(hist), flush=True)

cache = json.loads((SHA / "recent_10_cache.json").read_text(encoding="utf-8"))
have = [p for p in sorted(hist, reverse=True) if hist[p]]
print("\n可用于判重的期 =", have, flush=True)

full, part = [], []
for name, e in cache["sites"].items():
    d = {int(k): v for k, v in e["data"].items()}
    common = [(p, hist[p], d[p]) for p in have if p in d]
    same = [x for x in common if x[1] == x[2]]
    if len(common) == len(have) and len(same) == len(have):
        full.append((name, len(common)))
    elif len(same) >= 3:
        part.append((name, len(common), len(same), same))

print("完全一致 =", full or "无", flush=True)
print("重合>=3期 =", len(part), flush=True)
for n, nc, ns, sm in sorted(part, key=lambda x: (-x[2], -x[1]))[:10]:
    print(f"   {n}: 共同{nc}期 一致{ns}期 {sm}", flush=True)
