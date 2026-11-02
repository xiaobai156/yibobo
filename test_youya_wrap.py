# -*- coding: utf-8 -*-
"""优雅小树：历史列表绕回旧年同期期号时，只取第一个连续递减段。"""
import sys
from pathlib import Path

SHA = Path(__file__).resolve().parent
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c  # noqa: E402


def _doc(*lines: str) -> str:
    return "\n".join(lines)


CURRENT = _doc(
    "296期【优雅小树】【双波中特】已公开",
    "",
    "优雅小树 发表于 10月22日 22:28:53",
    "",
    "296期:两波中特【蓝波红波】开？00中",
    "",
    "295期:两波中特【绿波蓝波】开兔28准",
    "",
    "294期:两波中特【蓝波绿波】开蛇37准",
    "",
)

OLD_WRAP = _doc(
    "001期:两波中特【红波绿波】开牛29准",
    "",
    "365期:两波中特【红波蓝波】开龙26准",
    "",
    "297期:两波中特【蓝波绿波】开狗44准",
    "",
    "296期:两波中特【蓝波绿波】开牛05准",
    "",
    "295期:两波中特【红波蓝波】开马01准",
    "",
)


def _prepare(docs, site, period=296):
    """复刻 crawl_site 的判定顺序：先判绕回，再截断。"""
    cands = c.extract_primary_candidates(docs, site)
    cands, reason = c._reject_if_wrapped_before_target(cands, period)
    if reason:
        return [], reason
    return c._keep_first_descending_run(cands), None


def test_current_period_not_conflicting_when_old_year_wraps():
    docs = [CURRENT, OLD_WRAP]
    site = c.Site("优雅小树", "https://example.com/topic/1.html", "top", None)
    cands, wrapped_reason = _prepare(docs, site, 296)
    assert wrapped_reason is None
    hits = [x for x in cands if x.issue == 296]
    assert len(hits) == 1, f"296 期应只有 1 条，实际 {[(x.value, x.line) for x in hits]}"
    assert hits[0].value == "绿波"
    assert c.has_conflicting_target_candidates(cands, 296) is False
    sel, reason = c.select_candidate_with_reason(cands, 296, "top")
    assert reason is None
    assert sel is not None and sel.value == "绿波"


def test_history_before_wrap_still_parsed():
    docs = [CURRENT, OLD_WRAP]
    site = c.Site("优雅小树", "https://example.com/topic/1.html", "top", None)
    cands, _ = _prepare(docs, site, 296)
    issues = {x.issue for x in cands}
    assert {296, 295, 294} <= issues
