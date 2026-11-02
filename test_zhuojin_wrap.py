# -*- coding: utf-8 -*-
"""捉襟见肘：历史列表绕回旧年同期期号时，只取第一个连续递减段。

复现：页面历史列表 001→365 后继续递减到 295（去年），与本轮 295（开0000）撞车，
原实现产出两条 295 候选（蓝波/红波），被统一校验判「指定期数存在多条冲突数据」。
"""
import sys
from pathlib import Path

import pytest

SHA = Path(__file__).resolve().parent
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c  # noqa: E402


def _doc(*lines: str) -> str:
    return "\n".join(lines)


CURRENT = _doc(
    "295期: 捉襟见肘《两波中特》意想丰收",
    "",
    "捉襟见肘 发表于 10月22日 12:08:35",
    "",
    "295期《两波中特》《绿波红波》开0000准",
    "",
    "294期《两波中特》《红波绿波》开兔28准",
    "",
    "293期《两波中特》《绿波红波》开蛇37准",
    "",
)

OLD_WRAP = _doc(
    "001期《两波中特》《绿波红波》开牛29准",
    "",
    "365期《两波中特》《红波蓝波》开龙26准",
    "",
    "296期《两波中特》《绿波蓝波》开猴22准",
    "",
    "295期《两波中特》《蓝波绿波》开牛05准",
    "",
    "294期《两波中特》《红波蓝波》开马01准",
    "",
)


def _prepare(docs, site, period=295):
    """复刻 crawl_site 的判定顺序：先判绕回，再截断。"""
    cands = c.extract_primary_candidates(docs, site)
    cands, reason = c._reject_if_wrapped_before_target(cands, period)
    if reason:
        return [], reason
    return c._keep_first_descending_run(cands), None


def test_current_period_not_conflicting_when_old_year_wraps():
    """绕回段里的旧 295 不应污染本期 295。"""
    docs = [CURRENT, OLD_WRAP]
    site = c.Site("捉襟见肘", "https://example.com/topic/1.html", "top", None)
    cands, wrapped_reason = _prepare(docs, site, 295)
    assert wrapped_reason is None
    hits = [x for x in cands if x.issue == 295]
    assert len(hits) == 1, f"295 期应只有 1 条候选，实际 {[(x.value, x.line) for x in hits]}"
    assert hits[0].value == "蓝波"
    assert c.has_conflicting_target_candidates(cands, 295) is False
    sel, reason = c.select_candidate_with_reason(cands, 295, "top")
    assert reason is None
    assert sel is not None and sel.value == "蓝波"


def test_history_before_wrap_still_parsed():
    """绕回段之前的正常历史仍要保留。"""
    docs = [CURRENT, OLD_WRAP]
    site = c.Site("捉襟见肘", "https://example.com/topic/1.html", "top", None)
    cands, _ = _prepare(docs, site, 295)
    issues = {x.issue for x in cands}
    assert {295, 294, 293} <= issues
    assert 365 in issues or 1 in issues
