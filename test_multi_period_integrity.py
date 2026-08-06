# -*- coding: utf-8 -*-
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import summarize_multi_period_failures as summary


class MultiPeriodIntegrityTest(unittest.TestCase):
    def test_periods_are_strictly_numeric_deduplicated_and_ordered(self):
        self.assertEqual([188, 187, 189], summary.normalize_periods(["188", "187", "188", "189"]))

        for value in ("187期", "abc187", "187-188", "18x7"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    summary.normalize_period(value)

    def test_missing_failure_report_means_zero_failures_when_success_report_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            self._write_success(output_dir, 187)

            rows = summary.collect_all_failed([187], output_dir)

        self.assertEqual([], rows)

    def test_missing_success_and_failure_reports_is_an_integrity_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)

            with self.assertRaises(summary.ReportIntegrityError) as caught:
                summary.collect_all_failed([187], output_dir)

        self.assertEqual([187], caught.exception.missing_periods)
        self.assertEqual([], caught.exception.invalid_periods)

    def test_failure_report_without_success_report_remains_parseable(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            self._write_failure(output_dir, 187, "甲站 https://example.test/a 失败原因: 超时\n")

            rows = summary.collect_all_failed([187], output_dir)

        self.assertEqual("甲站", rows[0]["name"])

    def test_collect_all_failed_reads_success_and_failure_directories_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            success_dir = Path(tmp) / "success"
            failure_dir = Path(tmp) / "failure"
            success_dir.mkdir()
            failure_dir.mkdir()
            self._write_success(success_dir, 187)
            self._write_failure(failure_dir, 187, "甲站 https://example.test/a 失败原因: 超时\n")

            rows = summary.collect_all_failed([187], success_dir, failure_dir)

        self.assertEqual("甲站", rows[0]["name"])

    def test_unreadable_failure_report_is_an_integrity_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            self._write_success(output_dir, 187)
            report = self._write_failure(output_dir, 187, "甲站 https://example.test/a 失败原因: 超时\n")
            original_read_text = Path.read_text

            def fail_target(path, *args, **kwargs):
                if path == report:
                    raise PermissionError("拒绝访问")
                return original_read_text(path, *args, **kwargs)

            with patch.object(Path, "read_text", fail_target):
                with self.assertRaises(summary.ReportIntegrityError) as caught:
                    summary.collect_all_failed([187], output_dir)

        self.assertEqual([], caught.exception.missing_periods)
        self.assertEqual([187], caught.exception.invalid_periods)

    def test_malformed_failure_report_is_an_integrity_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            self._write_success(output_dir, 187)
            self._write_failure(output_dir, 187, "这不是有效的失败报告行\n")

            with self.assertRaises(summary.ReportIntegrityError) as caught:
                summary.collect_all_failed([187], output_dir)

        self.assertEqual([187], caught.exception.invalid_periods)

    def test_empty_failure_report_is_valid_and_means_no_site_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            self._write_success(output_dir, 187)
            self._write_failure(output_dir, 187, "")

            rows = summary.collect_all_failed([187], output_dir)

        self.assertEqual([], rows)

    def test_main_returns_nonzero_and_does_not_write_summary_for_bad_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            stdout = io.StringIO()

            with patch("sys.stdout", stdout):
                exit_code = summary.main(["187", "188", "--output-dir", str(output_dir)])

            expected_summary = output_dir / "187-188期-杀一波-多期全部失败汇总.txt"
            summary_exists = expected_summary.exists()

        self.assertNotEqual(0, exit_code)
        self.assertIn("缺失期: 187, 188", stdout.getvalue())
        self.assertFalse(summary_exists)

    def test_main_lists_missing_and_invalid_periods_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            stdout = io.StringIO()
            self._write_success(output_dir, 187)
            self._write_failure(output_dir, 187, "格式异常\n")

            with patch("sys.stdout", stdout):
                exit_code = summary.main(["187", "188", "--output-dir", str(output_dir)])

        self.assertNotEqual(0, exit_code)
        self.assertIn("缺失期: 188", stdout.getvalue())
        self.assertIn("异常期: 187", stdout.getvalue())

    def test_main_rejects_non_numeric_period_input_before_writing_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            stdout = io.StringIO()

            with patch("sys.stdout", stdout):
                exit_code = summary.main(["abc187", "--output-dir", str(output_dir)])

            generated = list(output_dir.glob("*多期全部失败汇总.txt"))

        self.assertNotEqual(0, exit_code)
        self.assertIn("无效期数: abc187", stdout.getvalue())
        self.assertEqual([], generated)

    def test_duplicate_periods_do_not_change_summary_order_or_reasons(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            self._write_success(output_dir, 188)
            self._write_success(output_dir, 187)
            self._write_failure(output_dir, 188, "甲站 https://example.test/a 失败原因: 原因188\n")
            self._write_failure(output_dir, 187, "甲站 https://example.test/a 失败原因: 原因187\n")
            periods = summary.normalize_periods(["188", "187", "188"])

            rows = summary.collect_all_failed(periods, output_dir)
            path = summary.write_summary(periods, rows, output_dir)
            text = path.read_text(encoding="utf-8")

        self.assertEqual([188, 187], periods)
        self.assertEqual("188期_187期-杀一波-多期全部失败汇总.txt", path.name)
        self.assertLess(text.index("188期失败原因"), text.index("187期失败原因"))

    def test_batch_stops_before_summary_when_a_period_has_no_fresh_reports(self):
        batch_text = (Path(__file__).parent / "抓多期不刷新缓存.bat").read_text(encoding="utf-8")

        self.assertIn('set "BATCH_FAILED=0"', batch_text)
        self.assertIn('set "UNIQUE_PERIODS="', batch_text)
        self.assertIn('if not defined SEEN', batch_text)
        self.assertIn('set "CRAWL_EXIT=!ERRORLEVEL!"', batch_text)
        self.assertIn('if "!CRAWL_EXIT!"=="0"', batch_text)
        self.assertIn('if not exist "!SUCCESS_FILE!"', batch_text)
        self.assertIn('set "BATCH_FAILED=1"', batch_text)
        self.assertIn('if "!BATCH_FAILED!"=="1"', batch_text)
        self.assertLess(batch_text.index('if "!BATCH_FAILED!"=="1"'), batch_text.index("summarize_multi_period_failures.py"))
        self.assertLess(batch_text.index('del /q "!SUCCESS_FILE!"'), batch_text.index("sha_yibo_crawler.py"))
        self.assertLess(batch_text.index('del /q "!FAILURE_FILE!"'), batch_text.index("sha_yibo_crawler.py"))
        self.assertIn("Could not remove stale reports", batch_text)
        self.assertIn("--no-cache-update", batch_text)

    def test_batch_rejects_nonzero_crawl_without_failure_report(self):
        batch_text = (Path(__file__).parent / "抓多期不刷新缓存.bat").read_text(encoding="utf-8")

        self.assertIn('if not "!CRAWL_EXIT!"=="0" if not exist "!FAILURE_FILE!"', batch_text)
        self.assertIn("returned nonzero without a failure report", batch_text)

    @staticmethod
    def _write_failure(output_dir: Path, period: int, content: str) -> Path:
        path = output_dir / f"{period}期-杀一波-失败.txt"
        path.write_text(content, encoding="utf-8")
        return path

    @staticmethod
    def _write_success(output_dir: Path, period: int) -> Path:
        path = output_dir / f"{period}期-一波.txt"
        path.write_text("", encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
