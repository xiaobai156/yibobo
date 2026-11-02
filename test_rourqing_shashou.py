# -*- coding: utf-8 -*-
"""柔情杀手专属解析回归测试：走用户发布接口，而不是列表页预览文本。"""
from __future__ import annotations

import contextlib

import pytest

import sha_yibo_crawler as crawler

SITE = crawler.Site(
    "柔情杀手",
    "https://macqvc.shinengwenhua.com:8443/#/user/1413954",
    "bottom",
)

DESCRIPTION_261 = (
    "250期【柔情杀手】【绝杀绿波】T14√ 251期【柔情杀手】【绝杀蓝波】T30√ "
    "252期【柔情杀手】【绝杀绿波】T22X 253期【柔情杀手】【绝杀红波】T16√ "
    "254期【柔情杀手】【绝杀蓝波】T02√ 255期【柔情杀手】【绝杀绿波】T44X "
    "256期【柔情杀手】【绝杀红波】T01X 257期【柔情杀手】【绝杀蓝波】T07√ "
    "258期【柔情杀手】【绝杀绿波】T46√ 259期【柔情杀手】【绝杀蓝波】T22√ "
    "260期【柔情杀手】【绝杀红波】T20√ 261期【柔情杀手】【绝杀绿波】T00√"
)
DESCRIPTION_267 = "266期【柔情杀手】【绝杀蓝波】T08√ 267期【柔情杀手】【绝杀绿波】T00√"


def make_record(issue: int, description: str, **overrides) -> dict:
    record = {
        "id": 42200000 + issue,
        "userId": 1413954,
        "number": issue,
        "periodStr": str(issue),
        "title": "【柔情杀手】精准绝杀《绝杀一波》",
        "description": description,
    }
    record.update(overrides)
    return record


def make_payload(records: list[dict]) -> dict:
    return {"code": 10000, "success": True, "data": {"list": records}}


@pytest.fixture
def fake_api(monkeypatch):
    calls: list[str] = []

    @contextlib.contextmanager
    def fake_browser_page():
        yield object()

    def install(records: list[dict]) -> None:
        monkeypatch.setattr(crawler, "_browser_page", fake_browser_page)
        monkeypatch.setattr(crawler, "open_qvuuqs_page", lambda page, url, timeout: None)

        def fake_fetch(page, path):
            calls.append(path)
            return make_payload(records)

        monkeypatch.setattr(crawler, "fetch_qvuuqs_json", fake_fetch)

    install.calls = calls  # type: ignore[attr-defined]
    return install


def test_collects_target_period_from_publish_api(fake_api):
    fake_api([make_record(267, DESCRIPTION_267), make_record(261, DESCRIPTION_261)])

    documents = crawler.collect_rourqing_shashou_documents(SITE, 267)

    assert documents == [DESCRIPTION_267]
    assert fake_api.calls == [
        "/unite49/h5/userHomePage/userPublish?userId=1413954&type=3&pageNum=1"
        "&title=&newVersion=1&lotteryType=0"
    ]
    candidates = crawler.extract_primary_candidates(documents, SITE)
    candidate, reason = crawler.select_candidate_with_reason(candidates, 267, SITE.pick)
    assert reason is None
    assert candidate is not None and candidate.value == "绿波"


def test_history_matches_cached_values(fake_api):
    fake_api([make_record(267, DESCRIPTION_267), make_record(261, DESCRIPTION_261)])

    documents = crawler.collect_rourqing_shashou_documents(SITE, None)
    history = crawler.build_site_history(
        crawler.extract_primary_candidates(documents, SITE), SITE.pick, 10
    )

    assert history[267] == "绿波"
    assert history[258] == "绿波"
    assert history[259] == "蓝波"
    assert history[260] == "红波"
    assert history[261] == "绿波"


def test_missing_period_is_failure_not_fallback(fake_api):
    fake_api([make_record(261, DESCRIPTION_261)])

    with pytest.raises(ValueError, match="未找到指定期数"):
        crawler.collect_rourqing_shashou_documents(SITE, 267)


def test_author_id_mismatch_is_rejected(fake_api):
    fake_api([make_record(267, DESCRIPTION_267, userId=999999)])

    with pytest.raises(ValueError, match="作者ID不匹配"):
        crawler.collect_rourqing_shashou_documents(SITE, 267)


def test_column_mismatch_is_rejected(fake_api):
    fake_api([make_record(267, DESCRIPTION_267, title="【柔情杀手】其它栏目")])

    with pytest.raises(ValueError, match="栏目不匹配"):
        crawler.collect_rourqing_shashou_documents(SITE, 267)


def test_body_without_own_period_is_rejected(fake_api):
    fake_api([make_record(267, DESCRIPTION_261)])

    with pytest.raises(ValueError, match="未包含自身期数"):
        crawler.collect_rourqing_shashou_documents(SITE, 267)


def test_conflicting_same_period_is_rejected(fake_api):
    fake_api(
        [
            make_record(267, DESCRIPTION_267),
            make_record(267, "267期【柔情杀手】【绝杀红波】T00√", id=42209999),
        ]
    )

    with pytest.raises(ValueError, match="多条冲突文章"):
        crawler.collect_rourqing_shashou_documents(SITE, 267)


def test_collect_documents_for_site_routes_to_publish_api(fake_api):
    fake_api([make_record(267, DESCRIPTION_267)])

    assert crawler.collect_documents_for_site(SITE, 267) == [DESCRIPTION_267]
