# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import re
from pathlib import Path

from sha_yibo_crawler import DEFAULT_FAILURE_OUTPUT_DIR, DEFAULT_OUTPUT_DIR


FAILURE_RE = re.compile(r"^(?P<name>\S+)\s+(?P<url>\S+)\s+失败原因:\s*(?P<reason>.*)$")


class FailureReportFormatError(ValueError):
    pass


class ReportIntegrityError(RuntimeError):
    def __init__(self, missing_periods: list[int], invalid_reports: dict[int, str]):
        self.missing_periods = missing_periods
        self.invalid_periods = list(invalid_reports)
        parts = ["报告完整性检查未通过"]
        if missing_periods:
            parts.append("缺失期: " + ", ".join(str(period) for period in missing_periods))
        if invalid_reports:
            details = ", ".join(f"{period} ({reason})" for period, reason in invalid_reports.items())
            parts.append("异常期: " + details)
        super().__init__("；".join(parts))


def normalize_period(value: str) -> int:
    if not re.fullmatch(r"[0-9]+", value):
        raise ValueError(f"无效期数: {value}")
    return int(value)


def normalize_periods(values: list[str]) -> list[int]:
    return list(dict.fromkeys(normalize_period(value) for value in values))


def parse_failure_file(path: Path) -> dict[tuple[str, str], str]:
    failures: dict[tuple[str, str], str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        match = FAILURE_RE.match(line)
        if not match:
            raise FailureReportFormatError(f"第{line_number}行格式异常")
        name = match.group("name")
        url = match.group("url")
        reason = match.group("reason").strip() or "未知失败"
        failures[(name, url)] = reason
    return failures


def collect_all_failed(
    periods: list[int],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    failure_output_dir: Path | None = None,
) -> list[dict[str, object]]:
    failure_dir = failure_output_dir or output_dir
    period_failures: dict[int, dict[tuple[str, str], str]] = {}
    missing_periods: list[int] = []
    invalid_reports: dict[int, str] = {}
    for period in periods:
        success_path = output_dir / f"{period}期-一波.txt"
        failure_path = failure_dir / f"{period}期-杀一波-失败.txt"
        if not success_path.exists() and not failure_path.exists():
            missing_periods.append(period)
            continue
        if not failure_path.exists():
            period_failures[period] = {}
            continue
        try:
            period_failures[period] = parse_failure_file(failure_path)
        except (OSError, UnicodeError, FailureReportFormatError) as exc:
            invalid_reports[period] = str(exc)
    if missing_periods or invalid_reports:
        raise ReportIntegrityError(missing_periods, invalid_reports)
    if not period_failures:
        return []

    common_keys: set[tuple[str, str]] | None = None
    for failures in period_failures.values():
        keys = set(failures)
        common_keys = keys if common_keys is None else common_keys & keys

    rows: list[dict[str, object]] = []
    for name, url in sorted(common_keys or set()):
        rows.append(
            {
                "name": name,
                "url": url,
                "period_errors": {
                    period: period_failures[period][(name, url)]
                    for period in periods
                },
            }
        )
    return rows


def summary_path(periods: list[int], output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    first = periods[0]
    last = periods[-1]
    if len(periods) == 1:
        label = f"{first}期"
    elif periods == list(range(first, last + 1)):
        label = f"{first}-{last}期"
    else:
        label = "_".join(f"{period}期" for period in periods)
    return output_dir / f"{label}-杀一波-多期全部失败汇总.txt"


def write_summary(periods: list[int], rows: list[dict[str, object]], output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = summary_path(periods, output_dir)
    period_labels = " ".join(f"{period}期" for period in periods)
    lines = [
        f"{period_labels} 杀一波 多期全部失败汇总",
        "规则：任意一期成功则不列入；只有全部期数失败才列入。",
        "",
        f"全部失败目录数：{len(rows)}",
        "",
    ]
    if not rows:
        lines.append("无全部失败目录")
    for row in rows:
        lines.append(f"{row['name']} {row['url']}")
        errors = row["period_errors"]
        for period in periods:
            lines.append(f"  {period}期失败原因: {errors[period]}")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成杀一波多期全部失败汇总")
    parser.add_argument("periods", nargs="+", help="期数，例如 187 188 189 190")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--failure-output-dir", type=Path)
    args = parser.parse_args(argv)
    failure_output_dir = args.failure_output_dir
    if failure_output_dir is None:
        failure_output_dir = DEFAULT_FAILURE_OUTPUT_DIR if args.output_dir == DEFAULT_OUTPUT_DIR else args.output_dir

    try:
        periods = normalize_periods(args.periods)
        rows = collect_all_failed(periods, args.output_dir, failure_output_dir)
    except (ValueError, ReportIntegrityError) as exc:
        print(f"汇总失败: {exc}")
        return 1
    path = write_summary(periods, rows, failure_output_dir)
    print(f"多期全部失败汇总: {path}")
    print(f"全部失败目录数: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
