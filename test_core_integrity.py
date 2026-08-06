import json
import os
from pathlib import Path

import pytest

import sha_yibo_crawler as crawler


def test_update_cache_uses_same_unique_keys_and_migrates_legacy_name_key(tmp_path: Path) -> None:
    cache_file = tmp_path / "recent_10_cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "periods": [188],
                "sites": {
                    "鸿运": {
                        "url": "https://a.example",
                        "pick": "top",
                        "data": {"188": "红波"},
                    },
                    "已删除": {
                        "url": "https://removed.example",
                        "pick": "top",
                        "data": {"188": "绿波"},
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    sites = [
        crawler.Site("鸿运", "https://a.example", "top"),
        crawler.Site("鸿运", "https://b.example", "bottom"),
        crawler.Site("单名站", "https://single.example", "top"),
    ]
    results = [
        crawler.SuccessResult("鸿运", "蓝波", "https://b.example"),
        crawler.SuccessResult("单名站", "绿波", "https://single.example"),
    ]

    crawler.update_recent_cache(cache_file, 189, sites, results)
    data = json.loads(cache_file.read_text(encoding="utf-8"))

    assert set(data["sites"]) == {
        "鸿运｜https://a.example",
        "鸿运｜https://b.example",
        "单名站",
    }
    assert data["sites"]["鸿运｜https://a.example"]["data"] == {"188": "红波"}
    assert data["sites"]["鸿运｜https://b.example"]["data"]["189"] == "蓝波"


def test_update_cache_does_not_migrate_different_name_with_same_url(tmp_path: Path) -> None:
    cache_file = tmp_path / "recent_10_cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "periods": [188],
                "sites": {
                    "旧名称": {
                        "url": "https://shared.example",
                        "pick": "top",
                        "data": {"188": "红波"},
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    crawler.update_recent_cache(
        cache_file,
        189,
        [crawler.Site("新名称", "https://shared.example", "top")],
        [crawler.SuccessResult("新名称", "蓝波")],
    )
    data = json.loads(cache_file.read_text(encoding="utf-8"))

    assert data["sites"]["新名称"]["data"] == {"189": "蓝波"}


def test_update_cache_merges_legacy_data_into_existing_empty_composite_key(tmp_path: Path) -> None:
    cache_file = tmp_path / "recent_10_cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "periods": [188],
                "sites": {
                    "鸿运": {
                        "url": "https://b.example",
                        "pick": "top",
                        "data": {"188": "蓝波"},
                    },
                    "鸿运｜https://a.example": {
                        "name": "鸿运",
                        "url": "https://a.example",
                        "pick": "top",
                        "data": {},
                    },
                    "鸿运｜https://b.example": {
                        "name": "鸿运",
                        "url": "https://b.example",
                        "pick": "top",
                        "data": {},
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    sites = [
        crawler.Site("鸿运", "https://a.example", "top"),
        crawler.Site("鸿运", "https://b.example", "top"),
    ]

    crawler.update_recent_cache(cache_file, 189, sites, [])
    data = json.loads(cache_file.read_text(encoding="utf-8"))

    assert data["sites"]["鸿运｜https://a.example"]["data"] == {}
    assert data["sites"]["鸿运｜https://b.example"]["data"] == {"188": "蓝波"}


def test_update_cache_rerunning_old_period_does_not_make_it_latest(tmp_path: Path) -> None:
    cache_file = tmp_path / "recent_10_cache.json"
    site = crawler.Site("甲", "https://example.test", "top")
    for period in range(152, 162):
        crawler.update_recent_cache(
            cache_file,
            period,
            [site],
            [crawler.SuccessResult("甲", "红波")],
        )

    crawler.update_recent_cache(
        cache_file,
        150,
        [site],
        [crawler.SuccessResult("甲", "蓝波")],
    )
    data = json.loads(cache_file.read_text(encoding="utf-8"))

    assert data["periods"] == [161, 160, 159, 158, 157, 156, 155, 154, 153, 152]
    assert "150" not in data["sites"]["甲"]["data"]


def test_update_cache_cleans_removed_sites_even_when_current_run_has_no_results(tmp_path: Path) -> None:
    cache_file = tmp_path / "recent_10_cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "periods": [189],
                "sites": {
                    "保留": {"url": "https://keep.example", "pick": "top", "data": {"189": "红波"}},
                    "删除": {"url": "https://remove.example", "pick": "top", "data": {"189": "蓝波"}},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    crawler.update_recent_cache(
        cache_file,
        190,
        [crawler.Site("保留", "https://keep.example", "top")],
        [],
    )
    data = json.loads(cache_file.read_text(encoding="utf-8"))

    assert set(data["sites"]) == {"保留"}
    assert data["periods"] == [189]


@pytest.mark.parametrize("writer", ["update", "rebuild"])
def test_cache_writes_use_same_directory_temp_and_os_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, writer: str
) -> None:
    cache_file = tmp_path / "recent_10_cache.json"
    calls: list[tuple[Path, Path, bool]] = []
    real_replace = os.replace

    def checked_replace(source: os.PathLike[str], destination: os.PathLike[str]) -> None:
        source_path = Path(source)
        destination_path = Path(destination)
        calls.append((source_path, destination_path, source_path.exists()))
        real_replace(source_path, destination_path)

    monkeypatch.setattr(crawler.os, "replace", checked_replace)
    site = crawler.Site("甲", "https://example.test", "top")
    if writer == "update":
        crawler.update_recent_cache(
            cache_file,
            189,
            [site],
            [crawler.SuccessResult("甲", "红波")],
        )
    else:
        monkeypatch.setattr(crawler, "collect_site_history", lambda site, keep=10: {189: "红波"})
        crawler.rebuild_recent_cache(cache_file, [site], workers=1)

    assert len(calls) == 1
    source, destination, existed = calls[0]
    assert existed
    assert source.parent == destination.parent == tmp_path
    assert source != destination == cache_file


def test_build_site_history_rejects_same_period_conflicting_values() -> None:
    candidates = [
        crawler.Candidate(189, "红波", "189期 红波", 0),
        crawler.Candidate(189, "蓝波", "189期 蓝波", 1),
    ]

    with pytest.raises(ValueError, match="189.*冲突"):
        crawler.build_site_history(candidates, "top")


@pytest.mark.parametrize(
    "selector,args",
    [
        (crawler.select_candidate_with_reason, (189, "top")),
        (crawler.select_candidate_in_region_limit, (189, "top", 3)),
    ],
)
def test_manual_selection_rejects_conflict_outside_region_window(selector, args) -> None:
    candidates = [
        crawler.Candidate(189, "红波", "189期 红波", 0),
        crawler.Candidate(188, "绿波", "188期 绿波", 1),
        crawler.Candidate(187, "蓝波", "187期 蓝波", 2),
    ]
    candidates.extend(
        crawler.Candidate(150 - index, "绿波", f"{150 - index}期 绿波", 3 + index)
        for index in range(30)
    )
    candidates.append(crawler.Candidate(189, "蓝波", "189期 蓝波", 33))

    selected, reason = selector(candidates, *args)

    assert selected is None
    assert reason == "指定期数存在多条冲突数据"


def test_liuxuanwang_does_not_scan_unanchored_rendered_page() -> None:
    document = "普通栏目\n189期绝杀一波〖红波〗开？00准"

    assert crawler.extract_liuxuanwang_candidates([document]) == []


def test_liuxuanwang_accepts_dedicated_syibo_script_format() -> None:
    script = 'document.writeln("<td>189期绝杀一波〖蓝波〗开？00准</td>");'

    candidates = crawler.extract_liuxuanwang_candidates([script])

    assert [(item.issue, item.value) for item in candidates] == [(189, "蓝波")]


def test_focus_candidates_stop_at_next_registered_site_title() -> None:
    document = """
    鸿运
    189期绝杀一波【红波】开00准
    彩民书籍
    189期绝杀一波【蓝波】开00准
    """

    candidates = crawler.extract_focus_candidates([document], "鸿运")

    assert [(item.issue, item.value) for item in candidates] == [(189, "红波")]


def test_rebuild_cache_migrates_legacy_same_name_data_to_composite_key(tmp_path: Path) -> None:
    cache_file = tmp_path / "recent_10_cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "periods": [188],
                "sites": {
                    "鸿运": {
                        "url": "https://b.example",
                        "pick": "top",
                        "data": {"188": "蓝波"},
                    },
                    "鸿运｜https://a.example": {
                        "name": "鸿运",
                        "url": "https://a.example",
                        "pick": "top",
                        "data": {},
                    },
                    "鸿运｜https://b.example": {
                        "name": "鸿运",
                        "url": "https://b.example",
                        "pick": "top",
                        "data": {},
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    sites = [
        crawler.Site("鸿运", "https://a.example", "top"),
        crawler.Site("鸿运", "https://b.example", "top"),
    ]

    cache, failures = crawler.rebuild_recent_cache(cache_file, sites, workers=1)

    assert failures == []
    assert cache["sites"]["鸿运｜https://a.example"]["data"] == {}
    assert cache["sites"]["鸿运｜https://b.example"]["data"] == {"188": "蓝波"}


def test_liuxuanwang_stops_before_next_site_section() -> None:
    document = """
    澳彩六玄网【绝杀一波】
    189期绝杀一波〖蓝波〗开？00准
    澳彩其他网【绝杀一波】
    188期绝杀一波〖红波〗开？00准
    """

    candidates = crawler.extract_liuxuanwang_candidates([document])

    assert [(item.issue, item.value) for item in candidates] == [(189, "蓝波")]


@pytest.mark.parametrize("next_title", ["六合皇【绝杀一波】", "朱雀【绝杀一波】", "其他栏目【绝杀一波】"])
def test_liuxuanwang_stops_at_any_next_sha_yibo_section(next_title: str) -> None:
    document = f"""
    澳彩六玄网【绝杀一波】
    189期绝杀一波〖蓝波〗开？00准
    {next_title}
    188期绝杀一波〖红波〗开？00准
    """

    candidates = crawler.extract_liuxuanwang_candidates([document])

    assert [(item.issue, item.value) for item in candidates] == [(189, "蓝波")]


def test_focus_candidates_stop_at_non_focus_registered_site_title() -> None:
    document = """
    鸿运
    189期绝杀一波【红波】开00准
    六玄网
    189期绝杀一波【蓝波】开00准
    """

    candidates = crawler.extract_focus_candidates([document], "鸿运")

    assert [(item.issue, item.value) for item in candidates] == [(189, "红波")]


def test_bowang_bowang_only_uses_immediate_second_line_missing_wave() -> None:
    documents = [
        "\n".join(
            [
                "192期 波王一波【绿波】",
                "波王双波【绿波蓝波】开??准",
                "191期 波王一波【蓝波】",
                "广告插入",
                "波王双波【蓝波红波】开虎29准",
            ]
        )
    ]

    candidates = crawler.extract_missing_wave_pair_candidates(documents, "波王波王")

    assert [(item.issue, item.value) for item in candidates] == [(192, "红波")]


def test_babu_maoge_only_reads_sha_bo_column_from_comprehensive_table() -> None:
    site = crawler.Site("八步毛哥", "https://example.test/#62111", "top")
    documents = [
        """
        八步毛哥【综合杀料】
        期数 杀肖 杀尾 杀波 杀头 特开
        192期 鼠 1尾 红双 4头 ？00
        191期 猴 7尾 蓝双 2头 虎29
        八步毛哥【砍杀一波】
        192期砍杀一波【杀蓝波】开？00准
        """
    ]

    candidates = crawler.extract_primary_candidates(documents, site)

    assert [(item.issue, item.value) for item in candidates] == [(192, "红波"), (191, "蓝波")]


def test_liuhehuang_only_reads_con_jsxl_5_container() -> None:
    site = crawler.Site("六合皇", "https://example.test/", "top")
    documents = [
        """
        <div id="con_jsxl_4">
          <p>192期☯杀一波色☯【红波】开 ?? 准</p>
        </div>
        <div id="con_jsxl_5" style="display: none;">
          <p><span>192期</span><span>☯杀一波色☯</span><span>【绿波】</span></p>
          <p><span>190期</span><span>☯杀一波色☯</span><span>【蓝波】</span></p>
        </div>
        <div id="con_jsxl_6">
          <p>192期☯杀一波色☯【蓝波】开 ?? 准</p>
        </div>
        """
    ]

    candidates = crawler.extract_primary_candidates(documents, site)

    assert [(item.issue, item.value) for item in candidates] == [(192, "绿波"), (190, "蓝波")]


def test_jinduobao_only_reads_kansha_yibo_inside_own_title_section() -> None:
    site = crawler.Site("金多宝", "https://example.test/", "top")
    documents = [
        """
        192期砍杀一波【杀红波】开？00准
        【金多宝】绝杀一波
        192期砍杀一波【杀蓝波】开？00准
        189期砍杀一波【杀红波】开龙15准
        【金多宝】绝杀二肖
        192期砍杀一波【杀绿波】开？00准
        """
    ]

    candidates = crawler.extract_primary_candidates(documents, site)

    assert [(item.issue, item.value) for item in candidates] == [(192, "蓝波"), (189, "红波")]


@pytest.mark.parametrize("collector_result", [RuntimeError("boom"), {}])
def test_rebuild_cache_preserves_migrated_legacy_data_when_refresh_fails_or_is_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, collector_result: object
) -> None:
    cache_file = tmp_path / "recent_10_cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "periods": [188],
                "sites": {
                    "鸿运": {
                        "url": "https://b.example",
                        "pick": "top",
                        "data": {"188": "蓝波"},
                    },
                    "鸿运｜https://b.example": {
                        "name": "鸿运",
                        "url": "https://b.example",
                        "pick": "top",
                        "data": {},
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    site = crawler.Site("鸿运", "https://b.example", "top")

    if isinstance(collector_result, Exception):
        monkeypatch.setattr(crawler, "collect_site_history", lambda *_args, **_kwargs: (_ for _ in ()).throw(collector_result))
    else:
        monkeypatch.setattr(crawler, "collect_site_history", lambda *_args, **_kwargs: collector_result)

    cache, _failures = crawler.rebuild_recent_cache(cache_file, [site, crawler.Site("鸿运", "https://a.example", "top")], workers=1, force=True)

    assert cache["sites"]["鸿运｜https://b.example"]["data"] == {"188": "蓝波"}
