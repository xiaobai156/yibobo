# -*- coding: utf-8 -*-
"""跨期借值防线（走真实入口 crawl_site / collect_site_history）。

关键约束：本项目期号 = 年内第几天（1..365），
所以「300 期以后」和「001..012 升序」都是正常形态，绝不能误杀。
"""
import sys
from pathlib import Path

import pytest

SHA = Path(__file__).resolve().parent
sys.path.insert(0, str(SHA))
import sha_yibo_crawler as c  # noqa: E402

SITE = c.Site("捉襟见肘", "https://example.com/topic/1.html", "top", None)


def _doc(*lines: str) -> str:
    return "\n".join(lines)


def _stub(monkeypatch, text: str) -> None:
    monkeypatch.setattr(c, "collect_documents_for_site", lambda site, period=None: [text])
    monkeypatch.setattr(c, "collect_rendered_documents", lambda url, timeout=20, retries=1: [text])


def _rows(start: int, count: int) -> list[str]:
    colors = ["绿波", "红波", "蓝波"]
    return [
        f"{start - i}期《两波中特》《{colors[i % 3]}红波》开0000准"
        for i in range(count)
    ]


# ================= 正常形态：绝不能误杀 =================

def test_late_year_window_300_plus_succeeds(monkeypatch):
    """300..291 这种当期窗口必须成功（期号=年内天数，不是旧年）。"""
    _stub(monkeypatch, _doc(*_rows(305, 10)))
    result, error = c.crawl_site(SITE, 305)
    assert result is not None, f"300 期以后被误杀：{error}"


def test_late_year_window_360_succeeds(monkeypatch):
    _stub(monkeypatch, _doc(*_rows(360, 10)))
    result, error = c.crawl_site(SITE, 360)
    assert result is not None, f"360 期被误杀：{error}"


def test_ascending_early_year_11_12_succeeds(monkeypatch):
    """001..012 升序，请求 11/12 不得被假接缝误杀。"""
    rows = [f"{i:03d}期《两波中特》《绿波红波》开0000准" for i in range(1, 13)]
    _stub(monkeypatch, _doc(*rows))
    for period in (11, 12):
        result, error = c.crawl_site(SITE, period)
        assert result is not None, f"升序 {period} 期被误杀：{error}"


def test_ascending_200_to_298_succeeds(monkeypatch):
    """升序 200..298 属正常站，不得被绕回判据误杀。

    注意：这类站可能被既有的「顶部/尾部 N 组」方向窗口拦下，
    那属另一套规则，与本防线无关；这里只断言不是「绕回」。
    """
    rows = [f"{i}期《两波中特》《绿波红波》开0000准" for i in range(200, 299)]
    _stub(monkeypatch, _doc(*rows))
    result, error = c.crawl_site(SITE, 298)
    assert not (error and "绕回" in error), f"升序站被绕回判据误杀：{error}"


# ================= 真绕回：必须拦住 =================

def test_wrap_current_period_succeeds(monkeypatch):
    """298..001 + 365..297，请求 298 必须成功。"""
    rows = _rows(298, 5) + [f"{i:03d}期《两波中特》《绿波红波》开牛29准" for i in range(1, 4)]
    rows += _rows(365, 5)
    _stub(monkeypatch, _doc(*rows))
    result, error = c.crawl_site(SITE, 298)
    assert result is not None, f"当期不应失败：{error}"


def test_wrap_old_year_only_period_rejected(monkeypatch):
    """某期只出现在 365 段（去年），必须失败。"""
    rows = _rows(298, 3) + [f"{i:03d}期《两波中特》《绿波红波》开牛29准" for i in range(1, 3)]
    rows += _rows(365, 3)
    _stub(monkeypatch, _doc(*rows))
    result, error = c.crawl_site(SITE, 363)
    assert result is None, f"去年 363 不得当今年，实际 {result}"
    assert error and "绕回" in error


def test_stale_year_block_with_future_issue_rejected(monkeypatch):
    """页面出现比目标期更大的期号（365）且无 001，判旧年。"""
    _stub(monkeypatch, _doc(*_rows(365, 6)))
    result, error = c.crawl_site(SITE, 298)
    assert result is None, f"不得借去年值，实际 {result}"
    assert error and "绕回" in error


def test_fallback_cannot_override_wrap_verdict(monkeypatch):
    """主路径判绕回后，兜底不得改写结论成功返回。"""
    stale = _doc(*_rows(365, 6))
    monkeypatch.setattr(c, "collect_documents_for_site", lambda site, period=None: [stale])
    # 兜底返回一份看似正常但同样缺当期的文档
    monkeypatch.setattr(c, "collect_rendered_documents", lambda url, timeout=20, retries=1: [_doc(*_rows(360, 5))])
    result, error = c.crawl_site(SITE, 298)
    assert result is None, f"兜底不得覆盖绕回结论，实际 {result}"


def test_old_year_first_layout_rejects_old_period(monkeypatch):
    """365..001 在前、今年段在后：去年段里的期号必须失败。"""
    colors = ["绿波", "红波", "蓝波"]
    rows = [f"{i}期《两波中特》《{colors[i % 3]}红波》开龙26准" for i in range(365, 360, -1)]
    rows += [f"{i:03d}期《两波中特》《{colors[i % 3]}红波》开牛29准" for i in range(1, 4)]
    rows += [f"{i}期《两波中特》《{colors[i % 3]}红波》开0000准" for i in range(298, 293, -1)]
    _stub(monkeypatch, _doc(*rows))
    result, error = c.crawl_site(SITE, 363)
    assert result is None, f"去年段 363 不得当今年，实际 {result}"
    assert error and "绕回" in error


def test_old_year_first_layout_keeps_current(monkeypatch):
    """同一布局下今年段的期号仍要能取到。"""
    colors = ["绿波", "红波", "蓝波"]
    rows = [f"{i}期《两波中特》《{colors[i % 3]}红波》开龙26准" for i in range(365, 360, -1)]
    rows += [f"{i:03d}期《两波中特》《{colors[i % 3]}红波》开牛29准" for i in range(1, 4)]
    rows += [f"{i}期《两波中特》《{colors[i % 3]}红波》开0000准" for i in range(298, 293, -1)]
    _stub(monkeypatch, _doc(*rows))
    result, error = c.crawl_site(SITE, 296)
    assert result is not None, f"今年段 296 不应失败：{error}"


# ================= 缓存重建 =================

def test_history_rebuild_keeps_current_year(monkeypatch):
    rows = _rows(298, 5) + [f"{i:03d}期《两波中特》《绿波红波》开牛29准" for i in range(1, 3)]
    rows += _rows(365, 3)
    _stub(monkeypatch, _doc(*rows))
    history = c.collect_site_history(SITE, keep=10)
    assert 298 in history


def test_pending_next_period_not_treated_as_stale(monkeypatch):
    """页面顶部挂出未开奖的下一期（开0000），不得被判为旧年数据。

    真实场景：目标期 303 已开奖，页面顶部已挂 304 期待开。
    """
    rows = ["304期《两波中特》《红波绿波》开0000准"] + _rows(303, 8)
    _stub(monkeypatch, _doc(*rows))
    result, error = c.crawl_site(SITE, 303)
    assert result is not None, f"待开期被误判旧年：{error}"


def test_pending_next_period_with_colon_marker(monkeypatch):
    """开：00 / 开？00 这类未开奖写法同样不算旧年证据。"""
    for marker in ("开：00准", "开？00准"):
        rows = [f"304期《两波中特》《红波绿波》{marker}"] + _rows(303, 8)
        _stub(monkeypatch, _doc(*rows))
        result, error = c.crawl_site(SITE, 303)
        assert result is not None, f"{marker} 被误判旧年：{error}"


def test_stale_year_block_still_rejected_with_pending(monkeypatch):
    """真旧年段（365..360 已开奖）仍必须拦住，即便顶部有待开期。"""
    colors = ["绿波", "红波", "蓝波"]
    rows = [f"{i}期《两波中特》《{colors[i % 3]}红波》开龙26准" for i in range(365, 359, -1)]
    rows += ["304期《两波中特》《红波绿波》开0000准"]
    _stub(monkeypatch, _doc(*rows))
    result, error = c.crawl_site(SITE, 303)
    assert result is None, f"旧年段不得借值，实际 {result}"
    assert error and "绕回" in error
