# -*- coding: utf-8 -*-
"""用『开』的结果反推两个站的两波格式语义。"""
import html, json, re, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

# 六合彩波色表
RED = {1,2,7,8,12,13,18,19,23,24,29,30,34,35,40,45,46}
BLUE = {3,4,9,10,14,15,20,25,26,31,36,37,41,42,47,48}
GREEN = {5,6,11,16,17,21,22,27,28,32,33,38,39,43,44,49}
def color_of(n):
    if n in RED: return "红波"
    if n in BLUE: return "蓝波"
    if n in GREEN: return "绿波"
    return None

ZODIAC = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
NUM = re.compile(r"[鼠牛虎兔龙蛇马羊猴鸡狗猪](\d{1,2})")

def parse_open(s):
    m = NUM.search(s)
    if not m:
        return None
    return color_of(int(m.group(1)))

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
            w1, w2 = m.group(2) + "波", m.group(3) + "波"
            tail = plain[m.end():m.end() + 30]
            res = "准" if "准" in tail else ("错" if "错" in tail else "?")
            out[issue] = (w1, w2, parse_open(tail), res)
    return out

# 南金东箭
nj = load(c.Site("南金东箭", "https://rujlvxn.ss1zj-ptamt-njsyyf.work:17455/topic/770539.html", "top"),
          303, re.compile(r"(\d{3})\s*期\s*[:：]\s*【两波中特】\s*〖\s*(红|蓝|绿)波\s*(红|蓝|绿)波\s*〗"))

# 雨果天气
cache = json.loads((SHA / "recent_10_cache.json").read_text(encoding="utf-8"))
yg_url = cache["sites"]["雨果天气"]["url"]
yg = load(c.Site("雨果天气", yg_url, "top", keyword="两波中特"),
          302, re.compile(r"(\d{3})期❦两波中特❦【(红|蓝|绿)波防(红|蓝|绿)波】"))

WAVES = ["红波", "蓝波", "绿波"]
def third(a, b):
    rest = [w for w in WAVES if w != a and w != b]
    return rest[0] if len(rest) == 1 else None

def test(name, data):
    print("=" * 18, name, "共", len(data), "期", flush=True)
    hyps = {
        "first":  lambda w1, w2: w1,
        "second": lambda w1, w2: w2,
        "third":  lambda w1, w2: third(w1, w2),
    }
    for hname, fn in hyps.items():
        ok = bad = 0
        for issue, (w1, w2, drawn, res) in data.items():
            if drawn is None or res == "?":
                continue
            pred = fn(w1, w2)
            hit = (pred == drawn)
            if (hit and res == "准") or ((not hit) and res == "错"):
                ok += 1
            else:
                bad += 1
        print(f"  {hname:7s} 吻合 {ok} / 矛盾 {bad}", flush=True)
    # 抽样
    for issue in sorted(data, reverse=True)[:6]:
        w1, w2, drawn, res = data[issue]
        print(f"    {issue}: {w1} {w2} | 开 {drawn} | {res} | 缺={third(w1,w2)}", flush=True)

test("南金东箭", nj)
test("雨果天气", yg)
