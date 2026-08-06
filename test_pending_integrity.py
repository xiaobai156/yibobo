# -*- coding: utf-8 -*-
from __future__ import annotations

import json

import pytest

import check_pending_against_cache as pending_check
import sha_yibo_crawler as crawler


def site(name: str, url: str = "https://new.example/topic/1", pick: str = "top") -> crawler.Site:
    return crawler.Site(name, url, pick)


def run_main(monkeypatch, tmp_path, pending, existing, predictions, cache):
    cache_file = tmp_path / "recent_10_cache.json"
    report_file = tmp_path / "pending_cache_check.json"
    cache_file.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(pending_check, "CACHE_FILE", cache_file)
    monkeypatch.setattr(pending_check, "REPORT_FILE", report_file)
    monkeypatch.setattr(pending_check, "load_pending", lambda: pending)
    monkeypatch.setattr(pending_check, "load_existing_sites", lambda: existing)

    def fake_collect(candidate):
        result = predictions[candidate.name]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(pending_check, "collect_site_pred", fake_collect)
    exit_code = pending_check.main()
    return exit_code, json.loads(report_file.read_text(encoding="utf-8"))


def test_normalize_url_handles_host_case_trailing_slash_and_anchor_fragment() -> None:
    assert pending_check.normalize_site_url("HTTPS://Example.COM/topic/42/#section") == (
        pending_check.normalize_site_url("https://example.com/topic/42")
    )


def test_normalize_url_keeps_topic_path_query_and_hash_route_distinct() -> None:
    base = pending_check.normalize_site_url("https://example.com/topic/42?id=1")
    assert base != pending_check.normalize_site_url("https://example.com/topic/43?id=1")
    assert base != pending_check.normalize_site_url("https://example.com/topic/42?id=2")
    assert pending_check.normalize_site_url("https://example.com/#/users/1") != (
        pending_check.normalize_site_url("https://example.com/#/users/2")
    )


def test_normalize_url_removes_default_http_and_https_ports() -> None:
    assert pending_check.normalize_site_url("https://example.com:443/topic/42") == (
        pending_check.normalize_site_url("https://example.com/topic/42")
    )
    assert pending_check.normalize_site_url("http://example.com:80/topic/42") == (
        pending_check.normalize_site_url("http://example.com/topic/42")
    )
    assert pending_check.normalize_site_url("https://example.com:8443/topic/42") != (
        pending_check.normalize_site_url("https://example.com/topic/42")
    )


def test_same_normalized_url_rejects_different_name_and_reports_existing_site() -> None:
    candidate = site("新名字", "HTTPS://Example.COM/topic/42/#anchor")
    existing = [site("已有站", "https://example.com/topic/42")]

    rejection = pending_check.find_existing_rejection(candidate, existing)

    assert rejection["status"] == "duplicate_url"
    assert rejection["existing_site"] == "已有站"


def test_collect_site_pred_rejects_empty_and_conflicting_period(monkeypatch) -> None:
    candidate = site("候选")
    monkeypatch.setattr(pending_check.crawler, "collect_documents_for_site", lambda _site: ["raw"])
    monkeypatch.setattr(pending_check.crawler, "missing_primary_reason", lambda _site: "没有有效数据")
    monkeypatch.setattr(pending_check.crawler, "extract_primary_candidates", lambda _docs, _site: [])
    with pytest.raises(ValueError, match="没有有效数据"):
        pending_check.collect_site_pred(candidate)

    conflicting = [
        crawler.Candidate(191, "红波", "191期红波", 0),
        crawler.Candidate(191, "蓝波", "191期蓝波", 1),
    ]
    monkeypatch.setattr(pending_check.crawler, "extract_primary_candidates", lambda _docs, _site: conflicting)
    with pytest.raises(ValueError, match="191.*冲突"):
        pending_check.collect_site_pred(candidate)


def test_collect_site_pred_ignores_conflict_older_than_candidate_near_ten(monkeypatch) -> None:
    candidate = site("候选")
    candidates = [
        crawler.Candidate(period, "红波", f"{period}期红波", index)
        for index, period in enumerate(range(191, 181, -1))
    ]
    candidates.extend(
        [
            crawler.Candidate(181, "红波", "181期红波", 10),
            crawler.Candidate(181, "蓝波", "181期蓝波", 11),
        ]
    )
    monkeypatch.setattr(pending_check.crawler, "collect_documents_for_site", lambda _site: ["raw"])
    monkeypatch.setattr(pending_check.crawler, "extract_primary_candidates", lambda _docs, _site: candidates)

    assert list(pending_check.collect_site_pred(candidate)) == list(range(191, 181, -1))


def test_candidate_without_latest_two_cache_periods_is_failure_not_clean(monkeypatch, tmp_path) -> None:
    cache = {"periods": [191, 190, 189], "sites": {}}
    exit_code, report = run_main(
        monkeypatch, tmp_path, [site("过期候选")], [], {"过期候选": {189: "红波"}}, cache
    )

    assert exit_code & pending_check.EXIT_FAILURE
    assert report["failures"][0]["status"] == "failure"
    assert report["checked"] == []


def test_missing_cache_writes_failure_report_and_returns_failure(monkeypatch, tmp_path) -> None:
    cache_file = tmp_path / "missing_cache.json"
    report_file = tmp_path / "pending_cache_check.json"
    monkeypatch.setattr(pending_check, "CACHE_FILE", cache_file)
    monkeypatch.setattr(pending_check, "REPORT_FILE", report_file)

    exit_code = pending_check.main()
    report = json.loads(report_file.read_text(encoding="utf-8"))

    assert exit_code == pending_check.EXIT_FAILURE
    assert report["failures"][0]["status"] == "failure"
    assert report["failures"][0]["name"] == "recent_10_cache.json"


def test_duplicate_and_suspect_thresholds_still_align_concrete_periods() -> None:
    six = [(period, "红波") for period in range(191, 185, -1)]
    five = [(period, "蓝波") for period in range(191, 186, -1)]
    assert pending_check.classify_pair_match(six, six)["status"] == "duplicate"
    assert pending_check.classify_pair_match(five, five)["status"] == "suspect"
    shifted = [(period - 20, value) for period, value in six]
    assert pending_check.classify_pair_match(six, shifted)["status"] == "ignore"


def test_report_and_exit_code_distinguish_blocked_rejected_and_failure(monkeypatch, tmp_path) -> None:
    candidate_sites = [
        site("同名站"),
        site("疑似站", "https://suspect.example/topic/1"),
        site("失败站", "https://failure.example/topic/1"),
    ]
    existing = [site("同名站", "https://old.example/topic/1")]
    suspect_data = {191: "红波", 190: "蓝波", 189: "绿波"}
    cache = {
        "periods": [191, 190, 189],
        "sites": {"已有匹配站": {"data": {str(k): v for k, v in suspect_data.items()}}},
    }
    exit_code, report = run_main(
        monkeypatch,
        tmp_path,
        candidate_sites,
        existing,
        {"疑似站": suspect_data, "失败站": RuntimeError("network down")},
        cache,
    )

    assert exit_code == (
        pending_check.EXIT_BLOCKED | pending_check.EXIT_REJECTED | pending_check.EXIT_FAILURE
    )
    assert report["blocked"][0]["name"] == "疑似站"
    assert report["rejected"][0]["name"] == "同名站"
    assert report["failures"][0]["name"] == "失败站"
    assert report["field_check"]["status"] == "not_implemented"


def test_duplicate_url_alone_returns_rejected_nonzero_without_fetch(monkeypatch, tmp_path) -> None:
    candidate = site("新名字", "HTTPS://Example.COM/topic/42/#anchor")
    existing = [site("已有站", "https://example.com/topic/42")]
    cache = {"periods": [191, 190], "sites": {}}
    exit_code, report = run_main(monkeypatch, tmp_path, [candidate], existing, {}, cache)

    assert exit_code == pending_check.EXIT_REJECTED
    assert report["rejected"][0]["status"] == "duplicate_url"
    assert report["checked"] == []


def test_pending_queue_rejects_later_candidate_with_same_normalized_url(monkeypatch, tmp_path) -> None:
    first = site("队列第一站", "https://example.com/topic/42")
    second = site("队列第二站", "HTTPS://Example.COM/topic/42/#anchor")
    cache = {"periods": [191, 190], "sites": {}}
    exit_code, report = run_main(
        monkeypatch, tmp_path, [first, second], [], {"队列第一站": {191: "红波"}}, cache
    )

    assert exit_code == pending_check.EXIT_REJECTED
    assert report["checked"][0]["name"] == "队列第一站"
    assert report["rejected"][0]["existing_site"] == "队列第一站"
