# -*- coding: utf-8 -*-
"""自强不息（zqbx）专属解析回归：帖子是「每期在顶部追加一行」的累计序列，跨年时序列在
001→365 处回卷。回卷之后的行属于上一轮，期号标签与本轮相同但并非本期数据（273 期形态：
顶部 273 期未开行 + 底部上一轮 273 期已开行），必须只取本轮候选，不能据此判冲突。"""
from __future__ import annotations

import sha_yibo_crawler as crawler

ZQBX = crawler.Site(
    "自强不息",
    "https://pjaliv.o53jc-9p80e-xxbelu.xyz:16677/topic/625967.html",
    "top",
)
OTHER_IFRAME_SITE = crawler.Site(
    "宁静致远",
    "https://pjaliv.o53jc-9p80e-xxbelu.xyz:16677/topic/625495.html",
    "top",
)

# 273 期真实页面形态（缩短到关键行）：本轮 273（未开，开：0000）→ 272/271 → … → 001，
# 回卷后是上一轮 365 → 364 → … → 上一轮 273（已开：虎04 准）。
ROLLOVER_BODY = "\n".join(
    [
        "杀肖区 273期: 自强不息「绝杀一波」",
        "273期:【绝杀一波】【绿波】开：0000准",
        "272期:【绝杀一波】【红波】开：蛇02错",
        "271期:【绝杀一波】【蓝波】开：猴35准",
        "001期:【绝杀一波】【红波】开：牛29错",
        "365期:【绝杀一波】【绿波】开：龙26准",
        "364期:【绝杀一波】【蓝波】开：马12准",
        "273期:【绝杀一波】【红波】开：虎04准",
    ]
)

CACHE_SERIES_272_TO_264 = {
    272: "红波",
    271: "蓝波",
    270: "绿波",
    269: "红波",
    268: "蓝波",
    267: "绿波",
    266: "红波",
    265: "蓝波",
    264: "绿波",
}


def select(body: str, site: crawler.Site, issue: int):
    candidates = crawler.extract_primary_candidates([body], site)
    return candidates, crawler.select_candidate_with_reason(candidates, issue, site.pick)


def test_rollover_keeps_only_current_cycle_candidates():
    candidates, (candidate, reason) = select(ROLLOVER_BODY, ZQBX, 273)

    assert [(item.issue, item.value) for item in candidates if item.issue == 273] == [(273, "绿波")]
    assert all(item.issue != 365 for item in candidates)
    assert reason is None
    assert candidate is not None and candidate.value == "绿波"


def test_previous_cycle_row_is_not_used_as_current_period():
    """上一轮 365 期行不得当作本轮 365 期：本期尚未发布时只能报未找到。"""
    candidates, (candidate, reason) = select(ROLLOVER_BODY, ZQBX, 365)

    assert candidates and all(item.issue <= 273 for item in candidates)
    assert candidate is None
    assert reason == "未找到指定期数"


def test_current_cycle_history_matches_cache():
    body = "\n".join(["杀肖区 273期: 自强不息「绝杀一波」"] + [
        "273期:【绝杀一波】【绿波】开：0000准",
        *[f"{issue}期:【绝杀一波】【{value}】开：鼠01准" for issue, value in CACHE_SERIES_272_TO_264.items()],
        "001期:【绝杀一波】【红波】开：牛29错",
        "365期:【绝杀一波】【绿波】开：龙26准",
        "364期:【绝杀一波】【蓝波】开：马12准",
        "273期:【绝杀一波】【红波】开：虎04准",
    ])

    candidates = crawler.extract_primary_candidates([body], ZQBX)
    history = crawler.build_site_history(candidates, ZQBX.pick, 10)

    for issue, value in CACHE_SERIES_272_TO_264.items():
        assert history[issue] == value, issue
    assert history[273] == "绿波"


def test_other_iframe_site_still_fails_on_same_period_conflict():
    """回卷只豁免自强不息；同模板其他站点出现同期两条不同波色仍必须判冲突。"""
    candidates, (candidate, reason) = select(ROLLOVER_BODY, OTHER_IFRAME_SITE, 273)

    assert {item.value for item in candidates if item.issue == 273} == {"绿波", "红波"}
    assert candidate is None
    assert reason == "指定期数存在多条冲突数据"


def test_normal_page_without_rollover_still_resolves():
    body = "\n".join(
        [
            "杀肖区 272期: 自强不息「绝杀一波」",
            "272期:【绝杀一波】【红波】开：0000准",
            "271期:【绝杀一波】【蓝波】开：猴35准",
            "270期:【绝杀一波】【绿波】开：鼠19准",
        ]
    )

    candidates, (candidate, reason) = select(body, ZQBX, 272)

    assert reason is None
    assert candidate is not None and candidate.value == "红波"
    assert [item.issue for item in candidates] == [272, 271, 270]
