# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import sha_yibo_crawler as crawler

SCRIPT_DIR = Path(__file__).resolve().parent
PENDING_FILE = SCRIPT_DIR / "待检测站点.json"
CACHE_FILE = SCRIPT_DIR / "recent_10_cache.json"
SITES_FILE = SCRIPT_DIR / "sites.json"
REPORT_FILE = SCRIPT_DIR / "pending_cache_check.json"
DETECTOR_NAME = "check_pending_against_cache"
DUPLICATE_SOURCE = "recent_10_cache.json"
BLOCKED_LEGACY_DUPLICATE_DETECTORS = ["analyze_latest.py", "旧实时指纹脚本", "旧全站指纹/实时比对脚本"]
WIN = 10
SUSPECT_MATCH = 3
DUPLICATE_MATCH = 6
EXIT_BLOCKED = 1
EXIT_REJECTED = 2
EXIT_FAILURE = 4


def build_seq(pred: dict[int, str], win: int = WIN) -> list[tuple[int, str]]:
    return sorted(pred.items(), reverse=True)[:win]


def classify_pair_match(sa: list[tuple[int, str]], sb: list[tuple[int, str]]) -> dict:
    ma, mb = dict(sa), dict(sb)
    common = sorted(set(ma.keys()) & set(mb.keys()), reverse=True)
    best: list[tuple[int, str]] = []
    current: list[tuple[int, str]] = []
    previous = None
    for period in common:
        same = ma[period] == mb[period]
        consecutive = previous is None or previous - period == 1
        if same and consecutive:
            current.append((period, ma[period]))
        elif same:
            if len(current) > len(best):
                best = current
            current = [(period, ma[period])]
        else:
            if len(current) > len(best):
                best = current
            current = []
        previous = period
    if len(current) > len(best):
        best = current

    if len(best) >= DUPLICATE_MATCH:
        status = "duplicate"
    elif len(best) >= SUSPECT_MATCH:
        status = "suspect"
    else:
        status = "ignore"
    return {"status": status, "length": len(best), "periods": best}


def collect_site_pred(site: crawler.Site) -> dict[int, str]:
    documents = crawler.collect_documents_for_site(site)
    primary_candidates = crawler.extract_primary_candidates(documents, site)
    if not primary_candidates:
        raise ValueError(crawler.missing_primary_reason(site))

    ordered = primary_candidates if site.pick == "top" else list(reversed(primary_candidates))
    near_periods: list[int] = []
    for item in ordered:
        if 100 <= item.issue <= 999 and item.issue not in near_periods:
            near_periods.append(item.issue)
            if len(near_periods) == WIN:
                break

    values_by_period: dict[int, set[str]] = {}
    for item in primary_candidates:
        if item.issue in near_periods:
            values_by_period.setdefault(item.issue, set()).add(item.value)
    conflicts = sorted(period for period, values in values_by_period.items() if len(values) > 1)
    if conflicts:
        raise ValueError(f"{', '.join(str(period) for period in conflicts)}期波色冲突")

    pred: dict[int, str] = {}
    for item in ordered:
        if item.issue in near_periods and item.issue not in pred:
            pred[item.issue] = item.value
    return pred

def load_pending() -> list[crawler.Site]:
    return crawler.load_sites(PENDING_FILE)

def load_existing_sites() -> list[crawler.Site]:
    return crawler.load_sites(SITES_FILE)


def normalize_site_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    userinfo = ""
    if parsed.username is not None:
        userinfo = parsed.username
        if parsed.password is not None:
            userinfo += f":{parsed.password}"
        userinfo += "@"
    host = f"[{hostname}]" if ":" in hostname and not hostname.startswith("[") else hostname
    netloc = f"{userinfo}{host}"
    port = parsed.port
    if port is not None and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        netloc += f":{port}"
    path = parsed.path.rstrip("/")
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)), doseq=True)
    fragment = parsed.fragment.rstrip("/") if parsed.fragment.startswith(("/", "!/")) else ""
    return urlunsplit((scheme, netloc, path, query, fragment))


def find_same_name_rejection(site: crawler.Site, existing_sites: list[crawler.Site]) -> dict | None:
    existing_names = {item.name for item in existing_sites}
    if site.name not in existing_names:
        return None
    return {
        "name": site.name,
        "url": site.url,
        "status": "duplicate_name",
        "error": f"失败原因: 新增站点名称与已有站点同名，直接拒收: {site.name}",
    }


def find_existing_rejection(site: crawler.Site, existing_sites: list[crawler.Site]) -> dict | None:
    same_name = find_same_name_rejection(site, existing_sites)
    if same_name is not None:
        return same_name

    normalized = normalize_site_url(site.url)
    for existing in existing_sites:
        if normalized == normalize_site_url(existing.url):
            return {
                "name": site.name,
                "url": site.url,
                "status": "duplicate_url",
                "existing_site": existing.name,
                "existing_url": existing.url,
                "error": f"失败原因: 新增站点 URL/topic 与已有站点相同，直接拒收: {existing.name}",
            }
    return None


def latest_cache_periods(cache: dict, count: int = 2) -> list[int]:
    periods = {int(period) for period in cache.get("periods", [])}
    return sorted(periods, reverse=True)[:count]


def new_report(cache: dict) -> dict:
    return {
        "detector": DETECTOR_NAME,
        "duplicate_source": DUPLICATE_SOURCE,
        "source_policy": "cache_only",
        "legacy_duplicate_detectors_blocked": BLOCKED_LEGACY_DUPLICATE_DETECTORS,
        "periods": cache.get("periods", []),
        "checked": [],
        "blocked": [],
        "rejected": [],
        "failures": [],
        "field_check": {
            "status": "not_implemented",
            "reason": "当前 Site/缓存结构没有可可靠判定同字段的显式字段，需要新增明确字段后实现",
        },
    }


def main() -> int:
    crawler.setup_console_encoding()
    try:
        if not CACHE_FILE.exists():
            raise FileNotFoundError(f"缓存不存在: {CACHE_FILE}")
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        report = new_report({})
        report["failures"].append(
            {
                "name": DUPLICATE_SOURCE,
                "status": "failure",
                "error": f"失败原因: 缓存读取失败: {type(exc).__name__}: {crawler.compact_detail(exc)}",
            }
        )
        REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(report["failures"][0]["error"])
        print(f"JSON: {REPORT_FILE}")
        return EXIT_FAILURE

    pending = load_pending()
    existing_sites = load_existing_sites()
    cached_sites = cache.get("sites", {})

    report = new_report(cache)
    exit_code = 0
    required_periods = latest_cache_periods(cache)
    comparison_sites = list(existing_sites)
    for site in pending:
        rejection = find_existing_rejection(site, comparison_sites)
        if rejection is not None:
            report["rejected"].append(rejection)
            exit_code |= EXIT_REJECTED
            continue
        comparison_sites.append(site)
        try:
            pred = collect_site_pred(site)
            if not pred:
                raise ValueError("候选站抓取结果为空")
            if not required_periods:
                raise ValueError("recent_10_cache.json periods 为空，无法确定最新近2期")
            if not set(pred) & set(required_periods):
                raise ValueError(
                    f"候选站未抓到缓存最新近2期中的任意一期: {', '.join(map(str, required_periods))}"
                )
        except Exception as exc:
            detail = crawler.compact_detail(exc)
            report["failures"].append(
                {
                    "name": site.name,
                    "status": "failure",
                    "error": f"失败原因: 抓取待检测站点失败: {type(exc).__name__}: {detail}",
                }
            )
            exit_code |= EXIT_FAILURE
            continue

        target_seq = build_seq(pred)
        matches = []
        for cached_name, cached in cached_sites.items():
            cached_pred = {int(period): value for period, value in cached.get("data", {}).items()}
            cached_seq = build_seq(cached_pred)
            match = classify_pair_match(target_seq, cached_seq)
            if match["status"] != "ignore":
                matches.append(
                    {
                        "name": cached_name,
                        "status": match["status"],
                        "length": match["length"],
                        "periods": match["periods"],
                    }
                )

        matches.sort(key=lambda item: (0 if item["status"] == "duplicate" else 1, -item["length"], item["name"]))
        if any(item["status"] == "duplicate" for item in matches):
            status = "duplicate"
        elif any(item["status"] == "suspect" for item in matches):
            status = "suspect"
        else:
            status = "clean"
        result = {"name": site.name, "status": status, "seq": target_seq, "matches": matches}
        report["checked"].append(result)
        if status == "duplicate":
            report["rejected"].append(result)
            exit_code |= EXIT_REJECTED
        elif status == "suspect":
            report["blocked"].append(result)
            exit_code |= EXIT_BLOCKED

    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON: {REPORT_FILE}")
    for item in report["rejected"]:
        if item.get("status") in {"duplicate_name", "duplicate_url"}:
            print(f"{item['name']}: REJECTED {item.get('error', '')}")
    for item in report["checked"]:
        print(f"{item['name']}: {item['status']} ({len(item['matches'])} matches)")
    for item in report["failures"]:
        print(f"{item['name']}: FAIL {item['error']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())







