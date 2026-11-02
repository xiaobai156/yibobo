# -*- coding: utf-8 -*-
"""修正封存落盘的换行风格（字节级，恢复到原文件行尾）。

问题：archive_gongshisha.py 用 Path.write_text 写盘，Windows 文本模式把 LF 翻译成 CRLF，
导致 sites.json（原本混合行尾 492 CRLF / 524 LF）被整体改成 CRLF，
archived_sites.json（原本纯 LF）也被改成 CRLF。内容无损，但超出「最小改动」。

修正：从 before/ 原始字节出发做字节级替换，其余字节逐字节保持不变。
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHA = HERE.parent
BEFORE = HERE / "before"
NAME = "公式杀"

# ---- sites.json：字节级删除条目块 ----
sites_before = (BEFORE / "sites.json").read_bytes()
text = sites_before.decode("utf-8")
lines = text.splitlines(keepends=True)
name_idx = next(i for i, line in enumerate(lines) if line.strip() == f'"name": "{NAME}",')
start_idx = next(i for i in range(name_idx, -1, -1) if lines[i].strip() == "{")
end_idx = next(i for i in range(name_idx, len(lines)) if lines[i].strip() in ("},", "}"))
start = sum(len(x) for x in lines[:start_idx])
end = start + sum(len(x) for x in lines[start_idx : end_idx + 1])
block = text[start:end]
assert NAME in block and "https://tetinte.nzxzd-cfket-xtgznp.xyz:16677/" in block, block
sites_target_text = text[:start] + text[end:]
sites_target = sites_target_text.encode("utf-8")
sites_parsed = json.loads(sites_target.decode("utf-8"))
assert len(sites_parsed) == 99 and all(s["name"] != NAME for s in sites_parsed)
assert sites_target_text[:start] == text[:start] and sites_target_text[start:] == text[end:]
(SHA / "sites.json").write_bytes(sites_target)

# ---- archived_sites.json：追加条目，保持纯 LF、无尾换行 ----
archive_text = (BEFORE / "archived_sites.json").read_text(encoding="utf-8")
archive_before = json.loads(archive_text)
cache_before = json.loads((BEFORE / "recent_10_cache.json").read_text(encoding="utf-8"))
old_entry = cache_before["sites"][NAME]
existing = json.loads((SHA / "archived_sites.json").read_text(encoding="utf-8"))
new_entry = existing["sites"][-1]
assert new_entry["name"] == NAME and len(existing["sites"]) == 13
entry_text = json.dumps(new_entry, ensure_ascii=False, indent=2)
entry_text = "\n".join("    " + line if i else line for i, line in enumerate(entry_text.splitlines()))
tail_anchor = "\n  ]\n}"
assert archive_text.endswith(tail_anchor), repr(archive_text[-16:])
archive_target = archive_text[: -len(tail_anchor)] + ",\n" + entry_text + tail_anchor
archived_parsed = json.loads(archive_target)
assert [s["name"] for s in archived_parsed["sites"]] == [s["name"] for s in archive_before["sites"]] + [NAME]
(SHA / "archived_sites.json").write_text(archive_target, encoding="utf-8", newline="\n")
# 上一行是「追加」写法，必须确认前 12 条与顶层字段原文未动
assert archive_target.startswith(archive_text[: -len(tail_anchor)]), "前缀被改动"

print("== 修正后 ==")
for name in ("sites.json", "recent_10_cache.json", "archived_sites.json"):
    b = (SHA / name).read_bytes()
    b0 = (BEFORE / name).read_bytes()
    print(f"  {name}: size={len(b)} (before {len(b0)}) crlf={b.count(bytes([13, 10]))} "
          f"lf={b.count(bytes([10]))} tail={b[-10:]!r}")
print("  sites.json 站点数:", len(sites_parsed), "；archived 条目数:", len(archived_parsed["sites"]))
