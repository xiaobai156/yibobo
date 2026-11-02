# -*- coding: utf-8 -*-
"""封存后验收：① 99 站配置可正常加载并单站跑通当期；② 现场复核 桃花没酒 290 是否已发布。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHA = HERE.parent
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c  # noqa: E402

PERIOD = 290
sites = c.load_sites(SHA / "sites.json")
print(f"load_sites -> {len(sites)} 站；公式杀 在册: {any(s.name == '公式杀' for s in sites)}")

target = next(s for s in sites if s.name == "针锋相对")
(HERE / "sites_check.json").write_text(json.dumps([{"name": target.name, "url": target.url, "pick": target.pick}], ensure_ascii=False, indent=2), encoding="utf-8")
print("单站隔离跑验收（针锋相对）：见 run_check\\")

site = next(s for s in sites if s.name == "桃花没酒")
print(f"\n桃花没酒 现场复核（pick={site.pick}）")
t0 = time.time()
docs = c.collect_documents_for_site(site, PERIOD)
print(f"  抓取 OK {round(time.time()-t0,2)}s docs={[len(d) for d in docs]}")
cands = c.extract_primary_candidates(docs, site)
issues = sorted({x.issue for x in cands})
hits = [x for x in cands if x.issue == PERIOD]
print(f"  候选={len(cands)} 期号区间={issues[:2]}…{issues[-2:]} {PERIOD}候选="
      f"{[(x.issue, x.value, x.line) for x in hits]} select={c.select_candidate_with_reason(cands, PERIOD, site.pick)}")
for ln in [l.strip() for l in c.plain_lines(docs) if str(PERIOD) in l or "绝杀一波" in l][:6]:
    print("   ", ln[:140])
print("\nDONE")
