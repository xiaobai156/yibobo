# -*- coding: utf-8 -*-
"""补 雨果天气 302 = 蓝波，写缓存并重建 302期-一波.txt，清失败文件。"""
import json, sys
from pathlib import Path
SHA = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波")
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c

PERIOD, NAME, VALUE = 302, "雨果天气", "蓝波"
CACHE = c.DEFAULT_CACHE_FILE
TXT = c.DEFAULT_OUTPUT_DIR / f"{PERIOD}期-一波.txt"
FAIL = c.DEFAULT_FAILURE_OUTPUT_DIR / f"{PERIOD}期-杀一波-失败.txt"

data = json.loads(CACHE.read_text(encoding="utf-8"))
entry = data["sites"][NAME]
print("改前 data[302] =", entry["data"].get("302"), flush=True)
entry["data"][str(PERIOD)] = VALUE
c.atomic_write_json(CACHE, data)
print("缓存已写:", json.loads(CACHE.read_text(encoding="utf-8"))["sites"][NAME]["data"].get("302"), flush=True)

# 从缓存重建 TXT
cached = json.loads(CACHE.read_text(encoding="utf-8"))
results = []
for key, e in cached["sites"].items():
    v = e.get("data", {}).get(str(PERIOD))
    if v:
        results.append(c.SuccessResult(e["name"], v, e.get("url")))
print("有 302 值的站 =", len(results), "/", len(cached["sites"]), flush=True)

if TXT.exists():
    TXT.unlink()
merged = c.write_success_results(TXT, results)
print("TXT 条数 =", len(merged), "| 文件 =", TXT, flush=True)

text = TXT.read_text(encoding="utf-8")
lines = text.splitlines()
print("行数 =", len(lines), "| 首行 =", lines[0], flush=True)
print("雨果天气行 =", [l for l in lines if NAME in l], flush=True)
print("排名区 =", lines[-4:], flush=True)

if FAIL.exists():
    FAIL.unlink()
    print("失败TXT 已删除", flush=True)
else:
    print("失败TXT 本就不存在", flush=True)

# 校验
parsed = c.parse_success_results(text)
names = [r.name for r in parsed]
print("重名 =", [n for n in set(names) if names.count(n) > 1] or "无", flush=True)
from collections import Counter
print("排行合计 =", sum(Counter(r.value for r in parsed).values()), "明细 =", len(parsed), flush=True)
