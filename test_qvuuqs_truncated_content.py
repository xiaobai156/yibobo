# -*- coding: utf-8 -*-
"""用户页列表正文被截断时的回退测试：列表正文缺少目标期必须改取文章详情。"""
from __future__ import annotations

import contextlib

import pytest

import sha_yibo_crawler as crawler

SITE = crawler.Site(
    "拥挤门",
    "https://qvuuqqs.8imf7-hteuh-ylwuqv.xyz/#/users/1504",
    "bottom",
    keyword="绝杀一波",
)

RECORD_ID = 16370620
TRUNCATED_CONTENT = (
    "<p>239期:绝杀一波【红波】开:虎05准</p>"
    "<p>240期:绝杀一波【绿波】开:龙27错</p>"
    "<p>241期:绝杀一波【红波】开:马49准</p>"
)
FULL_CONTENT = (
    "<p>313期:绝杀一波【绿波】开:鼠43错</p>"
    "<p>314期:绝杀一波【绿波】开:？00准</p>"
)


def make_list_record(content: str) -> dict:
    return {
        "id": RECORD_ID,
        "user_id": 1504,
        "draw": 314,
        "title": "绝杀一波",
        "content": content,
    }


def make_detail(content: str) -> dict:
    return {
        "data": {
            "id": RECORD_ID,
            "user_id": 1504,
            "draw": 314,
            "title": "绝杀一波",
            "content": content,
        }
    }


@pytest.fixture
def fake_api(monkeypatch):
    calls: list[str] = []

    @contextlib.contextmanager
    def fake_browser_page():
        yield object()

    def install(list_content: str, detail_content: str) -> None:
        monkeypatch.setattr(crawler, "_browser_page", fake_browser_page)
        monkeypatch.setattr(crawler, "open_qvuuqs_page", lambda page, url, timeout: None)

        def fake_fetch(page, path):
            calls.append(path)
            if path == "/api/v1/forums/16370620":
                return make_detail(detail_content)
            if "/references" in path:
                return {"data": [make_list_record(list_content)]}
            return {"data": []}

        monkeypatch.setattr(crawler, "fetch_qvuuqs_json", fake_fetch)

    install.calls = calls  # type: ignore[attr-defined]
    return install


def test_truncated_list_content_uses_forum_detail(fake_api):
    fake_api(TRUNCATED_CONTENT, FULL_CONTENT)

    documents = crawler.collect_qvuuqs_user_documents(SITE, 314)

    assert documents == [FULL_CONTENT]
    assert "/api/v1/forums/16370620" in fake_api.calls
    candidates = crawler.extract_exact_sha_yibo_candidates(documents)
    values = {item.issue: item.value for item in candidates}
    assert values[314] == "绿波"
    assert 239 not in values


def test_complete_list_content_skips_detail(fake_api):
    fake_api(FULL_CONTENT, FULL_CONTENT)

    documents = crawler.collect_qvuuqs_user_documents(SITE, 314)

    assert documents == [FULL_CONTENT]
    assert "/api/v1/forums/16370620" not in fake_api.calls


def test_detail_without_target_period_is_failure(fake_api):
    fake_api(TRUNCATED_CONTENT, TRUNCATED_CONTENT)

    with pytest.raises(ValueError, match="未找到指定期数|期数不匹配"):
        crawler.collect_qvuuqs_user_documents(SITE, 314)
