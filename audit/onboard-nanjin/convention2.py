# -*- coding: utf-8 -*-
"""严格行内解析，判定两波格式语义。"""
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

def load(site, period, rowre):
    docs = c.collect_documents_for_site(site, period)
    out = {}
    for d in docs:
        plain = html.unescape(TAG.sub("", text_of(d)))
        for m in rowre.finditer(plain):
            issue = int(m.group(1))
            if issue in out:
                continue
            openstr = m.group(4)
            res = "准" if "准" in m.group(0) else ("错" if "错" in m.group(0) else "?")
            out[issue] = (m.group(2) + "波", m.group(3) + "波", parse_open(openstr), res, openstr)
    return out

NJ_RE = re.compile(r"(\d{3})\s*期\s*[:：]\s*【两波中特】\s*〖\s*(红|蓝|绿)波\s*(红|蓝|绿)波\s*〗\s*开\s*([^准错]{0,12}?)\s*(准|错)")
YG_RE = re.compile(r"(\d{3})期❦两波中特❦【(红|蓝|绿)波防(红|蓝|绿)波】❦开[:：]?\s*([^❦准错]{0,12}?)\s*(准|错)")

nj = load(c.Site("南金东箭", "https://rujlvxn.ss1zj-ptamt-njsyyf.work:17455/topic/770539.html", "top"), 303, NJ_RE)
cache = json.loads((SHA / "recent_10_cache.json").read_text(encoding="utf-8"))
yg = load(c.Site("雨果天气", cache["sites"]["雨果天气"]["url"], "top", keyword="两波中特"), 302, YG_RE)

WAVES = ["红波", "蓝波", "绿波"]
def third(a, b):
    rest = [w for w in WAVES if w not in (a, b)]
    return rest[0] if len(rest) == 1 else None

def test(name, data):
    print("=" * 16, name, len(data), "期", flush=True)
    for issue in sorted(data, reverse=True)[:8]:
        w1, w2, drawn, res, raw = data[issue]
        print(f"  {issue}: {w1}+{w2} 开[{raw.strip()}]={drawn} {res} | 缺={third(w1,w2)}", flush=True)
    for hname, fn in {"first": lambda a,b: a, "second": lambda a,b: b, "third": lambda a,b: third(a,b)}.items():
        ok = bad = skip = 0
        for issue, (w1, w2, drawn, res, raw) in data.items():
            if drawn is None or res == "?":
                skip += 1; continue
            hit = fn(w1, w2) == drawn
            if (hit and res == "准") or ((not hit) and res == "错"): ok += 1
            else: bad += 1
        print(f"   {hname:7s} 吻合 {ok} 矛盾 {bad} 跳过 {skip}", flush=True)

test("南金东箭", nj)
test("雨果天气", yg)
