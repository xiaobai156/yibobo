# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import atexit
import base64
import gzip
import html
import json
import os
import re
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


_browser_local = threading.local()


def _get_browser_session():
    session = getattr(_browser_local, "session", None)
    if session is not None:
        return session
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError(f"Playwright不可用: {exc}") from exc
    manager = sync_playwright()
    playwright = manager.start() if hasattr(manager, "start") else manager
    browser = playwright.chromium.launch(headless=True)
    session = (playwright, browser)
    _browser_local.session = session
    return session


def _close_browser_sessions() -> None:
    session = getattr(_browser_local, "session", None)
    if session is None:
        return
    _browser_local.session = None
    playwright, browser = session
    try:
        browser.close()
    finally:
        stop = getattr(playwright, "stop", None)
        if stop is not None:
            stop()


@contextmanager
def _browser_page():
    _, browser = _get_browser_session()
    page = None
    failed = False
    try:
        page = browser.new_page(ignore_https_errors=True)
        yield page
    except BaseException:
        failed = True
        _close_browser_sessions()
        raise
    finally:
        if page is not None and not getattr(page, "closed", False):
            try:
                page.close()
            except Exception:
                if not failed:
                    raise


atexit.register(_close_browser_sessions)


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR.parent / "七类数据统一归纳"
DEFAULT_FAILURE_OUTPUT_DIR = SCRIPT_DIR.parent / "七类数据统一归纳失败"
DEFAULT_CACHE_FILE = SCRIPT_DIR / "recent_10_cache.json"
WAVE_VALUES = {"红波", "蓝波", "绿波"}
STRICT_REGION_NAMES = {"平特网", "猪八戒", "赤兔", "红姐论坛", "广东八二站"}
REFERENCE_EXACT_SHA_YIBO_NAMES = {"迷人教授", "帅气成衣", "好奇好奇", "拥挤门", "花心膝盖"}
IFRAME_TOPIC_SITE_NAMES = {"针锋相对", "自强不息", "宁静致远", "可怕人类", "我服慈悲", "桃花没酒"}
ZQBX_NAME = "自强不息"
QVUUQS_REFERENCE_DOUBLE_WAVE_KEYWORDS = {"珠光宝气": "双波中特", "攻克专家": "双波必中"}
ANJU_ZILIAOYUAN_NAME = "安居资料员"
EXACT_SHA_YIBO_SITE_NAMES = {"宝码玄机", "八步毛哥", "金吊桶", "宝马玄机"}
STRICT_WINDOW_LIMIT = 5
STRICT_WINDOW_THRESHOLD = 30
SHENGGONG_ZHIGUO_NAME = "生功止过"
ZHUNSHA_YIBO_NAME = "准杀一波"
QVUUQS_USER_RECORD_WINDOW_NAMES = {"已洗妈咪"}
ROURQING_SHASHOU_NAME = "柔情杀手"
ROURQING_SHASHOU_KEYWORD = "绝杀一波"
ROURQING_SHASHOU_USER_RE = re.compile(r"#/user/(\d+)")
ROURQING_SHASHOU_PUBLISH_PATH = "/unite49/h5/userHomePage/userPublish"
TEXT_TRANS = str.maketrans(
    {
        "絕": "绝",
        "殺": "杀",
        "獨": "独",
        "藍": "蓝",
        "紅": "红",
        "綠": "绿",
        "開": "开",
        "準": "准",
        "頭": "头",
    }
)
SCRIPT_SRC_RE = re.compile(r"<script\b[^>]*\bsrc\s*=\s*([\"']?)([^\"'\s>]+)\1", re.I)
STRDECODE_RE = re.compile(r"strdecode\s*\(\s*([\"'])([^\"']+)\1\s*\)", re.I)
WAVE_RE = r"([红蓝绿]波|红{2,3}|蓝{2,3}|绿{2,3})"
EXACT_SHA_YIBO_RE = re.compile(
    rf"(?<!\d)(\d{{1,4}})\s*期.{{0,18}}?绝杀\s*一波.{{0,12}}?{WAVE_RE}"
)
ISSUE_FIRST_RE = re.compile(
    rf"(?<!\d)(\d{{1,4}})\s*期.{{0,30}}?(?:独杀|绝杀|精杀|大杀|砍杀|稳杀)\s*(?:一波)?.{{0,12}}?(?:杀特)?{WAVE_RE}"
)
KEYWORD_FIRST_RE = re.compile(
    rf"(?:杀一波色|公式杀波).{{0,20}}?(?<!\d)(\d{{1,4}})\s*期.{{0,30}}?{WAVE_RE}"
)
TABLE_ROW_RE = re.compile(rf"(?<!\d)(\d{{1,4}})\s*期(?:\s+\S+){{0,3}}\s+{WAVE_RE}")
TABLE_SINGLE_WAVE_ROW_RE = re.compile(r"(?<!\d)(\d{1,4})\s*期\s+\S+\s+\(([红蓝绿])\)")
FORMULA_WAVE_RE = re.compile(rf"第?\s*(\d{{1,4}})\s*期.{{0,40}}?杀{WAVE_RE}")
DOUBLE_WAVE_RE = re.compile(
    r"(?<!\d)(\d{1,4})\s*期.{0,12}?(?:双波中特|双波必中|两波中特|必中双波).{0,8}?([红蓝绿]波).{0,3}?([红蓝绿]波)"
)
TABLE_DOUBLE_WAVE_RE = re.compile(
    r"(?<!\d)(\d{1,4})\s*期.{0,8}?([红蓝绿]波).{0,3}?([红蓝绿]波)"
)
DOTTED_DOUBLE_WAVE_RE = re.compile(
    r"(?<!\d)(\d{1,4})\s*期.{0,30}?(?:双波中特|双波必中|两波中特|必中双波).{0,12}?([红蓝绿])(?:[.\s、,，/\\-]*)?([红蓝绿])"
)
EXACT_TWO_COLOR_BRACKET_RE = re.compile(
    r"(?<!\d)(\d{1,4})\s*期.{0,20}?[【\[\(（〔]\s*([红蓝绿])(?:波)?\s*(?:[+、,，./\\-]*)\s*([红蓝绿])(?:波)?\s*[】\]\)）〕]"
)
BUY_TWO_WAVE_RE = re.compile(r"(?<!\d)(\d{1,4})\s*期.{0,20}?必买\s*二波")
TWO_COLOR_LINE_RE = re.compile(r"[【\[\(（〔]\s*([红蓝绿])(?:波)?\s+([红蓝绿])(?:波)?\s*[】\]\)）〕]")


@dataclass(frozen=True)
class Site:
    name: str
    url: str
    pick: str
    keyword: str | None = None


@dataclass(frozen=True)
class Candidate:
    issue: int
    value: str
    line: str
    order: int


@dataclass(frozen=True)
class SuccessResult:
    name: str
    value: str
    url: str | None = None


class PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"br", "p", "div", "li", "tr", "td", "h1", "h2"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


class ElementTextParser(HTMLParser):
    def __init__(self, element_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self.element_id = element_id
        self.depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if self.depth == 0:
            if dict(attrs).get("id") != self.element_id:
                return
            self.depth = 1
        else:
            self.depth += 1
        if tag in {"br", "p", "div", "li", "tr", "td", "h1", "h2"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.depth:
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth:
            self.parts.append(data)


class LinkTextParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.current_href: str | None = None
        self.current_parts: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if not href:
            return
        self.current_href = urljoin(self.base_url, href)
        self.current_parts = []

    def handle_data(self, data: str) -> None:
        if self.current_href:
            self.current_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self.current_href:
            return
        text = re.sub(r"\s+", " ", "".join(self.current_parts)).strip()
        if text:
            self.links.append((text, self.current_href))
        self.current_href = None
        self.current_parts = []


def setup_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def compact_detail(value: object) -> str:
    detail = re.sub(r"\s+", " ", str(value)).strip()
    return detail or "无异常详情"


def format_exception_reason(action: str, exc: Exception) -> str:
    return f"{action}: {type(exc).__name__}: {compact_detail(exc)}"


def format_site_failure(site: "Site", reason: str | None) -> str:
    return f"{site.name} {site.url} 失败原因: {compact_detail(reason or '')}"


def fetch_text_with_final_url(url: str, timeout: int = 20, retries: int = 2) -> tuple[str, str]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
            with urlopen(req, timeout=timeout, context=ssl._create_unverified_context()) as resp:
                data = resp.read()
                final_url = resp.geturl()
            if data[:2] == b"\x1f\x8b":
                data = gzip.decompress(data)
            return data.decode("utf-8", errors="replace"), final_url
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(str(last_error))


def fetch_text(url: str, timeout: int = 20, retries: int = 2) -> str:
    return fetch_text_with_final_url(url, timeout, retries)[0]


def decode_strdecode_blocks(text: str) -> list[str]:
    decoded: list[str] = []
    for match in STRDECODE_RE.finditer(text):
        payload = match.group(2)
        try:
            raw = base64.b64decode(payload + ("=" * (-len(payload) % 4)))
        except Exception:
            continue
        for encoding in ("utf-8", "gb18030", "big5"):
            try:
                decoded.append(raw.decode(encoding))
                break
            except UnicodeDecodeError:
                continue
    return decoded


def collect_documents(url: str, timeout: int = 20) -> list[str]:
    html_text = fetch_text(url, timeout)
    documents = [html_text]
    for match in SCRIPT_SRC_RE.finditer(html_text):
        script_url = urljoin(url, match.group(2))
        if "/upload/script/" not in script_url.lower():
            continue
        documents.append(fetch_text(script_url, timeout))

    seen = set(documents)
    for _ in range(3):
        additions: list[str] = []
        for document in documents:
            for decoded in decode_strdecode_blocks(document):
                if decoded not in seen:
                    seen.add(decoded)
                    additions.append(decoded)
        if not additions:
            break
        documents.extend(additions)
    return documents


def extract_links(documents: list[str], base_url: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for document in documents:
        parser = LinkTextParser(base_url)
        parser.feed(document)
        links.extend(parser.links)
    return links


def extract_qvuuqs_route(url: str) -> tuple[int | None, int | None]:
    match = re.search(r"#/(users|forums)/(\d+)(?:/references/(\d+))?(?:$|[/?])", url)
    if not match:
        return None, None
    route_kind, first_id, reference_id = match.groups()
    if route_kind == "forums":
        return None, int(first_id)
    return int(first_id), int(reference_id) if reference_id else None


def is_qvuuqs_host(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower().rstrip(".")
    return hostname.split(".", 1)[0] == "qvuuqqs"


def iter_qvuuqs_record_nodes(payload: object, path: str = "$"):
    if isinstance(payload, dict):
        if "id" in payload and any(field in payload for field in ("content", "title", "topic", "sub_topic", "section")):
            yield payload, path
        for key, value in payload.items():
            child_path = f"{path}.{key}" if str(key).isidentifier() else f"{path}[{key!r}]"
            yield from iter_qvuuqs_record_nodes(value, child_path)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            yield from iter_qvuuqs_record_nodes(value, f"{path}[{index}]")


def normalize_qvuuqs_id(value: object) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def locate_qvuuqs_record(payload: object, record_id: int) -> tuple[dict, str]:
    matches = [
        (record, path)
        for record, path in iter_qvuuqs_record_nodes(payload)
        if normalize_qvuuqs_id(record.get("id")) == record_id
    ]
    if not matches:
        raise ValueError(f"未找到唯一目标记录ID: {record_id}")
    if len(matches) > 1:
        raise ValueError(f"找到多个同ID目标记录: {record_id}")
    return matches[0]


def normalize_qvuuqs_field(value: object) -> str:
    return re.sub(r"[\s【】\[\]『』()（）:：·•]+", "", str(value or "")).translate(TEXT_TRANS)


def validate_qvuuqs_reference_record(
    record: object, user_id: int | None, record_id: int, keyword: str
) -> dict:
    if not isinstance(record, dict):
        raise ValueError("精确接口未返回单篇文章对象")
    if normalize_qvuuqs_id(record.get("id")) != record_id:
        raise ValueError(f"记录ID不匹配: 期望 {record_id}, 实际 {record.get('id')}")
    record_user_id = normalize_qvuuqs_id(record.get("user_id"))
    if record_user_id is None:
        raise ValueError("作者用户ID缺失")
    if user_id is not None and record_user_id != user_id:
        raise ValueError(f"作者用户ID不匹配: 期望 {user_id}, 实际 {record.get('user_id')}")
    nested_user = record.get("user")
    if isinstance(nested_user, dict) and normalize_qvuuqs_id(nested_user.get("id")) != record_user_id:
        raise ValueError(f"嵌套作者用户ID不匹配: 期望 {record_user_id}, 实际 {nested_user.get('id')}")
    metadata = " ".join(str(record.get(field) or "") for field in ("title", "topic", "sub_topic", "section"))
    if normalize_qvuuqs_field(keyword) not in normalize_qvuuqs_field(metadata):
        raise ValueError(f"栏目字段不匹配: 未找到 {keyword}")
    if not str(record.get("content") or "").strip():
        raise ValueError("目标文章正文为空")
    return record


def qvuuqs_record_issues(record: dict) -> set[int]:
    explicit_issues: set[int] = set()
    for field in ("draw", "issue", "period", "lottery_period"):
        value = normalize_qvuuqs_id(record.get(field))
        if value is not None:
            explicit_issues.add(value)
    if explicit_issues:
        return explicit_issues
    issues: set[int] = set()
    content = str(record.get("content") or "")
    issues.update(int(match.group(1)) for match in re.finditer(r"(?<!\d)(\d{1,4})\s*期", content))
    return issues


def qvuuqs_explicit_record_issues(record: dict) -> set[int]:
    issues: set[int] = set()
    for field in ("draw", "issue", "period", "lottery_period"):
        value = normalize_qvuuqs_id(record.get(field))
        if value is not None:
            issues.add(value)
    return issues


def qvuuqs_content_issues(record: dict) -> set[int]:
    content = html.unescape(str(record.get("content") or "")).translate(TEXT_TRANS)
    return {
        int(match.group(1))
        for match in re.finditer(r"(?<!\d)(\d{1,4})\s*期", content)
    }


def validate_qvuuqs_target_record(record: object, issue: int) -> dict:
    if not isinstance(record, dict):
        raise ValueError("目标期数详情不是单篇文章对象")
    explicit_issues = qvuuqs_explicit_record_issues(record)
    if explicit_issues != {issue}:
        shown = ",".join(str(item) for item in sorted(explicit_issues)) or "无"
        raise ValueError(f"记录字段期数不匹配: 目标{issue}期,实际{shown}")
    if not str(record.get("content") or "").strip():
        raise ValueError("目标期数详情正文为空")
    if issue not in qvuuqs_content_issues(record):
        raise ValueError(f"目标期数详情正文未找到指定期数: {issue}期")
    return record


def qvuuqs_index_record_issue(record: dict) -> int:
    explicit_issues = qvuuqs_explicit_record_issues(record)
    if len(explicit_issues) != 1:
        raise ValueError(f"索引文章期数字段不唯一: {record.get('id')}")
    return next(iter(explicit_issues))


def select_qvuuqs_index_records(
    records: list[dict], user_id: int, keyword: str, issue: int | None = None, limit: int = 10
) -> list[dict]:
    keyword_key = normalize_qvuuqs_field(keyword)
    matching: list[dict] = []
    for record in records:
        if not isinstance(record, dict) or normalize_qvuuqs_id(record.get("user_id")) != user_id:
            continue
        nested_user = record.get("user")
        if isinstance(nested_user, dict) and normalize_qvuuqs_id(nested_user.get("id")) != user_id:
            raise ValueError(f"索引文章作者ID不匹配: {record.get('id')}")
        metadata = " ".join(str(record.get(field) or "") for field in ("title", "topic", "sub_topic", "section"))
        if keyword_key not in normalize_qvuuqs_field(metadata):
            continue
        record_issue = qvuuqs_index_record_issue(record)
        if issue is not None and record_issue != issue:
            continue
        matching.append(record)
    if not matching:
        target = f"{issue}期" if issue is not None else "近期期数"
        raise ValueError(f"当前用户索引未找到指定栏目文章: {target} {keyword}")
    by_issue: dict[int, list[dict]] = {}
    for record in matching:
        by_issue.setdefault(qvuuqs_index_record_issue(record), []).append(record)
    conflicts = sorted(draw for draw, items in by_issue.items() if len({str(item.get("id")) for item in items}) > 1)
    if conflicts:
        raise ValueError(f"同一期当前索引匹配到多条文章: {','.join(map(str, conflicts))}期")
    ordered = sorted(matching, key=lambda item: (qvuuqs_index_record_issue(item), int(item.get("id", 0))), reverse=True)
    return ordered[:1] if issue is not None else ordered[:limit]


def select_qvuuqs_user_records(
    records: list[dict], user_id: int, keyword: str, issue: int | None = None
) -> list[dict]:
    keyword_key = normalize_qvuuqs_field(keyword)
    matching = []
    for record in records:
        if not isinstance(record, dict) or normalize_qvuuqs_id(record.get("user_id")) != user_id:
            continue
        nested_user = record.get("user")
        if isinstance(nested_user, dict) and normalize_qvuuqs_id(nested_user.get("id")) != user_id:
            raise ValueError(f"用户文章作者ID不匹配: {record.get('id')}")
        metadata = " ".join(str(record.get(field) or "") for field in ("title", "topic", "sub_topic", "section"))
        if keyword_key not in normalize_qvuuqs_field(metadata):
            continue
        if not str(record.get("content") or "").strip():
            raise ValueError(f"用户文章 {record.get('id')} 正文为空")
        matching.append(record)
    if issue is not None:
        matching = [record for record in matching if issue in qvuuqs_record_issues(record)]
    if not matching:
        target = f"{issue}期" if issue is not None else "近期期数"
        raise ValueError(f"用户页未找到唯一栏目文章: {target} {keyword}")
    duplicate_draws = [
        draw
        for draw, count in Counter(draw for record in matching for draw in qvuuqs_record_issues(record)).items()
        if count > 1
    ]
    if duplicate_draws:
        raise ValueError(f"同一期匹配到多条用户文章: {','.join(str(draw) for draw in sorted(duplicate_draws))}期")
    return sorted(matching, key=lambda record: max(qvuuqs_record_issues(record), default=0), reverse=True)


def select_qvuuqs_user_record(
    records: list[dict],
    user_id: int,
    keyword: str,
    issue: int,
    pick: str,
    limit: int = STRICT_WINDOW_LIMIT,
) -> dict:
    keyword_key = normalize_qvuuqs_field(keyword)
    matching: list[tuple[dict, int]] = []
    records_by_id: dict[int, tuple[dict, int]] = {}
    for record in records:
        if not isinstance(record, dict) or normalize_qvuuqs_id(record.get("user_id")) != user_id:
            continue
        nested_user = record.get("user")
        if isinstance(nested_user, dict) and normalize_qvuuqs_id(nested_user.get("id")) != user_id:
            raise ValueError(f"用户文章作者ID不匹配: {record.get('id')}")
        metadata = " ".join(str(record.get(field) or "") for field in ("title", "topic", "sub_topic", "section"))
        if keyword_key not in normalize_qvuuqs_field(metadata):
            continue
        explicit_issues = qvuuqs_explicit_record_issues(record)
        record_id = normalize_qvuuqs_id(record.get("id"))
        if len(explicit_issues) != 1 or record_id is None:
            continue
        record_issue = next(iter(explicit_issues))
        previous = records_by_id.get(record_id)
        if previous is not None:
            previous_record, previous_issue = previous
            if previous_issue != record_issue or str(previous_record.get("content") or "") != str(
                record.get("content") or ""
            ):
                raise ValueError(f"同一文章ID记录冲突: {record_id}")
            continue
        pair = (record, record_issue)
        records_by_id[record_id] = pair
        matching.append(pair)

    issue_ids: dict[int, set[int]] = {}
    for record, record_issue in matching:
        issue_ids.setdefault(record_issue, set()).add(normalize_qvuuqs_id(record.get("id")))
    if any(len(record_ids) > 1 for record_ids in issue_ids.values()):
        raise ValueError("同一期匹配到多条用户文章")

    ordered = sorted(
        matching,
        key=lambda item: (item[1], normalize_qvuuqs_id(item[0].get("id")) or 0),
        reverse=True,
    )
    scoped = ordered[:limit] if pick == "top" else ordered[-limit:]
    selected = [record for record, record_issue in scoped if record_issue == issue]
    if selected:
        return selected[0]
    if any(record_issue == issue for _, record_issue in ordered):
        label = "顶部" if pick == "top" else "尾部"
        raise ValueError(f"指定期数不在{label}{limit}组范围")
    raise ValueError(f"未找到指定期数: 用户页未找到指定栏目文章: {issue}期 {keyword}")


def open_qvuuqs_page(page, url: str, timeout: int) -> None:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
    except Exception:
        page.goto(url, wait_until="commit", timeout=timeout * 1000)


def fetch_qvuuqs_json(page, path: str) -> object:
    result = page.evaluate(
        """async path => {
            const response = await fetch(path, {credentials: "same-origin"});
            const text = await response.text();
            let data = null;
            try { data = JSON.parse(text); } catch (_) {}
            return {status: response.status, data};
        }""",
        path,
    )
    if result.get("status") != 200:
        raise RuntimeError(f"接口返回 HTTP {result.get('status')}: {path}")
    if result.get("data") is None:
        raise RuntimeError(f"接口返回非JSON: {path}")
    return result["data"]


def collect_qvuuqs_reference_documents(
    url: str, keyword: str, issue: int | None, timeout: int = 20
) -> list[str]:
    user_id, route_record_id = extract_qvuuqs_route(url)
    if route_record_id is None:
        raise ValueError("动态引用页URL缺少文章记录ID")
    with _browser_page() as page:
        open_qvuuqs_page(page, url, timeout)
        anchor_payload = fetch_qvuuqs_json(page, f"/api/v1/forums/{route_record_id}")
        anchor, _ = locate_qvuuqs_record(anchor_payload, route_record_id)
        anchor = validate_qvuuqs_reference_record(anchor, user_id, route_record_id, keyword)
        owner_id = user_id or normalize_qvuuqs_id(anchor.get("user_id"))
        if owner_id is None:
            raise ValueError("动态引用页缺少作者用户ID")

        payloads = [
            fetch_qvuuqs_json(page, f"/api/v1/users/{owner_id}/references?per_page=100"),
            fetch_qvuuqs_json(page, f"/api/v1/users/{owner_id}/forums?per_page=100"),
        ]
        records_by_id: dict[int, dict] = {}
        for payload in payloads:
            for record, _ in iter_qvuuqs_record_nodes(payload):
                record_key = normalize_qvuuqs_id(record.get("id"))
                if record_key is None:
                    continue
                previous = records_by_id.get(record_key)
                if previous is not None:
                    previous_signature = tuple(
                        str(previous.get(field) or "")
                        for field in ("user_id", "draw", "topic", "sub_topic", "section")
                    )
                    current_signature = tuple(
                        str(record.get(field) or "")
                        for field in ("user_id", "draw", "topic", "sub_topic", "section")
                    )
                    if previous_signature != current_signature:
                        raise ValueError(f"当前用户索引同一记录ID字段冲突: {record_key}")
                    continue
                records_by_id[record_key] = record

        selected = select_qvuuqs_index_records(list(records_by_id.values()), owner_id, keyword, issue)
        documents: list[str] = []
        for index_record in selected:
            current_id = normalize_qvuuqs_id(index_record.get("id"))
            if current_id is None:
                raise ValueError("当前用户索引记录缺少文章ID")
            detail_payload = fetch_qvuuqs_json(page, f"/api/v1/forums/{current_id}")
            detail, _ = locate_qvuuqs_record(detail_payload, current_id)
            detail = validate_qvuuqs_reference_record(detail, owner_id, current_id, keyword)
            detail = validate_qvuuqs_target_record(detail, qvuuqs_index_record_issue(index_record))
            documents.append(str(detail["content"]))
        return documents


def collect_qvuuqs_user_documents(site: Site, period: int | None, timeout: int = 20) -> list[str]:
    user_id, record_id = extract_qvuuqs_route(site.url)
    if user_id is None or record_id is not None:
        raise ValueError("用户页URL缺少有效用户ID")
    keyword = site.keyword or "绝杀一波"
    with _browser_page() as page:
        open_qvuuqs_page(page, site.url, timeout)
        references = fetch_qvuuqs_json(page, f"/api/v1/users/{user_id}/references?per_page=20")
        forums = fetch_qvuuqs_json(page, f"/api/v1/users/{user_id}/forums?per_page=20")
        records = [
            record
            for payload in (references, forums)
            for record, _ in iter_qvuuqs_record_nodes(payload)
        ]
        if period is not None and site.name in QVUUQS_USER_RECORD_WINDOW_NAMES:
            index_record = select_qvuuqs_user_record(
                records, user_id, keyword, period, site.pick
            )
            target_id = normalize_qvuuqs_id(index_record.get("id"))
            if target_id is None:
                raise ValueError("目标用户文章缺少记录ID")
            detail_payload = fetch_qvuuqs_json(page, f"/api/v1/forums/{target_id}")
            detail, _ = locate_qvuuqs_record(detail_payload, target_id)
            detail = validate_qvuuqs_reference_record(
                detail, user_id, target_id, keyword
            )
            detail = validate_qvuuqs_target_record(detail, period)
            return [str(detail["content"])]
        selected = select_qvuuqs_user_records(records, user_id, keyword, period)
        documents: list[str] = []
        for record in selected:
            content = str(record["content"])
            if period is not None and f"{period}期" not in content:
                record_id = normalize_qvuuqs_id(record.get("id"))
                if record_id is None:
                    raise ValueError("目标用户文章缺少记录ID")
                detail_payload = fetch_qvuuqs_json(page, f"/api/v1/forums/{record_id}")
                detail, _ = locate_qvuuqs_record(detail_payload, record_id)
                detail = validate_qvuuqs_reference_record(detail, user_id, record_id, keyword)
                detail = validate_qvuuqs_target_record(detail, period)
                content = str(detail["content"])
            documents.append(content)
        return documents


def collect_bazahei_documents(home_url: str, period: int | None, timeout: int = 20) -> list[str]:
    home_documents = collect_documents(home_url, timeout)
    target_issue = f"{period}期" if period is not None else ""
    matches = [
        (text, href)
        for text, href in extract_links(home_documents, home_url)
        if "绝杀一波" in text and "巴扎嘿" in text and (not target_issue or target_issue in text)
    ]
    if not matches:
        if target_issue:
            raise ValueError(f"首页未找到指定期数的巴扎嘿目录入口: {target_issue}")
        raise ValueError("首页未找到巴扎嘿目录入口")
    if period is not None:
        if len(matches) != 1:
            raise ValueError(f"目录页未唯一定位指定期数的巴扎嘿入口: {period}期")
        selected = matches[0]
    else:
        issue_links = [
            (int(issue.group(1)), item)
            for item in matches
            if (issue := re.search(r"(?<!\d)(\d{1,4})期", item[0]))
        ]
        if not issue_links:
            raise ValueError("目录页巴扎嘿入口缺少可验证期号")
        latest_issue = max(issue for issue, _ in issue_links)
        latest = [item for issue, item in issue_links if issue == latest_issue]
        if len(latest) != 1:
            raise ValueError(f"目录页同一期存在多条巴扎嘿入口: {latest_issue}期")
        selected = latest[0]
    return collect_documents(selected[1], timeout)


def collect_longxiao_jiutian_documents(home_url: str, period: int | None, timeout: int = 20) -> list[str]:
    home_documents = collect_documents(home_url, timeout)
    target_issue = f"{period}期" if period is not None else ""
    matches = [
        (text, href)
        for text, href in extract_links(home_documents, home_url)
        if "龙啸九天" in text and "绝杀壹波" in text and (not target_issue or target_issue in text)
    ]
    if not matches:
        if target_issue:
            raise ValueError(f"目录页未找到指定期数的龙啸九天入口: {target_issue}")
        raise ValueError("目录页未找到龙啸九天入口")
    if period is not None:
        selected = [item for item in matches if f"{period}期" in item[0]]
        if len(selected) != 1:
            raise ValueError(f"目录页未唯一定位指定期数的龙啸九天入口: {period}期")
    else:
        issue_links = [
            (int(issue.group(1)), item)
            for item in matches
            if (issue := re.search(r"(?<!\d)(\d{1,4})期", item[0]))
        ]
        if not issue_links:
            raise ValueError("目录页龙啸九天入口缺少可验证期号")
        latest_issue = max(issue for issue, _ in issue_links)
        selected = [item for issue, item in issue_links if issue == latest_issue]
        if len(selected) != 1:
            raise ValueError(f"目录页同一期存在多条龙啸九天入口: {latest_issue}期")
    return collect_documents(selected[0][1], timeout)


def extract_rourqing_shashou_user_id(url: str) -> int | None:
    match = ROURQING_SHASHOU_USER_RE.search(url)
    return int(match.group(1)) if match else None


def parse_rourqing_shashou_publish(payload: object, user_id: int) -> dict[int, str]:
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise ValueError("柔情杀手发布接口未返回成功响应")
    data = payload.get("data")
    records = data.get("list") if isinstance(data, dict) else None
    if not isinstance(records, list) or not records:
        raise ValueError("柔情杀手发布接口未返回文章列表")
    documents: dict[int, str] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("柔情杀手发布接口存在非对象文章记录")
        if normalize_qvuuqs_id(record.get("userId")) != user_id:
            raise ValueError(f"柔情杀手文章作者ID不匹配: {record.get('id')}")
        title = str(record.get("title") or "")
        if ROURQING_SHASHOU_NAME not in title or ROURQING_SHASHOU_KEYWORD not in title:
            raise ValueError(f"柔情杀手文章栏目不匹配: {record.get('id')} {title}")
        issue = normalize_qvuuqs_id(record.get("number"))
        if issue is None:
            issue = normalize_qvuuqs_id(record.get("periodStr"))
        if issue is None or not (100 <= issue <= 999):
            raise ValueError(f"柔情杀手文章期数字段无效: {record.get('id')}")
        content = str(record.get("description") or "").strip()
        if not content:
            raise ValueError(f"柔情杀手文章正文为空: {issue}期")
        if f"{issue}期" not in content:
            raise ValueError(f"柔情杀手文章正文未包含自身期数: {issue}期")
        previous = documents.get(issue)
        if previous is not None and previous != content:
            raise ValueError(f"柔情杀手同一期存在多条冲突文章: {issue}期")
        documents[issue] = content
    return documents


def collect_rourqing_shashou_documents(site: Site, period: int | None = None, timeout: int = 20) -> list[str]:
    user_id = extract_rourqing_shashou_user_id(site.url)
    if user_id is None:
        raise ValueError("柔情杀手用户页URL缺少有效用户ID")
    with _browser_page() as page:
        open_qvuuqs_page(page, site.url, timeout)
        payload = fetch_qvuuqs_json(
            page,
            f"{ROURQING_SHASHOU_PUBLISH_PATH}?userId={user_id}&type=3&pageNum=1"
            "&title=&newVersion=1&lotteryType=0",
        )
    documents = parse_rourqing_shashou_publish(payload, user_id)
    if period is None:
        return [documents[issue] for issue in sorted(documents)]
    if period not in documents:
        raise ValueError(f"未找到指定期数: 柔情杀手用户页未发布 {period}期")
    return [documents[period]]


def collect_rendered_documents(url: str, timeout: int = 20, retries: int = 1) -> list[str]:
    page_timeout = timeout * 1000
    with _browser_page() as page:
        for attempt in range(retries + 1):
            try:
                try:
                    page.goto(url, wait_until="networkidle", timeout=page_timeout)
                except Exception:
                    page.goto(url, wait_until="domcontentloaded", timeout=page_timeout)
                    page.wait_for_timeout(1500)
                return [page.locator("body").inner_text(timeout=5000), page.content()]
            except Exception:
                if attempt == retries:
                    raise


def reference_post_matches(text: str, today: str, keyword: str, issue: int | None = None) -> bool:
    if keyword not in text:
        return False
    if issue is not None and f"{issue}期" in text:
        return True
    return today in text


def collect_reference_post_documents(
    url: str, keyword: str, timeout: int = 20, today: str | None = None, issue: int | None = None
) -> list[str]:
    if is_qvuuqs_host(url):
        return collect_qvuuqs_reference_documents(url, keyword, issue, timeout)
    user_id, record_id = extract_qvuuqs_route(url)
    if record_id is None:
        raise ValueError("动态引用页URL缺少文章记录ID")
    with _browser_page() as page:
        open_qvuuqs_page(page, url, timeout)
        payload = fetch_qvuuqs_json(page, f"/api/v1/forums/{record_id}")
        record, _ = locate_qvuuqs_record(payload, record_id)
        validated = validate_qvuuqs_reference_record(record, user_id, record_id, keyword)
        return [str(validated["content"])]


def extract_topic_record_id(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    match = re.search(r"/topic/(\d+)(?:\.html)?$", path, re.I)
    if not match:
        raise ValueError("iframe详情页URL缺少topic文章ID")
    return match.group(1)


def validate_iframe_topic_page(
    final_url: str,
    expected_topic_id: str,
    site_name: str,
    article_count: int,
    heading: str,
    body: str,
) -> list[str]:
    actual_topic_id = extract_topic_record_id(final_url)
    if actual_topic_id != str(expected_topic_id):
        raise ValueError(f"iframe详情页URL文章ID不一致: 期望{expected_topic_id},实际{actual_topic_id}")
    if article_count != 1:
        raise ValueError(f"iframe详情页文章容器不唯一: {article_count}条")
    normalized_heading = heading.translate(TEXT_TRANS)
    if site_name not in normalized_heading or "绝杀一波" not in normalized_heading:
        raise ValueError(f"iframe详情页标题不匹配: {site_name}/绝杀一波")
    if not body.strip() or "绝杀一波" not in body.translate(TEXT_TRANS):
        raise ValueError(f"iframe详情页正文不匹配: {site_name}/绝杀一波")
    return [heading, body]


def collect_iframe_topic_documents(site: Site, period: int | None = None, timeout: int = 20) -> list[str]:
    expected_topic_id = extract_topic_record_id(site.url)
    page_timeout = timeout * 1000
    with _browser_page() as page:
        page.goto(site.url, wait_until="domcontentloaded", timeout=page_timeout)
        article = page.locator(".detail_info_forum2_item")
        article.first.wait_for(state="attached", timeout=page_timeout)
        article_count = article.count()
        target = article.first
        heading = target.locator(".forum-head").inner_text(timeout=5000)
        body = target.locator(".forum-body").inner_text(timeout=5000)
        return validate_iframe_topic_page(
            page.url,
            expected_topic_id,
            site.name,
            article_count,
            heading,
            body,
        )


def collect_anju_ziliaoyuan_documents(url: str, issue: int | None, timeout: int = 20) -> list[str]:
    documents = collect_reference_post_documents(url, "绝杀一波", timeout=timeout, issue=issue)
    if issue is None:
        return documents
    combined = "\n".join(documents)
    pattern = rf"{issue}\s*期\s*[:：]?\s*绝杀一波.*?[【\[]\s*(?:红波|蓝波|绿波)\s*[】\]]"
    if not re.search(pattern, combined.translate(TEXT_TRANS)):
        raise RuntimeError(f"安居资料员未进入指定期数详情或未匹配到数据: {issue}期绝杀一波")
    return documents

def plain_lines(documents: list[str]) -> list[str]:
    parser = PlainTextParser()
    parser.feed("\n".join(documents))
    text = html.unescape("".join(parser.parts))
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]


def extract_shenggong_article_documents(
    fragments: list[str], site_name: str = SHENGGONG_ZHIGUO_NAME
) -> list[str]:
    starts: list[int] = []
    for index, fragment in enumerate(fragments[:-1]):
        title_text = " ".join(plain_lines([fragment])).translate(TEXT_TRANS)
        author_text = " ".join(plain_lines([fragments[index + 1]])).translate(TEXT_TRANS)
        if re.search(r"(?<!\d)\d{1,4}\s*期.{0,40}?绝杀\s*一波", title_text) and re.search(
            rf"(?<![一-龥A-Za-z0-9]){re.escape(site_name)}(?![一-龥A-Za-z0-9])",
            author_text,
        ):
            starts.append(index)
    if not starts:
        return []
    if len(starts) != 1:
        raise ValueError("同一脚本中生功止过文章边界不唯一")

    start = starts[0]
    end = len(fragments)
    for index in range(start + 2, len(fragments)):
        boundary_text = " ".join(plain_lines([fragments[index]]))
        if "上一篇" in boundary_text or "下一篇" in boundary_text:
            end = index
            break
    return fragments[start:end]


def collect_shenggong_documents(site: Site, timeout: int = 20) -> list[str]:
    expected_topic_id = extract_topic_record_id(site.url)
    main_document, final_url = fetch_text_with_final_url(site.url, timeout)
    if extract_topic_record_id(final_url) != expected_topic_id:
        raise ValueError(
            f"生功止过topic ID不一致: 期望{expected_topic_id},实际{extract_topic_record_id(final_url)}"
        )

    articles: list[list[str]] = []
    seen_scripts: set[str] = set()
    for match in SCRIPT_SRC_RE.finditer(main_document):
        script_url = urljoin(site.url, match.group(2))
        if "/upload/script/" not in script_url.lower() or script_url in seen_scripts:
            continue
        seen_scripts.add(script_url)
        fragments = decode_strdecode_blocks(fetch_text(script_url, timeout))
        article = extract_shenggong_article_documents(fragments, site.name)
        if article:
            articles.append(article)
    if not articles:
        raise ValueError("未找到生功止过同源文章区块")
    if len(articles) != 1:
        raise ValueError("生功止过同源文章区块不唯一")
    return articles[0]


def extract_zhunsha_article_documents(fragments: list[str]) -> list[str]:
    starts = [
        index
        for index, fragment in enumerate(fragments)
        if re.search(
            r"(?<!\d)\d{1,4}\s*期\s*[:：]\s*[【\[]\s*准杀一波\s*[】\]]",
            " ".join(plain_lines([fragment])).translate(TEXT_TRANS),
        )
    ]
    if not starts:
        return []
    if len(starts) != 1:
        raise ValueError("同一脚本中准杀一波文章边界不唯一")

    article: list[str] = []
    for fragment in fragments[starts[0] :]:
        article.append(fragment)
        lines = plain_lines([fragment])
        if any("站长宣言" in line or "上一篇" in line or "下一篇" in line for line in lines):
            break
    return article


def collect_zhunsha_documents(site: Site, timeout: int = 20) -> list[str]:
    expected_topic_id = extract_topic_record_id(site.url)
    main_document, final_url = fetch_text_with_final_url(site.url, timeout)
    actual_topic_id = extract_topic_record_id(final_url)
    if actual_topic_id != expected_topic_id:
        raise ValueError(f"准杀一波topic ID不一致: 期望{expected_topic_id},实际{actual_topic_id}")

    articles: list[list[str]] = []
    seen_scripts: set[str] = set()
    for match in SCRIPT_SRC_RE.finditer(main_document):
        script_url = urljoin(site.url, match.group(2))
        if "/upload/script/" not in script_url.lower() or script_url in seen_scripts:
            continue
        seen_scripts.add(script_url)
        script_document = fetch_text(script_url, timeout)
        fragments = [script_document]
        seen_fragments = {script_document}
        for _ in range(3):
            additions: list[str] = []
            for fragment in fragments:
                for decoded in decode_strdecode_blocks(fragment):
                    if decoded in seen_fragments:
                        continue
                    seen_fragments.add(decoded)
                    additions.append(decoded)
            if not additions:
                break
            fragments.extend(additions)
        article = extract_zhunsha_article_documents(fragments)
        if article:
            articles.append(article)
    if not articles:
        raise ValueError("未找到准杀一波同源文章区块")
    if len(articles) != 1:
        raise ValueError("准杀一波同源文章区块不唯一")
    return articles[0]


def normalize_wave_value(value: str) -> str | None:
    if value in WAVE_VALUES:
        return value
    if value and len(set(value)) == 1 and value[0] in "红蓝绿":
        return f"{value[0]}波"
    return None


def missing_wave_value(first: str, second: str) -> str | None:
    first = normalize_wave_value(first) or first
    second = normalize_wave_value(second) or second
    values = {first, second}
    if len(values) != 2 or not values.issubset(WAVE_VALUES):
        return None
    return next(iter(WAVE_VALUES - values))


def extract_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    full_text = "\n".join(documents).translate(TEXT_TRANS)
    allow_formula_wave = "公式杀波" in full_text
    allow_double_wave = not allow_formula_wave
    lines = plain_lines(documents)
    table_section = False
    table_header_seen = False
    table_section_lines = 0
    for index, line in enumerate(lines):
        normalized = line.translate(TEXT_TRANS)
        matches = [(match, line) for match in ISSUE_FIRST_RE.finditer(normalized)]
        matches.extend((match, line) for match in KEYWORD_FIRST_RE.finditer(normalized))
        if "综合绝杀" in normalized:
            table_section = True
            table_header_seen = "杀一波" in normalized
            table_section_lines = 0
        elif table_section and "『" in normalized and "』" in normalized:
            table_section = False
            table_header_seen = False
        elif table_section and table_section_lines > 40:
            table_section = False
            table_header_seen = False
        if table_section:
            table_section_lines += 1
            if "杀一波" in normalized:
                table_header_seen = True
        if table_section and table_header_seen:
            row_parts: list[str] = []
            for offset, part in enumerate(lines[index : index + 6]):
                normalized_part = part.translate(TEXT_TRANS)
                if offset and "『" in normalized_part and "』" in normalized_part:
                    break
                row_parts.append(part)
            row_text = " ".join(row_parts).translate(TEXT_TRANS)
            matches.extend((match, match.group(0)) for match in TABLE_ROW_RE.finditer(row_text))
            matches.extend((match, match.group(0)) for match in TABLE_SINGLE_WAVE_ROW_RE.finditer(row_text))
        if allow_formula_wave:
            matches.extend((match, line) for match in FORMULA_WAVE_RE.finditer(normalized))
        for match, source_line in matches:
            issue = int(match.group(1))
            value = normalize_wave_value(match.group(2))
            if value is None:
                continue
            key = (issue, value, source_line)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(Candidate(issue, value, source_line, len(candidates)))
        if allow_double_wave:
            double_wave_matches = list(DOUBLE_WAVE_RE.finditer(normalized))
            if "主双波" in full_text or "必中双波" in full_text:
                double_wave_matches.extend(TABLE_DOUBLE_WAVE_RE.finditer(normalized))
            double_wave_matches.extend(DOTTED_DOUBLE_WAVE_RE.finditer(normalized))
            double_wave_matches.extend(EXACT_TWO_COLOR_BRACKET_RE.finditer(normalized))
            for match in double_wave_matches:
                issue = int(match.group(1))
                value = missing_wave_value(match.group(2), match.group(3))
                if value is None:
                    continue
                source_line = match.group(0)
                key = (issue, value, source_line)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(Candidate(issue, value, source_line, len(candidates)))
    explicit_issues = {
        item.issue
        for item in candidates
        if not DOUBLE_WAVE_RE.search(item.line.translate(TEXT_TRANS))
    }
    return [
        item
        for item in candidates
        if item.issue not in explicit_issues or not DOUBLE_WAVE_RE.search(item.line.translate(TEXT_TRANS))
    ]


def extract_focus_candidates(documents: list[str], focus_title: str) -> list[Candidate]:
    lines = plain_lines(documents)
    focused: list[str] = []
    registered_titles = (
        REGISTERED_FOCUS_SITE_NAMES
        | STRICT_REGION_NAMES
        | REFERENCE_EXACT_SHA_YIBO_NAMES
        | EXACT_SHA_YIBO_SITE_NAMES
        | NEW_MISSING_WAVE_SITE_NAMES
        | NEW_TABLE_SHA_YIBO_SITE_NAMES
        | set(KEYWORD_VARIANT_SITE_KEYWORDS)
        | {
            ANJU_ZILIAOYUAN_NAME,
            "世外桃源",
            "朱雀",
            "六表主",
            "巴扎嘿",
            "龙啸九天",
            "二肖四码",
            "荷花莲藕",
            "袁家大少",
            "千人一面",
            "水果奶奶",
            "瞬杀一波",
            "王者",
            "六合皇",
            "白蛇传",
            "潮余诗音",
            "后起之秀",
            "六玄网",
            "柔情杀手",
            "准杀一波",
            "公式杀",
        }
    )
    for index, line in enumerate(lines):
        if focus_title and re.search(rf"(?<![一-龥A-Za-z0-9]){re.escape(focus_title)}(?![一-龥A-Za-z0-9])", line):
            section = [line]
            for next_line in lines[index + 1 : index + 220]:
                stripped = next_line.strip()
                is_registered_title = any(
                    name != focus_title
                    and re.search(rf"(?<![一-龥A-Za-z0-9]){re.escape(name)}(?![一-龥A-Za-z0-9])", stripped)
                    for name in registered_titles
                )
                is_obvious_section = bool(
                    stripped
                    and not re.search(r"(?<!\d)\d{1,4}\s*期", stripped)
                    and re.search(r"[『【].{1,30}(?:绝杀|杀一波|双波|波色).{0,10}[』】]", stripped)
                )
                if is_registered_title or is_obvious_section:
                    break
                section.append(next_line)
            focused.extend(section)
    if not focused:
        return []
    return extract_candidates(["\n".join(focused)])


def extract_exact_sha_yibo_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    for line in plain_lines(documents):
        normalized = line.translate(TEXT_TRANS)
        for match in EXACT_SHA_YIBO_RE.finditer(normalized):
            issue = int(match.group(1))
            value = normalize_wave_value(match.group(2))
            if value is None:
                continue
            key = (issue, value, line)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(Candidate(issue, value, line, len(candidates)))
        spaced_match = re.search(r"(?<!\d)(\d{1,4})\s*期.{0,12}?绝\s*杀\s*([红蓝绿])\s*波", normalized)
        if spaced_match:
            issue = int(spaced_match.group(1))
            value = normalize_wave_value(f"{spaced_match.group(2)}波")
            if value is not None:
                key = (issue, value, line)
                if key not in seen:
                    seen.add(key)
                    candidates.append(Candidate(issue, value, line, len(candidates)))
    return candidates


def extract_zqbx_candidates(documents: list[str]) -> list[Candidate]:
    """自强不息专属解析：帖子是「每期在顶部追加一行」的累计序列。

    本轮行从首行开始逐期递减（本期在前），跨年时序列在 001→365 处回卷，
    回卷之后的行属于上一轮，期号标签与本轮相同但并非本期数据
    （273 期形态：顶部本轮 273 未开行 + 底部上一轮 273 已开行）。
    只保留从首行起、单调递减的当前轮次行，回卷后的上一轮行一律不作为候选，
    既不参与冲突判定，也不能当作指定期数的兜底来源。
    """
    current_cycle: list[Candidate] = []
    previous_issue: int | None = None
    for item in extract_exact_sha_yibo_candidates(documents):
        if previous_issue is not None and item.issue > previous_issue:
            break
        current_cycle.append(item)
        previous_issue = item.issue
    return current_cycle


def extract_shiwai_taoyuan_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    lines = plain_lines(documents)
    for index, line in enumerate(lines):
        normalized = line.translate(TEXT_TRANS)
        issue_match = BUY_TWO_WAVE_RE.search(normalized)
        if not issue_match or index + 1 >= len(lines):
            continue
        color_match = TWO_COLOR_LINE_RE.search(lines[index + 1].translate(TEXT_TRANS))
        if not color_match:
            continue
        value = missing_wave_value(color_match.group(1), color_match.group(2))
        if value is None:
            continue
        issue = int(issue_match.group(1))
        source_line = f"{line} {lines[index + 1]}"
        key = (issue, value, source_line)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(Candidate(issue, value, source_line, len(candidates)))
    return candidates


def extract_zhuque_candidates(documents: list[str]) -> list[Candidate]:
    lines = plain_lines(documents)
    focused: list[str] = []
    for index, line in enumerate(lines):
        if "『综合绝杀』" in line:
            focused.extend(lines[index : index + 120])
    if not focused:
        return []
    return extract_candidates(["\n".join(focused)])


def extract_liubiao_candidates(documents: list[str]) -> list[Candidate]:
    lines = plain_lines(documents)
    focused: list[str] = []
    for index, line in enumerate(lines):
        if "六表主双波" in line:
            focused.extend(lines[index : index + 120])
    if not focused:
        return []
    return extract_candidates(["\n".join(focused)])


def extract_bazahei_candidates(documents: list[str]) -> list[Candidate]:
    lines = plain_lines(documents)
    focused: list[str] = []
    for index, line in enumerate(lines):
        if "绝杀一波" not in line or "巴扎嘿" not in line:
            continue
        for candidate_line in lines[index : index + 120]:
            if candidate_line != line and "◇◇" in candidate_line:
                break
            focused.append(candidate_line)
    if not focused:
        return []
    return extract_exact_sha_yibo_candidates(["\n".join(focused)])


def extract_longxiao_jiutian_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    lines = plain_lines(documents)
    focused: list[str] = []
    for index, line in enumerate(lines):
        normalized = line.translate(TEXT_TRANS)
        if "龙啸九天" in normalized and "绝杀壹波" in normalized:
            for item in lines[index + 1 : index + 80]:
                item_normalized = item.translate(TEXT_TRANS)
                if re.search(r"(?<!\d)\d{1,4}\s*期\s*[:：]?\s*【", item_normalized):
                    break
                focused.append(item)
            break
    pattern = re.compile(r"(?<!\d)(\d{1,4})\s*期\s*[:：]?.{0,12}?绝杀壹波.{0,8}?◆\s*([红蓝绿])波\s*◆")
    for line in focused:
        normalized = line.translate(TEXT_TRANS)
        match = pattern.search(normalized)
        if not match:
            continue
        issue = int(match.group(1))
        value = normalize_wave_value(f"{match.group(2)}波")
        if value is None:
            continue
        key = (issue, value, line)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(Candidate(issue, value, line, len(candidates)))
    return candidates


def extract_erxiao_sima_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    lines = plain_lines(documents)
    pattern = re.compile(r"(?<!\d)(\d{1,4})\s*期\s*[:：]?.{0,8}?绝杀\s*一波\s*[【\[]\s*([红蓝绿])波\s*[】\]]")
    for index, line in enumerate(lines):
        if "澳门二肖四码" not in line:
            continue
        start: int | None = None
        for title_index in range(index, min(len(lines), index + 8)):
            title_line = re.sub(r"<[^>]+>", "", lines[title_index]).strip()
            if "综合绝杀区" in title_line:
                break
            if re.search(r"[『【\[]\s*绝杀一波\s*[』】\]]", title_line):
                start = title_index + 1
                break
        if start is None:
            continue
        for source_line in lines[start : start + 80]:
            if "澳门二肖四码" in source_line or "综合绝杀区" in source_line:
                break
            match = pattern.search(source_line)
            if not match:
                continue
            issue = int(match.group(1))
            value = normalize_wave_value(f"{match.group(2)}波")
            if value is None:
                continue
            key = (issue, value, source_line)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(Candidate(issue, value, source_line, len(candidates)))
    return candidates




def extract_hehua_lianou_candidates(documents: list[str]) -> list[Candidate]:
    lines = plain_lines(documents)
    focused: list[str] = []
    for index, line in enumerate(lines):
        if "荷花莲藕" in line:
            focused.extend(lines[max(0, index - 3) : index + 80])
            break
    if not focused:
        return []
    unique: list[Candidate] = []
    seen_issues: set[int] = set()
    for item in extract_candidates(["\n".join(focused)]):
        if item.issue in seen_issues:
            continue
        if "波色中特" not in item.line:
            continue
        seen_issues.add(item.issue)
        unique.append(Candidate(item.issue, item.value, item.line, len(unique)))
    return unique

def extract_yuanjia_dashao_candidates(documents: list[str]) -> list[Candidate]:
    lines = plain_lines(documents)
    focused: list[str] = []
    for index, line in enumerate(lines):
        if "袁家大少" in line:
            focused.extend(lines[max(0, index - 3) : index + 180])
            break
    if not focused:
        return []
    unique: list[Candidate] = []
    seen_issues: set[int] = set()
    for item in extract_candidates(["\n".join(focused)]):
        if item.issue in seen_issues:
            continue
        seen_issues.add(item.issue)
        unique.append(Candidate(item.issue, item.value, item.line, len(unique)))
    return unique

def extract_qianren_yimian_candidates(documents: list[str]) -> list[Candidate]:
    lines = plain_lines(documents)
    focused: list[str] = []
    for index, line in enumerate(lines):
        if "千人一面" in line and "经典两波" in line:
            focused.extend(lines[index : index + 260])
            break
    if not focused:
        return []
    return extract_candidates(["\n".join(focused)])

NEW_MISSING_WAVE_SITE_NAMES = {"澳门118开奖", "藏宝图", "目中无人", "牵肠挂肚", "波王波王"}
TWO_WAVE_MISSING_SITE_NAMES = {"捉襟见肘", "扑朔迷离"}
YOUYA_XIAOSHU_NAME = "优雅小树"
XIASHUO_BAIDAO_NAME = "瞎说白道"
NEW_TABLE_SHA_YIBO_SITE_NAMES = {"招财猫", "玄机", "玄机阁", "今日闲情"}
RENDERED_PRIMARY_SITE_NAMES = {"金多宝", "八步毛哥", "六合皇", "瞬杀一波", "王者", "六玄网", "招财猫", "玄机", "玄机阁", "藏宝图", "今日闲情", "捉襟见肘", "扑朔迷离", YOUYA_XIAOSHU_NAME}


def extract_missing_wave_pair_candidates(documents: list[str], site_name: str) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    lines = plain_lines(documents)
    if site_name == "波王波王":
        issue_pattern = re.compile(r"(?<!\d)(\d{1,4})\s*期\s*波王一波")
        colors_pattern = re.compile(r"波王双波\s*[【\[]\s*([红蓝绿])波\s*([红蓝绿])波\s*[】\]]")
        for index, line in enumerate(lines[:-1]):
            issue_match = issue_pattern.search(line.translate(TEXT_TRANS))
            if not issue_match:
                continue
            second_line = lines[index + 1]
            color_match = colors_pattern.search(second_line.translate(TEXT_TRANS))
            if not color_match:
                continue
            value = missing_wave_value(f"{color_match.group(1)}波", f"{color_match.group(2)}波")
            if value is None:
                continue
            issue = int(issue_match.group(1))
            key = (issue, value, second_line)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(Candidate(issue, value, second_line, len(candidates)))
        return candidates

    patterns = [
        re.compile(r"(?<!\d)(\d{1,4})\s*期.{0,20}?[【\[]\s*([红蓝绿])波\s*[】\]].{0,8}?[【\[]\s*([红蓝绿])波\s*[】\]]"),
        re.compile(r"(?<!\d)(\d{1,4})\s*期.{0,20}?主\s*([红蓝绿])波\s*[,，]?\s*防\s*([红蓝绿])波"),
        re.compile(r"(?<!\d)(\d{1,4})\s*期.{0,30}?[【\[]\s*([红蓝绿])波\s*防\s*([红蓝绿])波\s*[】\]]"),
        re.compile(r"(?<!\d)(\d{1,4})\s*期.{0,30}?波王双波\s*[【\[]\s*([红蓝绿])波\s*([红蓝绿])波\s*[】\]]"),
    ]
    for line in lines:
        normalized = line.translate(TEXT_TRANS)
        for pattern in patterns:
            match = pattern.search(normalized)
            if not match:
                continue
            value = missing_wave_value(f"{match.group(2)}波", f"{match.group(3)}波")
            if value is None:
                continue
            issue = int(match.group(1))
            key = (issue, value, line)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(Candidate(issue, value, line, len(candidates)))
            break
    return candidates


def extract_two_wave_missing_candidates(documents: list[str], pattern: re.Pattern[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    for line in plain_lines(documents):
        match = pattern.search(line.translate(TEXT_TRANS))
        if not match:
            continue
        value = missing_wave_value(f"{match.group(2)}波", f"{match.group(3)}波")
        if value is None:
            continue
        issue = int(match.group(1))
        key = (issue, value, match.group(0))
        if key in seen:
            continue
        seen.add(key)
        candidates.append(Candidate(issue, value, match.group(0), len(candidates)))
    return candidates


def extract_zhuojin_jianzhou_candidates(documents: list[str]) -> list[Candidate]:
    pattern = re.compile(
        r"(?<!\d)(\d{1,4})\s*期[^\r\n]{0,20}?《\s*两波中特\s*》\s*《\s*([红蓝绿])波\s*([红蓝绿])波\s*》"
    )
    return extract_two_wave_missing_candidates(documents, pattern)


def _find_seam(issues: list[int]) -> tuple[int | None, bool]:
    """定位跨年接缝，返回 (接缝下标, 去年段是否在前)。

    本项目期号 = 年内第几天（1..365），所以「365 和 001 同时出现」才是跨年接缝，
    阈值必须用 >=300 与 <=10，不能用 >10（否则 001..012 这种升序段会假接缝）。
    - 365 -> 001：去年段在前，接缝在 index，今年段从 index 起
    - 001 -> >=300：今年段在前，接缝在 index，去年段从 index 起
    """
    if len(issues) < 2:
        return None, False
    for index in range(1, len(issues)):
        prev_issue, curr_issue = issues[index - 1], issues[index]
        if prev_issue >= 300 and curr_issue <= 10:
            return index, True
        if prev_issue <= 10 and curr_issue >= 300:
            return index, False
    return None, False


def _keep_first_descending_run(candidates: list[Candidate]) -> list[Candidate]:
    """跨年绕回时只保留今年那一段（去年段在后时截尾，在前时跳过）。

    只在 _find_seam 明确识别出跨年接缝时才动手；升序站、缺期站、
    段内插大期号等情况一律原样返回，不做任何截断。
    """
    if len(candidates) < 2:
        return candidates
    issues = [item.issue for item in candidates]
    seam, old_first = _find_seam(issues)
    if seam is None:
        return candidates
    if old_first:
        # 去年段在前，今年段在 seam 之后
        return candidates[seam:]
    return candidates[:seam]


_PENDING_DRAW_PATTERN = re.compile(r"开\s*[:：?？]?\s*0{2,}")


def _is_pending_period_candidate(candidate: "Candidate", issue: int) -> bool:
    """目标期的下一期若尚未开奖，属待开期，不能当作「旧年更大期号」的证据。

    页面在新一期开奖前会先挂出该期（开0000/开：00/开？00），
    若把它当成旧年数据，全站都会在「目标期 = 最新已开期」时被误杀。
    """
    if candidate.issue != issue + 1:
        return False
    line = candidate.line or ""
    if _PENDING_DRAW_PATTERN.search(line):
        return True
    # 行被截断、看不到开奖标记时同样无法证明已开奖
    return "开" not in line


def _looks_like_stale_year_block(issues: list[int], issue: int) -> bool:
    """整段都是旧年数据的判据：出现比目标期更大的期号，却完全没有 <=10 的小期号。

    期号 = 年内第几天，所以「比目标期大」才可能是去年留下的更大期号
    （例如今年只到 298，页面却有 365）。反过来 300..291 这种当期窗口
    全部 <= 目标期，属正常，不能误判。

    真实跨年页面一定同时含 365 和 001；只有大期号一侧而没有 001，
    说明抓到的是去年那一段。
    """
    if not issues:
        return False
    return max(issues) > issue and not any(value <= 10 for value in issues)


def _reject_if_wrapped_before_target(
    candidates: list[Candidate], issue: int
) -> tuple[list[Candidate], str | None]:
    """判断目标期是否落在去年段里，是则判失败而不是借值。

    三道判据：
    1. 整段像旧年数据（有比目标期更大的期号但无 <=10）-> 直接失败。
    2. 有 365<->001 真接缝：按接缝两侧判定目标期属于今年段还是去年段。
    3. 无接缝：不做额外推断，交回原样。
    """
    issues = [item.issue for item in candidates]
    # 先判整段旧年：即便目标期根本不在里面，也要给出准确原因。
    # 顶部未开奖的下一期不算旧年证据。
    effective_issues = [
        item.issue for item in candidates if not _is_pending_period_candidate(item, issue)
    ]
    if _looks_like_stale_year_block(effective_issues, issue):
        return [], "列表已绕回，疑似旧年数据"

    positions = [index for index, item in enumerate(candidates) if item.issue == issue]
    if not positions:
        return candidates, None

    seam, old_first = _find_seam(issues)
    if seam is None:
        return candidates, None

    if old_first:
        # 去年段在前：目标期只要出现在 seam 之前，就是去年值
        if any(index < seam for index in positions):
            return [], "列表已绕回，疑似旧年数据"
        return candidates, None

    # 去年段在后：目标期只在 seam 之后，说明今年没发该期，拿到的是去年同号
    if all(index >= seam for index in positions):
        return [], "列表已绕回，疑似旧年数据"
    return candidates, None


def extract_pushuo_mili_candidates(documents: list[str]) -> list[Candidate]:
    pattern = re.compile(
        r"(?<!\d)(\d{1,4})\s*期[^\r\n]{0,20}?【\s*两波中特\s*】\s*[（(]\s*([红蓝绿])波\s*([红蓝绿])波\s*[）)]"
    )
    return extract_two_wave_missing_candidates(documents, pattern)


def extract_youya_xiaoshu_candidates(documents: list[str]) -> list[Candidate]:
    pattern = re.compile(
        r"(?<!\d)(\d{1,4})\s*期\s*[:：]?\s*两波中特\s*[【\[]\s*([红蓝绿])波\s*([红蓝绿])波\s*[】\]]"
    )
    return extract_two_wave_missing_candidates(documents, pattern)


def extract_table_sha_yibo_column_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    current_issue: int | None = None
    for line in plain_lines(documents):
        normalized = line.translate(TEXT_TRANS)
        full_match = re.search(r"(?<!\d)(\d{1,4})\s*期\s+\S+\s+\S+\s+([红蓝绿])波\s+\S+", normalized)
        paren_match = re.search(r"(?<!\d)(\d{1,4})\s*期\s*[（(][^）)]+[）)]\s*[（(]\s*([红蓝绿])\s*[）)]", normalized)
        issue_only = re.search(r"(?<!\d)(\d{1,4})\s*期\s*$", normalized)
        split_match = None if current_issue is None else re.search(r"\S+\s+\d+尾\s+([红蓝绿])波", normalized)

        if full_match:
            issue = int(full_match.group(1))
            value = normalize_wave_value(f"{full_match.group(2)}波")
        elif paren_match:
            issue = int(paren_match.group(1))
            value = normalize_wave_value(f"{paren_match.group(2)}波")
        elif issue_only:
            current_issue = int(issue_only.group(1))
            continue
        elif split_match:
            issue = current_issue
            value = normalize_wave_value(f"{split_match.group(1)}波")
            current_issue = None
        else:
            continue

        if value is None:
            continue
        key = (issue, value, line)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(Candidate(issue, value, line, len(candidates)))
    return candidates


def extract_babu_maoge_candidates(documents: list[str]) -> list[Candidate]:
    lines = plain_lines(documents)
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    row_pattern = re.compile(
        r"(?<!\d)(\d{1,4})\s*期\s+\S+\s+\d+尾\s+([红蓝绿])[单双]\s+\d+头(?:\s+\S+)?"
    )
    for index, line in enumerate(lines):
        normalized = line.translate(TEXT_TRANS)
        if "八步毛哥" not in normalized or "综合杀料" not in normalized:
            continue
        for source_line in lines[index + 1 : index + 120]:
            source_normalized = source_line.translate(TEXT_TRANS)
            if "八步毛哥" in source_normalized and "【" in source_normalized:
                break
            match = row_pattern.search(source_normalized)
            if not match:
                continue
            issue = int(match.group(1))
            value = normalize_wave_value(f"{match.group(2)}波")
            if value is None:
                continue
            key = (issue, value, source_line)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(Candidate(issue, value, source_line, len(candidates)))
        break
    return candidates


def extract_shuiguo_nainai_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    for line in plain_lines(documents):
        normalized = line.translate(TEXT_TRANS)
        match = re.search(r"(?<!\d)(\d{1,4})\s*期.{0,20}?绝杀一波.{0,8}?[【\[]\s*([红蓝绿])\s*[单双]\s*[】\]]", normalized)
        if not match:
            continue
        value = normalize_wave_value(f"{match.group(2)}波")
        if value is None:
            continue
        issue = int(match.group(1))
        key = (issue, value, line)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(Candidate(issue, value, line, len(candidates)))
    return candidates


def extract_shunsha_yibo_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    lines = plain_lines(documents)
    for index, line in enumerate(lines):
        normalized = line.translate(TEXT_TRANS)
        issue_match = re.search(r"(?<!\d)(\d{1,4})\s*期.{0,12}?瞬杀一波", normalized)
        if not issue_match or index + 1 >= len(lines):
            continue
        color_match = re.search(r"[【\[]\s*([红蓝绿])\s*[】\]]", lines[index + 1].translate(TEXT_TRANS))
        if not color_match:
            continue
        value = normalize_wave_value(f"{color_match.group(1)}波")
        if value is None:
            continue
        issue = int(issue_match.group(1))
        source_line = f"{line} {lines[index + 1]}"
        key = (issue, value, source_line)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(Candidate(issue, value, source_line, len(candidates)))
    return candidates


def extract_wangzhe_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    current_issue: int | None = None
    for line in plain_lines(documents):
        normalized = line.translate(TEXT_TRANS)
        issue_match = re.search(r"(?<!\d)(\d{1,4})\s*期[杀号肖]*统计", normalized)
        if issue_match:
            current_issue = int(issue_match.group(1))
            continue
        if current_issue is None or "杀一波图" not in normalized:
            continue
        color_match = re.search(r"[【\[]\s*([红蓝绿])波\s*[】\]]", normalized)
        if not color_match:
            continue
        value = normalize_wave_value(f"{color_match.group(1)}波")
        if value is None:
            continue
        key = (current_issue, value, line)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(Candidate(current_issue, value, line, len(candidates)))
    return candidates


def extract_baishezhuan_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    pattern = re.compile(r"(?<!\d)(\d{1,4})\s*期\s*[:：]?.{0,20}?走势杀波.{0,8}?[【\[]\s*([红蓝绿])波\s*[】\]]")
    for line in plain_lines(documents):
        normalized = line.translate(TEXT_TRANS)
        match = pattern.search(normalized)
        if not match:
            continue
        value = normalize_wave_value(f"{match.group(2)}波")
        if value is None:
            continue
        issue = int(match.group(1))
        key = (issue, value, line)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(Candidate(issue, value, line, len(candidates)))
    return candidates


def extract_chaoyu_shiyin_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    pattern = re.compile(r"(?<!\d)(\d{1,4})\s*期.{0,30}?稳杀.{0,8}?[【\[]\s*([红蓝绿])波\s*[】\]]")
    for line in plain_lines(documents):
        normalized = line.translate(TEXT_TRANS)
        if "稳杀" not in normalized:
            continue
        match = pattern.search(normalized)
        if not match:
            continue
        value = normalize_wave_value(f"{match.group(2)}波")
        if value is None:
            continue
        issue = int(match.group(1))
        key = (issue, value, line)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(Candidate(issue, value, line, len(candidates)))
    return candidates


def extract_houqi_zhixiu_candidates(documents: list[str]) -> list[Candidate]:
    lines = plain_lines(documents)
    pattern = re.compile(r"(?<!\d)(\d{1,4})\s*期.{0,12}?绝杀一波.{0,8}?[【\[]\s*([红蓝绿])波\s*[】\]]")
    section_heading = re.compile(r"(?<!\d)\d{1,4}\s*期\s*[:：]?\s*[【\[]")
    start_index = next(
        (
            index
            for index, line in enumerate(lines)
            if "后起之秀" in line.translate(TEXT_TRANS) and "绝杀一波" in line.translate(TEXT_TRANS)
        ),
        None,
    )
    if start_index is None:
        return []

    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    for line in lines[start_index + 1 :]:
        normalized = line.translate(TEXT_TRANS)
        if section_heading.search(normalized) and "绝杀一波" not in normalized:
            break
        match = pattern.search(normalized)
        if not match:
            continue
        value = normalize_wave_value(f"{match.group(2)}波")
        if value is None:
            continue
        issue = int(match.group(1))
        key = (issue, value, line)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(Candidate(issue, value, line, len(candidates)))
    return candidates


def extract_xiashuo_baidao_candidates(documents: list[str]) -> list[Candidate]:
    lines = plain_lines(documents)
    pattern = re.compile(
        r"(?<!\d)(\d{1,4})\s*期\s*[【\[]\s*两波中特\s*[】\]]\s*"
        r"[【\[]\s*([红蓝绿])波\s*[+＋]\s*([红蓝绿])波\s*[】\]]"
    )
    section_heading = re.compile(r"(?<!\d)\d{1,4}\s*期\s*[:：]?\s*[【\[]")
    start_index = next(
        (
            index
            for index, line in enumerate(lines)
            if "瞎说白道" in line.translate(TEXT_TRANS) and "两波中特" in line.translate(TEXT_TRANS)
        ),
        None,
    )
    if start_index is None:
        return []

    focused: list[str] = []
    for line in lines[start_index + 1 :]:
        normalized = line.translate(TEXT_TRANS)
        if section_heading.search(normalized) and "两波中特" not in normalized:
            break
        focused.append(line)
    return extract_two_wave_missing_candidates(["\n".join(focused)], pattern)


def extract_liuxuanwang_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    lines = plain_lines(documents)
    pattern = re.compile(r"(?<!\d)(\d{1,4})\s*期\s*绝杀\s*一波\s*[【〖\[\(（]\s*([红蓝绿])波\s*[】〗\]\)）]")
    focused: list[str] = []
    for index, line in enumerate(lines):
        normalized = line.translate(TEXT_TRANS)
        nearby_title = " ".join(lines[index : index + 3]).translate(TEXT_TRANS)
        if "六玄网" in normalized and "绝杀一波" in nearby_title:
            title_end_index = next(
                (
                    title_index
                    for title_index in range(index, min(len(lines), index + 3))
                    if "绝杀一波" in lines[title_index].translate(TEXT_TRANS)
                ),
                index,
            )
            for source_index, source_line in enumerate(lines[index : index + 120], start=index):
                source_normalized = source_line.translate(TEXT_TRANS)
                if (
                    source_index > title_end_index
                    and "绝杀一波" in source_normalized
                    and not re.search(r"(?<!\d)\d{1,4}\s*期", source_normalized)
                ):
                    break
                focused.append(source_line)
            break
    if not focused:
        script_text = "\n".join(documents).translate(TEXT_TRANS)
        if "document.writeln" not in script_text or "绝杀一波" not in script_text:
            return []
        focused = lines
    for line in focused:
        normalized = line.translate(TEXT_TRANS)
        match = pattern.search(normalized)
        if not match:
            continue
        issue = int(match.group(1))
        value = normalize_wave_value(f"{match.group(2)}波")
        if value is None:
            continue
        key = (issue, value, line)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(Candidate(issue, value, line, len(candidates)))
    return candidates


def collect_liuxuanwang_documents(url: str, timeout: int = 20) -> list[str]:
    script_url = urljoin(url, "/cj/syibo.js")
    try:
        script_text = fetch_text(script_url, timeout)
        if extract_liuxuanwang_candidates([script_text]):
            return [script_text]
    except Exception:
        pass

    last_documents: list[str] = []
    for target_url in (urljoin(url, "/915577.html"), url):
        documents = collect_rendered_documents(target_url)
        last_documents = documents
        if extract_liuxuanwang_candidates(documents):
            return documents
    return last_documents


def extract_liuhehuang_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    container_documents: list[str] = []
    for document in documents:
        parser = ElementTextParser("con_jsxl_5")
        parser.feed(document)
        if parser.parts:
            container_documents.append("".join(parser.parts))
    if not container_documents:
        return []
    pattern = re.compile(r"(?<!\d)(\d{1,4})\s*期.{0,12}?杀一波色.{0,12}?[【〖\[]\s*([红蓝绿])波\s*[】〗\]]")
    for line in plain_lines(container_documents):
        normalized = line.translate(TEXT_TRANS)
        match = pattern.search(normalized)
        if not match:
            continue
        issue = int(match.group(1))
        value = normalize_wave_value(f"{match.group(2)}波")
        if value is None:
            continue
        key = (issue, value, line)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(Candidate(issue, value, line, len(candidates)))
    return candidates


KEYWORD_VARIANT_SITE_KEYWORDS = {
    "八步毛哥": ["砍杀一波"],
    "无错绝杀": ["杀一波"],
    "签牌": ["绝杀一波"],
    "巫马沉璧": ["杀一波"],
    "身强体壮": ["必杀一波"],
    "寄人篱下": ["绝杀一波"],
    "一台二妙": ["必杀一波"],
    "王牌特工": ["精杀一波"],
    "塞翁失马": ["绝杀一波"],
}


def extract_jinduobao_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    in_section = False
    pattern = re.compile(r"(?<!\d)(\d{1,4})\s*期\s*砍杀一波\s*[【\[]\s*杀?([红蓝绿])波\s*[】\]]")

    for line in plain_lines(documents):
        normalized = line.translate(TEXT_TRANS)
        if "金多宝" in normalized and "绝杀一波" in normalized:
            in_section = True
            continue
        if in_section and "金多宝" in normalized and "【" in normalized:
            break
        if not in_section:
            continue
        for match in pattern.finditer(normalized):
            value = normalize_wave_value(f"{match.group(2)}波")
            if value is not None:
                candidates.append(Candidate(int(match.group(1)), value, match.group(0), len(candidates)))
    return candidates

REGISTERED_FOCUS_SITE_NAMES = {
    "一代国色",
    "一剑一江",
    "井井有条",
    "交詈聚唾",
    "人尽皆知",
    "六彩圣君",
    "凤凰",
    "勉强而已啊",
    "南面称孤",
    "可怕人类",
    "司空隐舟",
    "失魂落魄",
    "如有神助",
    "婷容修态",
    "字载乾坤",
    "宁静致远",
    "尽力而为",
    "川岛出逃",
    "已洗妈咪",
    "平易近人",
    "平铺直叙",
    "广东八二站第二版",
    "彩民书籍",
    "心旌摇曳",
    "我服慈悲",
    "振奋人心",
    "掉龙华凤",
    "攻克专家",
    "无以言表",
    "无视一切",
    "无际草原",
    "智能",
    "未来世界",
    "来来回回",
    "林下风致",
    "桃花园长",
    "桃花没酒",
    "欢天喜地",
    "波霸少郎",
    "泪流满面",
    "海慧寺撒",
    "满目河山",
    "澳彩传奇",
    "爱答不理",
    "珠光宝气",
    "生功止过",
    "疏影横斜",
    "白虎",
    "目瞪口呆",
    "相关材料",
    "瞽瞍不移",
    "神奇澳门",
    "积于忽微",
    "窃窃私语",
    "自强不息",
    "致富经",
    "花心膝盖",
    "谁敢争雄",
    "豪放不羁",
    "财富快车",
    "踏雪",
    "软妹味道",
    "远赴相思",
    "针锋相对",
    "长乐未央",
    "闻风丧胆",
    "雨果天气",
    "清气若兰",
    "马道成功",
    "鸿运",
}


def extract_keyword_variant_candidates(documents: list[str], keywords: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    keyword_pattern = "|".join(re.escape(keyword) for keyword in keywords)
    pattern = re.compile(rf"(?<!\d)(\d{{1,4}})\s*期.{{0,20}}?(?:{keyword_pattern}).{{0,12}}?[【〖\[]\s*杀?([红蓝绿])(?:波|单|双)\s*[】〗\]]")
    for line in plain_lines(documents):
        normalized = line.translate(TEXT_TRANS)
        for match in pattern.finditer(normalized):
            value = normalize_wave_value(f"{match.group(2)}波")
            if value is None:
                continue
            issue = int(match.group(1))
            source = match.group(0)
            key = (issue, value, source)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(Candidate(issue, value, source, len(candidates)))
    return candidates


def extract_registered_focus_candidates(documents: list[str], site: Site) -> list[Candidate]:
    if site.keyword:
        candidates = extract_focus_candidates(documents, site.keyword)
        if candidates:
            return candidates
    return extract_focus_candidates(documents, site.name)


def extract_qvuuqs_reference_double_wave_candidates(documents: list[str], keyword: str) -> list[Candidate]:
    keyword_key = normalize_qvuuqs_field(keyword)
    lines = [line for line in plain_lines(documents) if keyword_key in normalize_qvuuqs_field(line)]
    candidates = extract_candidates(["\n".join(lines)]) if lines else []
    seen: set[tuple[int, str]] = set()
    unique: list[Candidate] = []
    for item in candidates:
        key = (item.issue, item.value)
        if key in seen:
            continue
        seen.add(key)
        unique.append(Candidate(item.issue, item.value, item.line, len(unique)))
    return unique


def extract_rourqing_shashou_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    pattern = re.compile(r"(?<!\d)(\d{1,4})\s*期.{0,20}?柔情杀手.{0,20}?绝杀\s*([红蓝绿])波")
    for line in plain_lines(documents):
        normalized = line.translate(TEXT_TRANS)
        for match in pattern.finditer(normalized):
            value = normalize_wave_value(f"{match.group(2)}波")
            if value is None:
                continue
            issue = int(match.group(1))
            source = match.group(0)
            key = (issue, value, source)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(Candidate(issue, value, source, len(candidates)))
    ordered = sorted(candidates, key=lambda item: item.issue)
    return [Candidate(item.issue, item.value, item.line, index) for index, item in enumerate(ordered)]

def extract_zhunsha_yibo_candidates(documents: list[str]) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen: set[tuple[int, str, str]] = set()
    patterns = [
        re.compile(r"(?<!\d)(\d{1,4})\s*期.{0,80}?T\d{1,2}\s*=\s*([红蓝绿])波"),
        re.compile(
            r"(?<!\d)(\d{1,4})\s*期.{0,20}?特杀一波\s*[:：]\s*([红蓝绿])(?:波)?(?![一-龥A-Za-z0-9])"
        ),
    ]
    for line in plain_lines(documents):
        normalized = line.translate(TEXT_TRANS)
        for pattern in patterns:
            for match in pattern.finditer(normalized):
                value = normalize_wave_value(f"{match.group(2)}波")
                if value is None:
                    continue
                issue = int(match.group(1))
                source = match.group(0)
                key = (issue, value, source)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(Candidate(issue, value, source, len(candidates)))
    return candidates

def extract_section_candidates(documents: list[str], section_title: str) -> list[Candidate]:
    lines = plain_lines(documents)
    focused: list[str] = []
    for index, line in enumerate(lines):
        if line.strip() == section_title:
            focused.extend(lines[index : index + 120])
    if not focused:
        return []
    return extract_candidates(["\n".join(focused)])


def is_strict_region(site: Site) -> bool:
    return site.name in STRICT_REGION_NAMES


def extract_primary_candidates(documents: list[str], site: Site) -> list[Candidate]:
    if site.name == SHENGGONG_ZHIGUO_NAME:
        return extract_exact_sha_yibo_candidates(documents)
    if site.name == "金多宝":
        return extract_jinduobao_candidates(documents)
    if site.name == "捉襟见肘":
        return extract_zhuojin_jianzhou_candidates(documents)
    if site.name == "扑朔迷离":
        return extract_pushuo_mili_candidates(documents)
    if site.name == YOUYA_XIAOSHU_NAME:
        return extract_youya_xiaoshu_candidates(documents)
    if site.name == "世外桃源":
        return extract_shiwai_taoyuan_candidates(documents)
    if site.name == "朱雀":
        return extract_zhuque_candidates(documents)
    if site.name == "六表主":
        return extract_liubiao_candidates(documents)
    if site.name == "巴扎嘿":
        return extract_bazahei_candidates(documents)
    if site.name == "龙啸九天":
        return extract_longxiao_jiutian_candidates(documents)
    if site.name == "二肖四码":
        return extract_erxiao_sima_candidates(documents)
    if site.name == "荷花莲藕":
        return extract_hehua_lianou_candidates(documents)
    if site.name == "袁家大少":
        return extract_yuanjia_dashao_candidates(documents)
    if site.name == "千人一面":
        return extract_qianren_yimian_candidates(documents)
    if site.name == "水果奶奶":
        return extract_shuiguo_nainai_candidates(documents)
    if site.name == "瞬杀一波":
        return extract_shunsha_yibo_candidates(documents)
    if site.name == "王者":
        return extract_wangzhe_candidates(documents)
    if site.name == "六合皇":
        return extract_liuhehuang_candidates(documents)
    if site.name == "白蛇传":
        return extract_baishezhuan_candidates(documents)
    if site.name == "潮余诗音":
        return extract_chaoyu_shiyin_candidates(documents)
    if site.name == XIASHUO_BAIDAO_NAME:
        return extract_xiashuo_baidao_candidates(documents)
    if site.name == "后起之秀":
        return extract_houqi_zhixiu_candidates(documents)
    if site.name == "六玄网":
        return extract_liuxuanwang_candidates(documents)
    if site.name == "柔情杀手":
        return extract_rourqing_shashou_candidates(documents)
    if site.name == "准杀一波":
        return extract_zhunsha_yibo_candidates(documents)
    if site.name == "八步毛哥":
        return extract_babu_maoge_candidates(documents)
    if site.name in KEYWORD_VARIANT_SITE_KEYWORDS:
        return extract_keyword_variant_candidates(documents, KEYWORD_VARIANT_SITE_KEYWORDS[site.name])
    if site.name in NEW_MISSING_WAVE_SITE_NAMES:
        return extract_missing_wave_pair_candidates(documents, site.name)
    if site.name in NEW_TABLE_SHA_YIBO_SITE_NAMES:
        return extract_table_sha_yibo_column_candidates(documents)
    if site.name == ANJU_ZILIAOYUAN_NAME:
        return extract_exact_sha_yibo_candidates(documents)
    if site.name in REFERENCE_EXACT_SHA_YIBO_NAMES:
        return extract_exact_sha_yibo_candidates(documents)
    if site.name in QVUUQS_REFERENCE_DOUBLE_WAVE_KEYWORDS:
        return extract_qvuuqs_reference_double_wave_candidates(
            documents, QVUUQS_REFERENCE_DOUBLE_WAVE_KEYWORDS[site.name]
        )
    if site.name == ZQBX_NAME:
        return extract_zqbx_candidates(documents)
    if site.name in IFRAME_TOPIC_SITE_NAMES:
        return extract_exact_sha_yibo_candidates(documents)
    if site.name in EXACT_SHA_YIBO_SITE_NAMES:
        return extract_exact_sha_yibo_candidates(documents)
    if site.keyword == "绝杀一波精准":
        return extract_exact_sha_yibo_candidates(documents)
    if is_strict_region(site):
        return extract_exact_sha_yibo_candidates(documents)
    if site.name == "公式杀":
        return extract_section_candidates(documents, "双波中特")
    if site.name in REGISTERED_FOCUS_SITE_NAMES:
        return extract_registered_focus_candidates(documents, site)
    return []


def missing_primary_reason(site: Site) -> str:
    if site.name == "金多宝":
        return "未匹配到金多宝专属解析栏目: 绝杀一波/砍杀一波"
    if site.name in TWO_WAVE_MISSING_SITE_NAMES:
        return "未匹配到两波中特专属解析格式: 期号+两波中特+两个波色"
    if site.name == YOUYA_XIAOSHU_NAME:
        return "未匹配到优雅小树专属解析格式: 期号+两波中特【两个波色】"
    if site.name == XIASHUO_BAIDAO_NAME:
        return "未匹配到瞎说白道专属解析栏目: 两波中特/缺少波色"
    if site.name == "世外桃源":
        return "未匹配到世外桃源专属解析关键字: 必买二波"
    if site.name == "朱雀":
        return "未匹配到朱雀专属解析栏目: 综合绝杀/杀一波"
    if site.name == "六表主":
        return "未匹配到六表主专属解析栏目: 六表主双波"
    if site.name == "巴扎嘿":
        return "未匹配到巴扎嘿专属解析栏目: 绝杀一波◇◇巴扎嘿"
    if site.name == "龙啸九天":
        return "未匹配到龙啸九天专属解析栏目: 绝杀壹波"
    if site.name == "二肖四码":
        return "未匹配到二肖四码专属解析栏目: 澳门二肖四码/『绝杀一波』"
    if site.name == "荷花莲藕":
        return "未匹配到荷花莲藕专属解析栏目: 波色中特"
    if site.name == "袁家大少":
        return "未匹配到袁家大少专属解析栏目: 两波中特"
    if site.name == "千人一面":
        return "未匹配到千人一面专属解析栏目: 经典两波"
    if site.name == "水果奶奶":
        return "未匹配到水果奶奶专属解析格式: 绝杀一波/红单蓝双"
    if site.name == "瞬杀一波":
        return "未匹配到瞬杀一波专属解析格式: 期号下一行颜色"
    if site.name == "王者":
        return "未匹配到王者专属解析格式: 杀一波图"
    if site.name == "六合皇":
        return "未匹配到六合皇专属解析栏目: 澳彩六合皇/绝杀系列/杀一波色"
    if site.name == "白蛇传":
        return "未匹配到白蛇传专属解析格式: 走势杀波"
    if site.name == "潮余诗音":
        return "未匹配到潮余诗音专属解析格式: 稳杀"
    if site.name == "后起之秀":
        return "未匹配到后起之秀专属解析格式: 绝杀一波"
    if site.name == "六玄网":
        return "未匹配到六玄网专属解析栏目: 澳彩六玄网/绝杀一波"
    if site.name == "柔情杀手":
        return "未匹配到柔情杀手专属解析格式: 绝杀X波"
    if site.name == "准杀一波":
        return "未匹配到准杀一波专属解析格式: T号=波色/特杀一波"
    if site.name == "八步毛哥":
        return "未匹配到八步毛哥专属解析栏目: 综合杀料/杀波"
    if site.name in KEYWORD_VARIANT_SITE_KEYWORDS:
        return "未匹配到站点专属一波变体解析格式"
    if site.name in NEW_MISSING_WAVE_SITE_NAMES:
        return "未匹配到双波取缺失波色专属解析格式"
    if site.name in NEW_TABLE_SHA_YIBO_SITE_NAMES:
        return "未匹配到表格杀一波列专属解析格式"
    if site.name == ANJU_ZILIAOYUAN_NAME:
        return "未匹配到安居资料员专属解析关键字: 绝杀一波"
    if site.name in QVUUQS_REFERENCE_DOUBLE_WAVE_KEYWORDS:
        return f"未匹配到{site.name}专属解析栏目: {QVUUQS_REFERENCE_DOUBLE_WAVE_KEYWORDS[site.name]}"
    if site.name in IFRAME_TOPIC_SITE_NAMES:
        return f"未匹配到{site.name}专属详情页解析栏目: 绝杀一波"
    if site.name in REFERENCE_EXACT_SHA_YIBO_NAMES:
        return "未匹配到用户页专属解析关键字: 绝杀一波"
    if site.name in EXACT_SHA_YIBO_SITE_NAMES:
        return "未匹配到站点专属解析关键字: 绝杀一波"
    if is_strict_region(site):
        return "未匹配到严格专属解析关键字: 绝杀一波"
    if site.name == "公式杀":
        return "未匹配到专属解析栏目: 双波中特"
    if site.name in REGISTERED_FOCUS_SITE_NAMES:
        return f"未匹配到已登记站点专属标题: {site.keyword or site.name}"
    return f"未登记站点级专属解析: {site.name}"


def select_candidate(candidates: list[Candidate], issue: int, pick: str) -> Candidate | None:
    candidate, _ = select_candidate_with_reason(candidates, issue, pick)
    return candidate


def has_conflicting_target_candidates(candidates: list[Candidate], issue: int) -> bool:
    return len({item.value for item in candidates if item.issue == issue}) > 1


def select_exact_candidate_with_reason(
    candidates: list[Candidate], issue: int
) -> tuple[Candidate | None, str | None]:
    if has_conflicting_target_candidates(candidates, issue):
        return None, "指定期数存在多条冲突数据"
    selected = [item for item in candidates if item.issue == issue]
    if not selected:
        return None, "未找到指定期数"
    return min(selected, key=lambda item: item.order), None


def select_candidate_in_region_limit(
    candidates: list[Candidate], issue: int, pick: str, limit: int
) -> tuple[Candidate | None, str | None]:
    if has_conflicting_target_candidates(candidates, issue):
        return None, "指定期数存在多条冲突数据"
    scoped_candidates = candidates[:limit] if pick == "top" else candidates[-limit:]
    selected = [item for item in scoped_candidates if item.issue == issue]
    if not selected:
        all_selected = [item for item in candidates if item.issue == issue]
        if not all_selected:
            return None, "未找到指定期数"
        label = "顶部" if pick == "top" else "尾部"
        return None, f"指定期数不在{label}{limit}组范围"
    candidate = min(selected, key=lambda item: item.order) if pick == "top" else max(selected, key=lambda item: item.order)
    return candidate, None


def select_candidate_with_reason(
    candidates: list[Candidate], issue: int, pick: str
) -> tuple[Candidate | None, str | None]:
    if has_conflicting_target_candidates(candidates, issue):
        return None, "指定期数存在多条冲突数据"
    strict_window = len(candidates) > STRICT_WINDOW_THRESHOLD
    scoped_candidates = candidates
    if strict_window:
        scoped_candidates = (
            candidates[:STRICT_WINDOW_LIMIT] if pick == "top" else candidates[-STRICT_WINDOW_LIMIT:]
        )

    selected = [item for item in scoped_candidates if item.issue == issue]
    if not selected:
        all_selected = [item for item in candidates if item.issue == issue]
        if not all_selected:
            return None, "未找到指定期数"
        label = "顶部" if pick == "top" else "尾部"
        return None, f"指定期数不在{label}{STRICT_WINDOW_LIMIT}组范围"
    candidate = min(selected, key=lambda item: item.order) if pick == "top" else max(selected, key=lambda item: item.order)
    return candidate, None


def load_sites(path: Path) -> list[Site]:
    data = json.loads(path.read_text(encoding="utf-8"))
    sites: list[Site] = []
    for item in data:
        pick = str(item.get("pick", "top")).strip().lower()
        if pick in {"上", "顶部", "top"}:
            pick = "top"
        elif pick in {"下", "底部", "bottom"}:
            pick = "bottom"
        else:
            raise ValueError(f"未知位置: {pick}")
        keyword = str(item.get("keyword", "")).strip() or None
        sites.append(Site(str(item["name"]).strip(), str(item["url"]).strip(), pick, keyword))
    return sites


def format_success(results: list[SuccessResult]) -> str:
    lines = ["内容 名称"]
    lines.extend(f"{item.value} {item.name}" for item in results)
    lines.append("")
    lines.append("内容 次数 排名")
    counts = Counter(item.value for item in results)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    for rank, (value, count) in enumerate(ranked, start=1):
        lines.append(f"{value} {count} {rank}")
    return "\n".join(lines) + "\n"


def parse_success_results(text: str) -> list[SuccessResult]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "内容 名称":
        raise ValueError("成功TXT格式无效: 缺少明细标题")
    try:
        detail_end = next(index for index, line in enumerate(lines[1:], start=1) if not line.strip())
    except StopIteration as exc:
        raise ValueError("成功TXT格式无效: 缺少明细边界") from exc
    if detail_end + 1 >= len(lines) or lines[detail_end + 1].strip() != "内容 次数 排名":
        raise ValueError("成功TXT格式无效: 缺少排名标题")

    results: list[SuccessResult] = []
    for line in lines[1:detail_end]:
        match = re.fullmatch(r"(红波|蓝波|绿波)\s+(.+)", line.strip())
        if not match or not match.group(2).strip():
            raise ValueError(f"成功TXT格式无效: 无法解析明细行: {line}")
        results.append(SuccessResult(match.group(2).strip(), match.group(1)))
    return results


def merge_success_results(
    existing: list[SuccessResult], current: list[SuccessResult]
) -> list[SuccessResult]:
    merged = list(existing)
    known_names = {item.name for item in existing}
    for item in current:
        if item.name in known_names:
            continue
        merged.append(item)
        known_names.add(item.name)
    return merged


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def write_success_results(path: Path, current: list[SuccessResult]) -> list[SuccessResult]:
    existing = parse_success_results(path.read_text(encoding="utf-8")) if path.exists() else []
    merged = merge_success_results(existing, current)
    if not path.exists() or len(merged) != len(existing):
        atomic_write_text(path, format_success(merged))
    return merged


def site_cache_key(site: Site, name_counts: Counter[str]) -> str:
    return site.name if name_counts[site.name] == 1 else f"{site.name}｜{site.url}"


def merge_cached_site_entry(old_sites: dict, site: Site, cache_key: str) -> dict:
    matching_entries = [
        entry
        for old_key, entry in old_sites.items()
        if isinstance(entry, dict)
        and entry.get("url") == site.url
        and (
            old_key == site.name
            or old_key.startswith(f"{site.name}｜")
            or entry.get("name") == site.name
        )
    ]
    exact_entry = old_sites.get(cache_key)
    if not isinstance(exact_entry, dict):
        exact_entry = {}
    merged_data: dict[str, str] = {}
    for matching_entry in matching_entries:
        merged_data.update(matching_entry.get("data", {}))
    merged_data.update(exact_entry.get("data", {}))
    if not matching_entries and not exact_entry:
        return {}
    merged_entry = {**exact_entry, "name": site.name, "url": site.url, "pick": site.pick, "data": merged_data}
    if site.keyword:
        merged_entry["keyword"] = site.keyword
    else:
        merged_entry.pop("keyword", None)
    return merged_entry


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def update_recent_cache(
    cache_file: Path,
    period: int,
    sites: list[Site],
    results: list[SuccessResult],
    keep: int = 10,
) -> None:
    if not results and not cache_file.exists():
        return
    if cache_file.exists():
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        data = {"periods": [], "sites": {}}

    old_sites = data.get("sites", {})
    name_counts = Counter(site.name for site in sites)
    sites_data: dict[str, dict] = {}
    sites_by_identity: dict[tuple[str, str], Site] = {}
    sites_by_name: dict[str, list[Site]] = {}
    for site in sites:
        cache_key = site_cache_key(site, name_counts)
        old_entry = merge_cached_site_entry(old_sites, site, cache_key)
        entry = {**old_entry, "name": site.name, "url": site.url, "pick": site.pick}
        entry["data"] = dict(old_entry.get("data", {}))
        if site.keyword:
            entry["keyword"] = site.keyword
        else:
            entry.pop("keyword", None)
        sites_data[cache_key] = entry
        sites_by_identity[(site.name, site.url)] = site
        sites_by_name.setdefault(site.name, []).append(site)

    for result in results:
        site = sites_by_identity.get((result.name, result.url)) if result.url else None
        if site is None and len(sites_by_name.get(result.name, [])) == 1:
            site = sites_by_name[result.name][0]
        if site is None:
            continue
        entry = sites_data[site_cache_key(site, name_counts)]
        values = entry.setdefault("data", {})
        values[str(period)] = result.value

    periods = sorted(
        {
            int(item)
            for entry in sites_data.values()
            for item in entry.get("data", {})
            if str(item).isdigit()
        },
        reverse=True,
    )[:keep]
    keep_keys = {str(item) for item in periods}

    for entry in sites_data.values():
        values = entry.get("data", {})
        for key in list(values.keys()):
            if key not in keep_keys:
                del values[key]

    data = {
        **data,
        "periods": periods,
        "sites": sites_data,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    atomic_write_json(cache_file, data)


def build_site_history(candidates: list[Candidate], pick: str, keep: int = 10) -> dict[int, str]:
    conflicting_issues = sorted(
        issue
        for issue in {item.issue for item in candidates if 100 <= item.issue <= 999}
        if has_conflicting_target_candidates(candidates, issue)
    )
    if conflicting_issues:
        raise ValueError(f"{','.join(map(str, conflicting_issues))}期存在波色冲突")
    history: dict[int, str] = {}
    ordered = candidates if pick == "top" else list(reversed(candidates))
    for item in ordered:
        if not (100 <= item.issue <= 999):
            continue
        if item.issue not in history:
            history[item.issue] = item.value
        if len(history) >= keep:
            break
    return history


def uses_reference_navigation(site: Site) -> bool:
    return bool(site.keyword and "qvuuqqs." in site.url and ("#/users/" in site.url or "#/forums/" in site.url))


def is_qvuuqs_dynamic_site(site: Site) -> bool:
    return is_qvuuqs_host(site.url) and "#/" in site.url


def collect_documents_for_site(site: Site, period: int | None = None) -> list[str]:
    try:
        if site.name == SHENGGONG_ZHIGUO_NAME:
            return collect_shenggong_documents(site)
        if site.name == ZHUNSHA_YIBO_NAME:
            return collect_zhunsha_documents(site)
        if site.name == "巴扎嘿":
            return collect_bazahei_documents(site.url, period)
        if site.name == "龙啸九天":
            return collect_longxiao_jiutian_documents(site.url, period)
        if site.name == "瞬杀一波":
            return collect_rendered_documents(urljoin(site.url, "/main/bbs/070.html"))
        if site.name == "六玄网":
            return collect_liuxuanwang_documents(site.url)
        if site.name in RENDERED_PRIMARY_SITE_NAMES:
            return collect_rendered_documents(site.url)
        if site.name == ANJU_ZILIAOYUAN_NAME:
            return collect_anju_ziliaoyuan_documents(site.url, period)
        if site.name == "柔情杀手":
            return collect_rourqing_shashou_documents(site, period)
        if site.name in IFRAME_TOPIC_SITE_NAMES:
            return collect_iframe_topic_documents(site, period)
        if is_qvuuqs_dynamic_site(site):
            user_id, record_id = extract_qvuuqs_route(site.url)
            if record_id is not None:
                return collect_reference_post_documents(site.url, site.keyword or "", issue=period)
            if user_id is not None:
                return collect_qvuuqs_user_documents(site, period)
            raise ValueError("qvuuqs动态URL无法提取用户或文章记录ID")
        if uses_reference_navigation(site):
            return collect_reference_post_documents(site.url, site.keyword or "", issue=period)
        if "#/users/" in site.url or "#/forums/" in site.url:
            raise ValueError("未登记动态用户页专属解析")
        return collect_documents(site.url)
    except Exception:
        if site.name in {SHENGGONG_ZHIGUO_NAME, ZHUNSHA_YIBO_NAME}:
            raise
        if site.name == "巴扎嘿":
            raise
        if site.name == "龙啸九天":
            raise
        if site.name == ANJU_ZILIAOYUAN_NAME:
            raise
        if site.name == "柔情杀手":
            raise
        if site.name in IFRAME_TOPIC_SITE_NAMES:
            raise
        if is_qvuuqs_dynamic_site(site):
            raise
        if uses_reference_navigation(site):
            return collect_reference_post_documents(site.url, site.keyword or "", issue=period)
        if "#/users/" in site.url or "#/forums/" in site.url:
            raise ValueError("未登记动态用户页专属解析")
        return collect_rendered_documents(site.url)


def collect_site_history(site: Site, keep: int = 10) -> dict[int, str]:
    documents = collect_documents_for_site(site)
    primary_candidates = extract_primary_candidates(documents, site)
    if not primary_candidates:
        documents = collect_documents_for_site(site)
        primary_candidates = extract_primary_candidates(documents, site)
    # 重建缓存没有单一目标期：先按接缝截断保留今年段，再交统一校验
    primary_candidates = _keep_first_descending_run(primary_candidates)
    return build_site_history(primary_candidates, site.pick, keep)


def collect_site_history_with_timeout(site: Site, keep: int = 10, timeout: int = 90) -> dict[int, str]:
    payload = json.dumps(
        {"name": site.name, "url": site.url, "pick": site.pick, "keyword": site.keyword, "keep": keep},
        ensure_ascii=False,
    )
    code = r'''
import json
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
item = json.loads(sys.argv[1])
import sha_yibo_crawler as crawler
site = crawler.Site(item["name"], item["url"], item.get("pick", "top"), item.get("keyword") or None)
history = crawler.collect_site_history(site, int(item.get("keep", 10)))
print(json.dumps(history, ensure_ascii=False))
'''
    try:
        completed = subprocess.run(
            [sys.executable, "-c", code, payload],
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"单站超时 {timeout}s") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"returncode {completed.returncode}")
    raw = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else "{}"
    return {int(period): value for period, value in json.loads(raw).items()}


def rebuild_recent_cache(
    cache_file: Path,
    sites: list[Site],
    keep: int = 10,
    workers: int = 8,
    progress: bool = False,
    force: bool = False,
    site_timeout: int = 0,
    fill_incomplete: bool = False,
) -> tuple[dict, list[str]]:
    old_cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    old_sites = old_cache.get("sites", {})
    cache = {"updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "periods": [], "sites": {}}
    failures: list[str] = []
    all_periods: set[int] = set()
    name_counts = Counter(site.name for site in sites)
    pending_sites: list[tuple[str, Site]] = []
    for site in sites:
        cache_key = site_cache_key(site, name_counts)
        old_entry = merge_cached_site_entry(old_sites, site, cache_key)
        old_data = old_entry.get("data", {}) if isinstance(old_entry, dict) else {}
        if not force and old_entry and (not fill_incomplete or len(old_data) >= keep):
            cache["sites"][cache_key] = old_entry
            all_periods.update(int(period) for period in old_data.keys() if str(period).isdigit())
            if progress:
                print(f"[缓存] {site.name} SKIP {len(old_data)}期", flush=True)
        elif not force and old_sites and not fill_incomplete:
            cache["sites"][cache_key] = {"name": site.name, "url": site.url, "pick": site.pick, "data": {}}
            if site.keyword:
                cache["sites"][cache_key]["keyword"] = site.keyword
            if progress:
                print(f"[缓存] {site.name} SKIP 0期", flush=True)
        else:
            pending_sites.append((cache_key, site))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        collector = collect_site_history_with_timeout if site_timeout else collect_site_history
        futures = {
            executor.submit(collector, site, keep, site_timeout) if site_timeout else executor.submit(collector, site, keep): (cache_key, site)
            for cache_key, site in pending_sites
        }
        for done, future in enumerate(as_completed(futures), start=1):
            cache_key, site = futures[future]
            try:
                history = future.result()
            except Exception as exc:
                old_entry = merge_cached_site_entry(old_sites, site, cache_key)
                old_data = old_entry.get("data", {})
                if old_entry:
                    cache["sites"][cache_key] = old_entry
                    all_periods.update(int(period) for period in old_data.keys() if str(period).isdigit())
                else:
                    cache["sites"][cache_key] = {"name": site.name, "url": site.url, "pick": site.pick, "data": {}}
                reason = format_exception_reason("抓取失败", exc)
                failures.append(format_site_failure(site, reason))
                if progress:
                    kept = f" 保留旧缓存{len(old_data)}期" if old_entry else ""
                    print(f"[{done}/{len(pending_sites)}] {site.name} 失败原因: {reason}{kept}", flush=True)
                continue
            if not history:
                old_entry = merge_cached_site_entry(old_sites, site, cache_key)
                old_data = old_entry.get("data", {})
                if old_entry and old_data:
                    cache["sites"][cache_key] = old_entry
                    all_periods.update(int(period) for period in old_data.keys() if str(period).isdigit())
                    if progress:
                        print(f"[{done}/{len(pending_sites)}] {site.name} 空结果 保留旧缓存{len(old_data)}期", flush=True)
                    continue
                if not old_entry:
                    cache["sites"][cache_key] = {"name": site.name, "url": site.url, "pick": site.pick, "data": {}}
                    if progress:
                        print(f"[{done}/{len(pending_sites)}] {site.name} 空结果 保留空站点", flush=True)
                    continue
            entry = {"name": site.name, "url": site.url, "pick": site.pick, "data": {str(k): v for k, v in history.items()}}
            if site.keyword:
                entry["keyword"] = site.keyword
            cache["sites"][cache_key] = entry
            all_periods.update(history.keys())
            if progress:
                print(f"[{done}/{len(pending_sites)}] {site.name} OK {len(history)}期", flush=True)

    cache["periods"] = sorted(all_periods, reverse=True)[:keep]
    if fill_incomplete:
        for key, entry in cache["sites"].items():
            if entry["data"]:
                continue
            site = Site(
                str(entry.get("name", key)),
                str(entry["url"]),
                str(entry.get("pick", "top")),
                str(entry.get("keyword", "")).strip() or None,
            )
            for period in cache["periods"]:
                result, _ = crawl_site(site, period)
                if result is not None:
                    entry["data"][str(period)] = result.value
            if progress and entry["data"]:
                print(f"[补齐] {site.name} OK {len(entry['data'])}期", flush=True)
    atomic_write_json(cache_file, cache)
    return cache, failures


def crawl_site(site: Site, period: int) -> tuple[SuccessResult | None, str | None]:
    try:
        documents = collect_documents_for_site(site, period)
        strict_region = is_strict_region(site)
        primary_candidates = extract_primary_candidates(documents, site)
        # 先判绕回（需要看到接缝），再截断，顺序不可颠倒
        primary_candidates, wrapped_reason = _reject_if_wrapped_before_target(primary_candidates, period)
        primary_candidates = _keep_first_descending_run(primary_candidates)
        candidates = primary_candidates
        missing_reason = missing_primary_reason(site) if not primary_candidates else None
        if site.name in QVUUQS_USER_RECORD_WINDOW_NAMES:
            candidate, reason = select_exact_candidate_with_reason(candidates, period)
        elif strict_region:
            candidate, reason = select_candidate_in_region_limit(candidates, period, site.pick, 3)
        else:
            candidate, reason = select_candidate_with_reason(candidates, period, site.pick)
        reason = wrapped_reason or missing_reason or reason
        primary_wrapped = wrapped_reason == "列表已绕回，疑似旧年数据"
        if (
            candidate is None
            and not primary_wrapped
            and site.name != ANJU_ZILIAOYUAN_NAME
            and site.name != SHENGGONG_ZHIGUO_NAME
            and site.name != ZHUNSHA_YIBO_NAME
            and site.name != "柔情杀手"
            and not is_qvuuqs_dynamic_site(site)
            and "#/users/" not in site.url
            and "#/forums/" not in site.url
        ):
            try:
                fallback_documents = (
                    collect_reference_post_documents(site.url, site.keyword or "", issue=period)
                    if uses_reference_navigation(site)
                    else collect_rendered_documents(site.url)
                )
                fallback_candidates = extract_primary_candidates(fallback_documents, site)
                fallback_candidates, fallback_wrapped_reason = _reject_if_wrapped_before_target(
                    fallback_candidates, period
                )
                fallback_candidates = _keep_first_descending_run(fallback_candidates)
                candidates = fallback_candidates
                fallback_missing_reason = missing_primary_reason(site) if not fallback_candidates else None
                if strict_region:
                    candidate, fallback_reason = select_candidate_in_region_limit(candidates, period, site.pick, 3)
                else:
                    candidate, fallback_reason = select_candidate_with_reason(candidates, period, site.pick)
                fallback_reason = fallback_wrapped_reason or fallback_missing_reason or fallback_reason
                if candidate is None and fallback_reason:
                    # 绕回判定是硬结论，不能被兜底的「未找到指定期数」覆盖
                    if reason != "列表已绕回，疑似旧年数据":
                        if not (reason and fallback_reason == missing_primary_reason(site)):
                            reason = fallback_reason
            except Exception:
                pass
        if candidate is None:
            return None, format_site_failure(site, reason or missing_primary_reason(site))
        return SuccessResult(site.name, candidate.value), None
    except Exception as exc:
        return None, format_site_failure(site, format_exception_reason("抓取失败", exc))


def print_progress(done: int, total: int, success_count: int, fail_count: int, elapsed: float, site: Site) -> None:
    percent = int(done * 100 / total) if total else 100
    print(
        f"[进度 {done}/{total} {percent}% 成功 {success_count} 失败 {fail_count} 用时 {elapsed:.1f}s] 当前: {site.name}",
        flush=True,
    )


def run(
    period: int,
    sites_file: Path,
    output_dir: Path,
    workers: int = 8,
    progress: bool = False,
    update_cache: bool = True,
    failure_output_dir: Path | None = None,
) -> tuple[list[str], list[str]]:
    sites = load_sites(sites_file)
    ordered_results: list[SuccessResult | None] = [None] * len(sites)
    ordered_failures: list[str | None] = [None] * len(sites)
    start_time = time.monotonic()
    success_count = 0
    fail_count = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(crawl_site, site, period): (index, site) for index, site in enumerate(sites)}
        for done, future in enumerate(as_completed(futures), start=1):
            index, site = futures[future]
            result, error = future.result()
            if result is not None:
                ordered_results[index] = SuccessResult(result.name, result.value, site.url)
                success_count += 1
            if error is not None:
                ordered_failures[index] = error
                fail_count += 1
            if progress:
                print_progress(done, len(sites), success_count, fail_count, time.monotonic() - start_time, site)

    results = [item for item in ordered_results if item is not None]
    fail = [item for item in ordered_failures if item is not None]
    output_dir.mkdir(parents=True, exist_ok=True)
    failure_dir = failure_output_dir or output_dir
    success = [f"{item.value} {item.name}" for item in results]
    write_success_results(output_dir / f"{period}期-一波.txt", results)
    fail_file = failure_dir / f"{period}期-杀一波-失败.txt"
    if fail:
        failure_dir.mkdir(parents=True, exist_ok=True)
        fail_file.write_text("\n\n".join(fail) + "\n", encoding="utf-8")
    elif fail_file.exists():
        fail_file.unlink()
    if update_cache:
        update_recent_cache(DEFAULT_CACHE_FILE, period, sites, results)
    return success, fail


def main() -> int:
    setup_console_encoding()
    parser = argparse.ArgumentParser(description="抓取杀一波数据")
    parser.add_argument("--period", type=int, help="目标期数，例如 151")
    parser.add_argument("--sites", type=Path, default=SCRIPT_DIR / "sites.json")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--failure-output-dir", type=Path)
    parser.add_argument("--workers", type=int, default=8, help="并发抓取数量，默认 8")
    parser.add_argument("--rebuild-cache", action="store_true", help="全站重建最近10期缓存")
    parser.add_argument("--force-rebuild-cache", action="store_true", help="忽略已有完整缓存，强制重抓")
    parser.add_argument("--fill-incomplete-cache", action="store_true", help="尝试补齐不足10期的旧缓存")
    parser.add_argument("--site-timeout", type=int, default=90, help="重建缓存时单站硬超时秒数，默认90")
    parser.add_argument("--no-cache-update", action="store_true", help="本次抓取不更新 recent_10_cache.json")
    args = parser.parse_args()

    if args.rebuild_cache:
        sites = load_sites(args.sites)
        cache, failures = rebuild_recent_cache(
            DEFAULT_CACHE_FILE,
            sites,
            workers=args.workers,
            progress=True,
            force=args.force_rebuild_cache,
            site_timeout=args.site_timeout,
            fill_incomplete=args.fill_incomplete_cache,
        )
        print(f"缓存完成：站点 {len(cache['sites'])} 个，期数 {len(cache['periods'])} 个，失败 {len(failures)} 个")
        for line in failures:
            print(line)
        return 0 if cache["sites"] else 1

    if args.period is None:
        parser.error("--period 或 --rebuild-cache 必须指定一个")

    failure_output_dir = args.failure_output_dir
    if failure_output_dir is None:
        failure_output_dir = DEFAULT_FAILURE_OUTPUT_DIR if args.output_dir == DEFAULT_OUTPUT_DIR else args.output_dir

    success, fail = run(
        args.period,
        args.sites,
        args.output_dir,
        args.workers,
        progress=True,
        update_cache=not args.no_cache_update,
        failure_output_dir=failure_output_dir,
    )
    print(f"完成：成功 {len(success)} 条，失败 {len(fail)} 条")
    for line in success:
        print(line)
    for line in fail:
        print(line)
    return 0 if success and not fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
































