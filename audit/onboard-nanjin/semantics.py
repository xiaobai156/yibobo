# -*- coding: utf-8 -*-
"""判定：准/错 到底对应『开∈两波』还是『开=第三波』。"""
import html, json, re, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

RED = {1,2,7,8,12,13,18,19,23,24,29,30,34,35,40,45,46}
BLUE = {3,4,9,10,14,15,20,25,26,31,36,37,41,42,47,48}
GREEN = {5,6,11,16,17,21,22,27,28,32,33,38,39,43,44,49}
def color_of(n):
    return "红波" if n in RED else "蓝波" if n in BLUE else "绿波" if n in GREEN else None
NUM = re.compile(r"[鼠牛虎兔龙蛇马羊猴鸡狗猪](\d{1,2})")
def parse_open(s):
    m = NUM.search(s)
    return color_of(int(m.group(1))) if m else None

def text_of(d):
    for a in ("text", "content", "html", "raw"):
        v = getattr(d, a, None)
        if isinstance(v, str) and v:
            return v
    return str(d)
TAG = re.compile(r"<[^>]+>")
WAVES = ["红波", "蓝波", "绿波"]
def third(a, b):
    rest = [w for w in WAVES if w not in (a, b)]
    return rest[0] if len(rest) == 1 else None

def load(site, period, rowre):
    docs = c.collect_documents_for_site(site, period)
    out = {}
    for d in docs:
        plain = html.unescape(TAG.sub("", text_of(d)))
        for m in rowre.finditer(plain):
            issue = int(m.group(1))
            if issue in out:
                continue
            out[issue] = (m.group(2) + "波", m.group(3) + "波",
                          parse_open(m.group(4)), "准" if "准" in m.group(0) else "错")
    return out

NJ_RE = re.compile(r"(\d{3})\s*期\s*[:：]\s*【两波中特】\s*〖\s*(红|蓝|绿)波\s*(红|蓝|绿)波\s*〗\s*开\s*([^准错]{0,12}?)\s*(准|错)")
YG_RE = re.compile(r"(\d{3})期❦两波中特❦【(红|蓝|绿)波防(红|蓝|绿)波】❦开[:：]?\s*([^❦准错]{0,12}?)\s*(准|错)")

cache = json.loads((SHA / "recent_10_cache.json").read_text(encoding="utf-8"))
nj = load(c.Site("南金东箭", "https://rujlvxn.ss1zj-ptamt-njsyyf.work:17455/topic/770539.html", "top"), 303, NJ_RE)
yg = load(c.Site("雨果天气", cache["sites"]["雨果天气"]["url"], "top", keyword="两波中特"), 302, YG_RE)

def report(name, data):
    print("=" * 16, name, len(data), "期", flush=True)
    a = b = 0
    for issue, (w1, w2, drawn, res) in data.items():
        if drawn is None:
            continue
        in_set = drawn in (w1, w2)
        is_third = (third(w1, w2) == drawn)
        if in_set: a += 1
        if is_third: b += 1
    n = sum(1 for v in data.values() if v[2])
    zheng = sum(1 for v in data.values() if v[3] == "准")
    print(f"  有效 {n} 期 | 准 {zheng} 错 {n - zheng}", flush=True)
    print(f"  开∈两波: {a}/{n}  ({a/n:.1%})   开=第三波: {b}/{n} ({b/n:.1%})", flush=True)
    # 逐期一致性
    h1 = sum(1 for v in data.values() if v[2] and ((v[2] in (v[0], v[1])) == (v[3] == "准")))
    h2 = sum(1 for v in data.values() if v[2] and ((third(v[0], v[1]) == v[2]) == (v[3] == "准")))
    print(f"  H1(准⟺开∈两波) 一致 {h1}/{n}   H2(准⟺开=第三波) 一致 {h2}/{n}", flush=True)

report("南金东箭", nj)
report("雨果天气", yg)

print("\n=== 南金东箭 vs 雨果天气 逐期两波对照 ===", flush=True)
for issue in sorted(set(nj) | set(yg), reverse=True)[:10]:
    a = nj.get(issue); b = yg.get(issue)
    print(f"  {issue}: 南金={a[:2] if a else None} 雨果={b[:2] if b else None}", flush=True)
