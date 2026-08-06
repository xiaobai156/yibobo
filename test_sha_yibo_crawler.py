# -*- coding: utf-8 -*-
import io
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import sha_yibo_crawler as crawler
import summarize_multi_period_failures as multi_summary


class ShaYiBoCrawlerTest(unittest.TestCase):
    def test_print_progress_uses_summary_style(self):
        output = io.StringIO()

        with patch("sys.stdout", output):
            crawler.print_progress(2, 120, 2, 0, 17.123, crawler.Site("亡魂丧魄", "https://example.test/", "top"))

        self.assertEqual("[进度 2/120 1% 成功 2 失败 0 用时 17.1s] 当前: 亡魂丧魄\n", output.getvalue())

    def test_run_can_skip_recent_cache_update(self):
        site = crawler.Site("甲站", "https://example.test/a", "top")
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            with patch.object(crawler, "load_sites", return_value=[site]):
                with patch.object(crawler, "crawl_site", return_value=(crawler.SuccessResult("甲站", "红波"), None)):
                    with patch.object(crawler, "update_recent_cache") as cache_updater:
                        success, fail = crawler.run(
                            190,
                            Path(tmp) / "sites.json",
                            output_dir,
                            workers=1,
                            update_cache=False,
                        )

        self.assertEqual(["红波 甲站"], success)
        self.assertEqual([], fail)
        cache_updater.assert_not_called()

    def test_run_updates_recent_cache_by_default(self):
        site = crawler.Site("甲站", "https://example.test/a", "top")
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            with patch.object(crawler, "load_sites", return_value=[site]):
                with patch.object(crawler, "crawl_site", return_value=(crawler.SuccessResult("甲站", "红波"), None)):
                    with patch.object(crawler, "update_recent_cache") as cache_updater:
                        crawler.run(190, Path(tmp) / "sites.json", output_dir, workers=1)

        cache_updater.assert_called_once()

    def test_run_separates_failure_sites_with_one_blank_line(self):
        sites = [
            crawler.Site("甲站", "https://example.test/a", "top"),
            crawler.Site("乙站", "https://example.test/b", "bottom"),
        ]

        def fail_site(site, _period):
            return None, f"{site.name} 失败原因: 测试失败"

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            with patch.object(crawler, "load_sites", return_value=sites):
                with patch.object(crawler, "crawl_site", side_effect=fail_site):
                    crawler.run(190, Path(tmp) / "sites.json", output_dir, workers=2, update_cache=False)
            failure_text = (output_dir / "190期-杀一波-失败.txt").read_text(encoding="utf-8")

        self.assertEqual(
            "甲站 失败原因: 测试失败\n\n乙站 失败原因: 测试失败\n",
            failure_text,
        )

    def test_run_writes_failure_report_to_distinct_directory(self):
        site = crawler.Site("甲站", "https://example.test/a", "top")
        with tempfile.TemporaryDirectory() as tmp:
            success_dir = Path(tmp) / "success"
            failure_dir = Path(tmp) / "failure"
            with patch.object(crawler, "load_sites", return_value=[site]):
                with patch.object(crawler, "crawl_site", return_value=(None, "甲站 失败原因: 测试失败")):
                    crawler.run(
                        190,
                        Path(tmp) / "sites.json",
                        success_dir,
                        workers=1,
                        update_cache=False,
                        failure_output_dir=failure_dir,
                    )

            self.assertTrue((failure_dir / "190期-杀一波-失败.txt").exists())
            self.assertFalse((success_dir / "190期-杀一波-失败.txt").exists())
            self.assertTrue((success_dir / "190期-一波.txt").exists())

    def test_multi_period_summary_only_lists_sites_failed_in_all_periods(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            (output_dir / "187期-杀一波-失败.txt").write_text(
                "甲站 https://example.test/a 失败原因: 未找到指定期数\n"
                "乙站 https://example.test/b 失败原因: SSL失败\n",
                encoding="utf-8",
            )
            (output_dir / "188期-杀一波-失败.txt").write_text(
                "甲站 https://example.test/a 失败原因: 指定期数存在多条冲突数据\n",
                encoding="utf-8",
            )

            rows = multi_summary.collect_all_failed([187, 188], output_dir)
            path = multi_summary.write_summary([187, 188], rows, output_dir)
            text = path.read_text(encoding="utf-8")

        self.assertEqual(1, len(rows))
        self.assertEqual("甲站", rows[0]["name"])
        self.assertIn("187期失败原因: 未找到指定期数", text)
        self.assertIn("188期失败原因: 指定期数存在多条冲突数据", text)
        self.assertNotIn("乙站", text)

    def test_loads_reference_keyword_from_site_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sites.json"
            path.write_text(
                '[{"name":"珠光宝气","url":"https://example.test/#/users/1/references/2","pick":"top","keyword":"双波中特"}]',
                encoding="utf-8",
            )

            sites = crawler.load_sites(path)

        self.assertEqual("双波中特", sites[0].keyword)

    def test_reference_post_match_requires_today_or_issue_and_keyword(self):
        self.assertTrue(crawler.reference_post_matches("资料员\n2026-06-04 13:07:23\n155期 双波中特", "2026-06-04", "双波中特"))
        self.assertTrue(crawler.reference_post_matches("资料员\n2026-06-03 13:07:23\n155期 双波中特", "2026-06-04", "双波中特", 155))
        self.assertFalse(crawler.reference_post_matches("资料员\n2026-06-03 13:07:23\n155期 双波中特", "2026-06-04", "双波中特"))
        self.assertFalse(crawler.reference_post_matches("资料员\n2026-06-04 13:07:23\n155期 一肖中特", "2026-06-04", "双波中特"))
        self.assertFalse(crawler.reference_post_matches("资料员\n2026-06-03 13:07:23\n154期 双波中特", "2026-06-04", "双波中特", 155))

    def test_qvuuqs_route_extracts_user_and_record_ids(self):
        self.assertEqual(
            (11978, 15342952),
            crawler.extract_qvuuqs_route(
                "https://qvuuqqs.example/#/users/11978/references/15342952"
            ),
        )
        self.assertEqual(
            (None, 15337561),
            crawler.extract_qvuuqs_route("https://qvuuqs.example/#/forums/15337561"),
        )
        self.assertEqual(
            (1504, None),
            crawler.extract_qvuuqs_route("https://qvuuqs.example/#/users/1504"),
        )

    def test_qvuuqs_reference_record_requires_exact_id_and_fields(self):
        record = {
            "id": 15342952,
            "user_id": 11978,
            "topic": "珠光宝气",
            "sub_topic": "双波中特",
            "content": "153期双波中特【红波蓝波】",
            "user": {"id": 11978},
        }
        self.assertEqual(record, crawler.validate_qvuuqs_reference_record(record, 11978, 15342952, "双波中特"))
        with self.assertRaisesRegex(ValueError, "记录ID不匹配"):
            crawler.validate_qvuuqs_reference_record({**record, "id": 15342953}, 11978, 15342952, "双波中特")
        with self.assertRaisesRegex(ValueError, "栏目字段不匹配"):
            crawler.validate_qvuuqs_reference_record({**record, "sub_topic": "大小中特"}, 11978, 15342952, "双波中特")
        with self.assertRaisesRegex(ValueError, "作者用户ID缺失"):
            crawler.validate_qvuuqs_reference_record({**record, "user_id": None}, None, 15342952, "双波中特")
        with self.assertRaisesRegex(ValueError, "嵌套作者用户ID不匹配"):
            crawler.validate_qvuuqs_reference_record({**record, "user": {"id": 4615}}, None, 15342952, "双波中特")

    def test_qvuuqs_record_locator_uses_nested_unique_id(self):
        payload = {
            "data": {
                "items": [
                    {"id": 1, "title": "其他文章", "content": "190期绝杀一波【红波】"},
                    {
                        "id": "15342952",
                        "title": "珠光宝气",
                        "sub_topic": "双波中特",
                        "content": "200期双波中特【红波蓝波】",
                    },
                ]
            }
        }

        record, path = crawler.locate_qvuuqs_record(payload, 15342952)

        self.assertEqual(15342952, int(record["id"]))
        self.assertEqual("$.data.items[1]", path)

    def test_qvuuqs_record_locator_rejects_missing_or_duplicate_id(self):
        with self.assertRaisesRegex(ValueError, "未找到唯一目标记录ID"):
            crawler.locate_qvuuqs_record({"data": [{"id": 1, "content": "200期绝杀一波【红波】"}]}, 15342952)

        duplicate = {
            "items": [
                {"id": 15342952, "content": "200期双波中特【红波蓝波】"},
                {"id": "15342952", "content": "200期双波中特【蓝波绿波】"},
            ]
        }
        with self.assertRaisesRegex(ValueError, "找到多个同ID目标记录"):
            crawler.locate_qvuuqs_record(duplicate, 15342952)

    def test_qvuuqs_user_records_select_by_period_not_first_record(self):
        records = [
            {"id": 9002, "user_id": 1504, "draw": 200, "topic": "绝杀一波", "content": "200期绝杀一波【红波】"},
            {"id": 9001, "user_id": 1504, "draw": 199, "topic": "绝杀一波", "content": "199期绝杀一波【蓝波】"},
        ]
        selected = crawler.select_qvuuqs_user_records(records, 1504, "绝杀一波", 199)
        self.assertEqual([9001], [item["id"] for item in selected])

    def test_qvuuqs_user_record_draw_field_is_the_record_boundary(self):
        records = [
            {
                "id": 9002,
                "user_id": 1504,
                "draw": 200,
                "topic": "绝杀一波",
                "content": "200期绝杀一波【红波】\n199期绝杀一波【蓝波】",
            },
            {
                "id": 9001,
                "user_id": 1504,
                "draw": 199,
                "topic": "绝杀一波",
                "content": "199期绝杀一波【蓝波】\n198期绝杀一波【绿波】",
            },
        ]

        selected = crawler.select_qvuuqs_user_records(records, 1504, "绝杀一波", 199)

        self.assertEqual([9001], [item["id"] for item in selected])

    def test_qvuuqs_reference_double_wave_sites_use_line_anchored_parser(self):
        cases = [
            ("珠光宝气", "双波中特", "153期双波中特【绿波蓝波】开0000准", "红波"),
            ("攻克专家", "双波必中", "152期双波必中《红波绿波》开000准", "蓝波"),
        ]

        for name, keyword, document, expected in cases:
            site = crawler.Site(name, "https://qvuuqqs.example/#/users/1/references/2", "top", keyword)
            candidates = crawler.extract_primary_candidates([document], site)
            selected, reason = crawler.select_candidate_with_reason(candidates, int(document[:3]), "top")
            self.assertIsNone(reason)
            self.assertIsNotNone(selected)
            self.assertEqual(expected, selected.value)

    def test_qvuuqs_reference_selects_current_index_record_by_period_and_keyword(self):
        records = [
            {
                "id": 15342952,
                "user_id": 11978,
                "draw": 153,
                "topic": "珠光宝气",
                "sub_topic": "双波中特",
            },
            {
                "id": 15647904,
                "user_id": 11978,
                "draw": 201,
                "topic": "珠光宝气",
                "sub_topic": "双波中特",
            },
        ]

        selected = crawler.select_qvuuqs_index_records(records, 11978, "双波中特", 201)

        self.assertEqual([15647904], [item["id"] for item in selected])

    def test_qvuuqs_reference_rejects_record_period_or_body_conflict(self):
        valid = {
            "id": 15647904,
            "user_id": 11978,
            "draw": 201,
            "topic": "珠光宝气",
            "sub_topic": "双波中特",
            "content": "201期双波中特【红波蓝波】开0000准",
        }
        self.assertEqual(valid, crawler.validate_qvuuqs_target_record(valid, 201))

        with self.assertRaisesRegex(ValueError, "记录字段期数不匹配"):
            crawler.validate_qvuuqs_target_record({**valid, "draw": 153}, 201)
        with self.assertRaisesRegex(ValueError, "正文未找到指定期数"):
            crawler.validate_qvuuqs_target_record({**valid, "content": "200期双波中特【绿波蓝波】"}, 201)

    def test_qvuuqs_reference_route_uses_current_record_collector(self):
        site_url = "https://qvuuqqs.example/#/users/11978/references/15342952"
        with patch.object(crawler, "collect_qvuuqs_reference_documents", return_value=["201期双波中特【红波蓝波】"]):
            documents = crawler.collect_reference_post_documents(site_url, "双波中特", issue=201)

        self.assertEqual(["201期双波中特【红波蓝波】"], documents)

    def test_huaxin_jiaogai_uses_user_page_exact_parser(self):
        site = crawler.Site("花心膝盖", "https://qvuuqqs.example/#/users/18131", "top")
        documents = ["201期:【绝杀一波】【红波】开:00准"]

        candidates = crawler.extract_primary_candidates(documents, site)

        self.assertEqual([(201, "红波")], [(item.issue, item.value) for item in candidates])

    def test_qvuuqs_user_records_reject_duplicate_target_period(self):
        records = [
            {"id": 9001, "user_id": 1504, "draw": 199, "topic": "绝杀一波", "content": "199期绝杀一波【蓝波】"},
            {"id": 9002, "user_id": 1504, "draw": 199, "topic": "绝杀一波", "content": "199期绝杀一波【红波】"},
        ]
        with self.assertRaisesRegex(ValueError, "同一期匹配到多条用户文章"):
            crawler.select_qvuuqs_user_records(records, 1504, "绝杀一波", 199)

    def test_collect_documents_for_qvuuqs_user_uses_structured_user_collector(self):
        site = crawler.Site("拥挤门", "https://qvuuqqs.example/#/users/1504", "bottom", "绝杀一波")
        calls = []

        def fake_collector(received_site, period):
            calls.append((received_site, period))
            return ["199期绝杀一波【蓝波】"]

        with patch.object(crawler, "collect_qvuuqs_user_documents", fake_collector):
            self.assertEqual(["199期绝杀一波【蓝波】"], crawler.collect_documents_for_site(site, 199))
        self.assertEqual([(site, 199)], calls)

    def test_qvuuqs_dynamic_site_matches_real_host(self):
        site = crawler.Site("帅气成衣", "https://qvuuqqs.example/#/users/1572", "top", "绝杀一波")

        self.assertTrue(crawler.is_qvuuqs_dynamic_site(site))
        self.assertFalse(
            crawler.uses_reference_navigation(
                crawler.Site("普通站", "https://qvuuqqs.example/", "top", "绝杀一波")
            )
        )

    def test_madao_success_config_uses_source_column(self):
        site = next(item for item in crawler.load_sites(crawler.SCRIPT_DIR / "sites.json") if item.name == "马道成功")

        self.assertEqual("绝杀一波", site.keyword)

    def test_keyword_site_uses_static_documents_for_normal_url(self):
        site = crawler.Site("彩民书籍", "https://example.test/", "bottom", "彩民书籍")
        documents = ["彩民书籍\n159期:绝杀➡绿波【开:0000】✔"]

        with patch.object(crawler, "collect_documents", return_value=documents) as static_collector:
            with patch.object(crawler, "collect_reference_post_documents", side_effect=AssertionError("普通站不应走历史帖采集")):
                result, error = crawler.crawl_site(site, 159)

        static_collector.assert_called_once_with(site.url)
        self.assertIsNone(error)
        self.assertEqual(crawler.SuccessResult("彩民书籍", "绿波"), result)

    def test_hongjie_forum_config_uses_top_region(self):
        sites = crawler.load_sites(crawler.SCRIPT_DIR / "sites.json")
        site = next(item for item in sites if item.name == "红姐论坛")

        self.assertEqual("top", site.pick)

    def test_hongjie_forum_uses_exact_sha_yibo_candidates(self):
        site = crawler.Site("红姐论坛", "https://example.test/topic/466186.html", "top")
        documents = [
            "资料区 163期:【绝杀一波】 置之高阁\n"
            "163期:【精杀一波】【红波】开:0000准\n"
            "163期:【绝杀一波】【绿波】开:0000准\n"
            "162期:【绝杀一波】【红波】开:猪32准\n"
            "161期:【绝杀一波】【蓝波】开:猪08准"
        ]

        with patch.object(crawler, "collect_documents", return_value=documents):
            with patch.object(crawler, "collect_rendered_documents", return_value=documents):
                result, error = crawler.crawl_site(site, 163)

        self.assertIsNone(error)
        self.assertEqual(crawler.SuccessResult("红姐论坛", "绿波"), result)

    def test_guangdong_baer_config_uses_bottom_region(self):
        sites = crawler.load_sites(crawler.SCRIPT_DIR / "sites.json")
        site = next(item for item in sites if item.name == "广东八二站")

        self.assertEqual("bottom", site.pick)

    def test_guangdong_baer_uses_exact_sha_yibo_candidates(self):
        site = crawler.Site("广东八二站", "https://example.test/#am", "bottom")
        documents = [
            "广东八二站『绝杀一波』\n"
            "164期精杀一波【红波】开0000准\n"
            "159期绝杀一波【蓝波】开龙39准\n"
            "160期绝杀一波【绿波】开蛇02准\n"
            "162期绝杀一波【蓝波】开猪32准\n"
            "163期绝杀一波【红波】开马37准\n"
            "164期绝杀一波【蓝波】开0000准"
        ]

        with patch.object(crawler, "collect_documents", return_value=documents):
            with patch.object(crawler, "collect_rendered_documents", return_value=documents):
                result, error = crawler.crawl_site(site, 164)

        self.assertIsNone(error)
        self.assertEqual(crawler.SuccessResult("广东八二站", "蓝波"), result)

    def test_strict_region_history_uses_exact_sha_yibo_candidates(self):
        site = crawler.Site("广东八二站", "https://example.test/#am", "bottom")
        documents = [
            "广东八二站『绝杀一波』\n"
            "164期精杀一波【红波】开0000准\n"
            "163期绝杀一波【红波】开马37准\n"
            "164期绝杀一波【蓝波】开0000准"
        ]

        with patch.object(crawler, "collect_documents", return_value=documents):
            history = crawler.collect_site_history(site, keep=2)

        self.assertEqual({164: "蓝波", 163: "红波"}, history)

    def test_strict_region_history_does_not_fallback_to_generic_candidates(self):
        site = crawler.Site("广东八二站", "https://example.test/#am", "bottom")
        documents = ["164期精杀一波【红波】开0000准"]

        with patch.object(crawler, "collect_documents", return_value=documents):
            history = crawler.collect_site_history(site, keep=2)

        self.assertEqual({}, history)

    def test_crawl_site_does_not_fallback_to_generic_candidates(self):
        site = crawler.Site("甲站", "https://example.test/a", "top")
        documents = ["168期绝杀一波【红波】开0000准"]

        with patch.object(crawler, "collect_documents", return_value=documents):
            with patch.object(crawler, "collect_rendered_documents", return_value=documents):
                result, error = crawler.crawl_site(site, 168)

        self.assertIsNone(result)
        self.assertIn("未登记站点级专属解析", error)

    def test_history_does_not_fallback_to_generic_candidates(self):
        site = crawler.Site("甲站", "https://example.test/a", "top")
        documents = ["168期绝杀一波【红波】开0000准"]

        with patch.object(crawler, "collect_documents", return_value=documents):
            history = crawler.collect_site_history(site, keep=2)

        self.assertEqual({}, history)

    def test_zhuque_uses_composite_table_sha_yibo_column(self):
        site = crawler.Site("朱雀", "https://example.test/", "top")
        documents = [
            "177792a.com『综合绝杀』\n"
            "期数\n杀一肖\n杀一波\n杀一尾\n杀一头\n开奖结果\n"
            "171期\n(龙)\n(绿)\n(9)\n(3)\n开:發00准\n"
            "170期\n(马)\n(红)\n(1)\n(0)\n开:龙03准"
        ]

        with patch.object(crawler, "collect_documents", return_value=documents):
            result, error = crawler.crawl_site(site, 171)

        self.assertIsNone(error)
        self.assertEqual(crawler.SuccessResult("朱雀", "绿波"), result)

    def test_liubiao_uses_double_wave_section(self):
        site = crawler.Site("六表主", "https://example.test/", "top")
        documents = [
            "【六表主双波】√\n"
            "171期【蓝波绿波】\n"
            "170期【绿波红波】\n"
            "169期【红波蓝波】"
        ]

        with patch.object(crawler, "collect_documents", return_value=documents):
            result, error = crawler.crawl_site(site, 171)

        self.assertIsNone(error)
        self.assertEqual(crawler.SuccessResult("六表主", "红波"), result)

    def test_bazahei_uses_named_sha_yibo_section(self):
        documents = [
            "173期：【绝杀一波◇◇巴扎嘿】←※已更新\n"
            "173期：绝杀一波【绿波】开000准\n"
            "172期：绝杀一波【红波】开猪44准\n"
            "173期：【绝杀(1)行◇◇陌南尘】←※已更新\n"
            "173期：绝杀一波【蓝波】开000准"
        ]

        candidates = crawler.extract_bazahei_candidates(documents)

        self.assertEqual([(173, "绿波"), (172, "红波")], [(item.issue, item.value) for item in candidates])

    def test_bazahei_opens_issue_entry_from_home_page(self):
        site = crawler.Site("巴扎嘿", "https://example.test/", "top")
        home = ['<a href="/topic/new.html">176期：【绝杀一波◇◇巴扎嘿】←※已更新</a>']
        detail = [
            "176期：【绝杀一波◇◇巴扎嘿】←※已更新\n"
            "176期：绝杀一波【红波】开000准"
        ]

        with patch.object(crawler, "collect_documents", side_effect=[home, detail]) as collector:
            result, error = crawler.crawl_site(site, 176)

        self.assertIsNone(error)
        self.assertEqual(crawler.SuccessResult("巴扎嘿", "红波"), result)
        self.assertEqual("https://example.test/", collector.call_args_list[0].args[0])
        self.assertEqual("https://example.test/topic/new.html", collector.call_args_list[1].args[0])

    def test_bazahei_fails_when_home_page_lacks_target_issue_entry(self):
        site = crawler.Site("巴扎嘿", "https://example.test/", "top")
        home = ['<a href="/topic/old.html">175期：【绝杀一波◇◇巴扎嘿】←※已更新</a>']

        with patch.object(crawler, "collect_documents", return_value=home):
            result, error = crawler.crawl_site(site, 176)

        self.assertIsNone(result)
        self.assertIn("首页未找到指定期数的巴扎嘿目录入口: 176期", error)

    def test_bazahei_rejects_multiple_target_issue_entries(self):
        site = crawler.Site("巴扎嘿", "https://example.test/", "top")
        home = [
            '<a href="/topic/one.html">190期：【绝杀一波◇◇巴扎嘿】入口一</a>',
            '<a href="/topic/two.html">190期：【绝杀一波◇◇巴扎嘿】入口二</a>',
        ]

        with patch.object(crawler, "collect_documents", return_value=home):
            result, error = crawler.crawl_site(site, 190)

        self.assertIsNone(result)
        self.assertIn("目录页未唯一定位指定期数的巴扎嘿入口: 190期", error)

    def test_longxiao_jiutian_opens_issue_entry_from_index(self):
        site = crawler.Site("龙啸九天", "https://example.test/topic/257907.html", "top")
        home = [
            '<a href="/topic/wrong.html">190期：【孤巷的猫】☆绝杀半波☆实力见证！</a>'
            '<a href="/topic/right.html">190期：【龙啸九天】☆绝杀壹波☆实力见证！</a>'
        ]
        detail = [
            "190期：【龙啸九天】☆绝杀壹波☆实力见证！\n"
            "190期：≦(绝杀壹波)≧◆绿波◆开0000准\n"
            "189期：≦(绝杀壹波)≧◆红波◆开龙15准\n"
            "190期：【孤巷的猫】☆绝杀半波☆实力见证！"
        ]

        with patch.object(crawler, "collect_documents", side_effect=[home, detail]) as collector:
            result, error = crawler.crawl_site(site, 190)

        self.assertIsNone(error)
        self.assertEqual(crawler.SuccessResult("龙啸九天", "绿波"), result)
        self.assertEqual("https://example.test/topic/right.html", collector.call_args_list[1].args[0])

    def test_longxiao_jiutian_fails_when_index_lacks_target_issue_entry(self):
        site = crawler.Site("龙啸九天", "https://example.test/topic/257907.html", "top")
        home = ['<a href="/topic/old.html">189期：【龙啸九天】☆绝杀壹波☆实力见证！</a>']

        with patch.object(crawler, "collect_documents", return_value=home):
            result, error = crawler.crawl_site(site, 190)

        self.assertIsNone(result)
        self.assertIn("目录页未找到指定期数的龙啸九天入口: 190期", error)

    def test_longxiao_jiutian_parser_stops_before_next_title(self):
        site = crawler.Site("龙啸九天", "https://example.test/topic/257907.html", "top")
        documents = [
            "190期：【龙啸九天】☆绝杀壹波☆实力见证！\n"
            "190期：≦(绝杀壹波)≧◆绿波◆开0000准\n"
            "189期：≦(绝杀壹波)≧◆红波◆开龙15准\n"
            "190期：【孤巷的猫】☆绝杀半波☆实力见证！\n"
            "190期：≦(绝杀壹波)≧◆蓝波◆开0000准"
        ]

        candidates = crawler.extract_primary_candidates(documents, site)

        self.assertEqual([(190, "绿波"), (189, "红波")], [(item.issue, item.value) for item in candidates])

    def test_shiwai_taoyuan_uses_buy_two_wave_candidates(self):
        site = crawler.Site("世外桃源", "https://example.test/gsb/074.html", "bottom")
        documents = [
            "世外桃源【必买二波】\n"
            "164期:☘️必买二波☘️开:狗21准\n"
            "【绿 蓝】\n"
            "165期:☘️必买二波☘️开:龙03准\n"
            "【红 蓝】\n"
            "166期:☘️必买二波☘️开:00准\n"
            "【红 绿】"
        ]

        with patch.object(crawler, "collect_documents", return_value=documents):
            with patch.object(crawler, "collect_rendered_documents", return_value=documents):
                result, error = crawler.crawl_site(site, 166)

        self.assertIsNone(error)
        self.assertEqual(crawler.SuccessResult("世外桃源", "蓝波"), result)

    def test_shiwai_taoyuan_history_uses_buy_two_wave_candidates(self):
        site = crawler.Site("世外桃源", "https://example.test/gsb/074.html", "bottom")
        documents = [
            "164期:☘️必买二波☘️开:狗21准\n【绿 蓝】\n"
            "165期:☘️必买二波☘️开:龙03准\n【红 蓝】\n"
            "166期:☘️必买二波☘️开:00准\n【红 绿】"
        ]

        with patch.object(crawler, "collect_documents", return_value=documents):
            history = crawler.collect_site_history(site, keep=2)

        self.assertEqual({166: "蓝波", 165: "绿波"}, history)

    def test_rejects_top_candidate_when_target_issue_repeats(self):
        documents = [
            """
            <p>151期绝杀一波【红波】开鼠31准</p>
            <p>151期绝杀一波【绿波】开鼠31准</p>
            """
        ]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 151, "top")
        self.assertIsNone(picked)

    def test_rejects_bottom_candidate_when_target_issue_repeats(self):
        documents = [
            """
            <p>151期 独杀一波 : 【红波】开 00 准</p>
            <p>151期 独杀一波 : 【绿波】开鼠31准</p>
            """
        ]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 151, "bottom")
        self.assertIsNone(picked)

    def test_extracts_traditional_text(self):
        documents = ["<p>151期：絕殺一波 (藍波）開?00準</p>"]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 151, "top")
        self.assertIsNotNone(picked)
        self.assertEqual("蓝波", picked.value)

    def test_extracts_repeated_color_text(self):
        documents = ["151期:绝杀一波〔红红红〕开？00准"]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 151, "top")
        self.assertIsNotNone(picked)
        self.assertEqual("红波", picked.value)

    def test_extracts_sha_te_wave_text(self):
        documents = ["151期：精杀一波【杀特绿波】开？00准"]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 151, "bottom")
        self.assertIsNotNone(picked)
        self.assertEqual("绿波", picked.value)

    def test_extracts_kan_sha_wave_text(self):
        documents = ["151期砍杀一波：蓝波：0000准"]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 151, "top")
        self.assertIsNotNone(picked)
        self.assertEqual("蓝波", picked.value)

    def test_extracts_wen_sha_repeated_color_text(self):
        documents = ["151期稳杀【蓝蓝蓝】开？00√"]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 151, "top")
        self.assertIsNotNone(picked)
        self.assertEqual("蓝波", picked.value)

    def test_extracts_keyword_first_wave_text(self):
        documents = ["☯杀一波色☯151期【蓝波】开 ?? 准"]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 151, "top")
        self.assertIsNotNone(picked)
        self.assertEqual("蓝波", picked.value)

    def test_extracts_table_wave_text(self):
        documents = ["<h1>49玄机阁【综合绝杀】</h1><table><tr><th>杀一波</th></tr><tr><td>151期</td><td>鼠</td><td>7尾</td><td>红波</td><td>3头</td><td>0000</td></tr></table>"]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 151, "top")
        self.assertIsNotNone(picked)
        self.assertEqual("红波", picked.value)

    def test_extracts_single_color_table_wave_text(self):
        documents = ["<h1>177792a.com『综合绝杀』</h1><table><tr><th>期数</th><th>杀一肖</th><th>杀一波</th></tr><tr><td>152期</td><td>(狗)</td><td>(红)</td><td>(3)</td><td>开:發00准</td></tr></table>"]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 152, "top")
        self.assertIsNotNone(picked)
        self.assertEqual("红波", picked.value)

    def test_ignores_table_wave_outside_composite_section(self):
        documents = ["<h1>177792a.com『综合绝杀』</h1><table><tr><th>期数</th><th>杀一波</th></tr></table><h1>177792a.com『计算公式』</h1><table><tr><td>152期</td><td>狗</td><td>蓝波</td><td>0000</td></tr></table>"]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 152, "top")
        self.assertIsNone(picked)

    def test_extracts_formula_wave_text(self):
        documents = ["公式杀波\n第151期杀绿波√"]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 151, "bottom")
        self.assertIsNotNone(picked)
        self.assertEqual("绿波", picked.value)

    def test_converts_double_wave_to_missing_wave(self):
        documents = ["152期双波中特【红波蓝波】开狗45准"]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 152, "top")
        self.assertIsNotNone(picked)
        self.assertEqual("绿波", picked.value)

    def test_converts_double_wave_variants_to_missing_wave(self):
        documents = [
            "152期双波必中《红波绿波》开000准",
            "153期❦两波中特❦【绿波防蓝波】❦开:0000错",
            "154期 必中双波【蓝波绿波】开000准",
        ]
        matches = crawler.extract_candidates(documents)
        first = crawler.select_candidate(matches, 152, "top")
        second = crawler.select_candidate(matches, 153, "top")
        third = crawler.select_candidate(matches, 154, "top")
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertIsNotNone(third)
        self.assertEqual("蓝波", first.value)
        self.assertEqual("红波", second.value)
        self.assertEqual("红波", third.value)

    def test_converts_six_table_double_wave_to_missing_wave(self):
        documents = ["【六表主双波】√\n155期【绿波红波】\n154期【蓝波绿波】"]
        matches = crawler.extract_candidates(documents)

        picked = crawler.select_candidate(matches, 155, "top")

        self.assertIsNotNone(picked)
        self.assertEqual("蓝波", picked.value)

    def test_converts_bizhong_double_wave_table_rows_to_missing_wave(self):
        documents = ["必中双波\n155期【双波开】=【蓝波绿波】开0000准"]
        matches = crawler.extract_candidates(documents)

        picked = crawler.select_candidate(matches, 155, "top")

        self.assertIsNotNone(picked)
        self.assertEqual("红波", picked.value)

    def test_converts_dotted_double_wave_to_missing_wave(self):
        documents = ["155期:〔少女的梦〕 ♠️双波中特♠️【红.绿】开:00准"]
        matches = crawler.extract_candidates(documents)

        picked = crawler.select_candidate(matches, 155, "bottom")

        self.assertIsNotNone(picked)
        self.assertEqual("蓝波", picked.value)

    def test_converts_exact_two_color_bracket_to_missing_wave(self):
        documents = ["半纸朱砂（双波中特）\n156期②个波色【绿红】√\n155期【蓝波绿波】√"]

        matches = crawler.extract_candidates(documents)

        self.assertEqual("蓝波", crawler.select_candidate(matches, 156, "top").value)
        self.assertEqual("红波", crawler.select_candidate(matches, 155, "top").value)

    def test_extracts_focus_title_section_first(self):
        documents = ["156期稳杀【红红红】开？00√\n【泉州两波哥】\n156期【蓝波绿波】√"]

        matches = crawler.extract_focus_candidates(documents, "泉州两波哥")

        self.assertEqual("红波", crawler.select_candidate(matches, 156, "top").value)

    def test_extracts_named_section_without_formula_page_interference(self):
        documents = ["\n".join(
            ["公式杀波", "第157期杀蓝波√", "双波中特"]
            + [f"导航{index}" for index in range(60)]
            + ["第157期双波中特〖红波蓝波〗开0000准"]
        )]

        matches = crawler.extract_section_candidates(documents, "双波中特")

        self.assertEqual("绿波", crawler.select_candidate(matches, 157, "top").value)

    def test_focus_section_keeps_long_history_target_issue(self):
        documents = ["\n".join(
            ["生功止过", "014期● ∽绝杀一波∽【红波】开:26准"]
            + [f"填充{index}" for index in range(40)]
            + ["157期● ∽绝杀一波∽【绿波】开:00准"]
        )]

        focus_matches = crawler.extract_focus_candidates(documents, "生功止过")
        all_matches = crawler.extract_candidates(documents)

        self.assertEqual("绿波", crawler.select_candidate(focus_matches, 157, "bottom").value)
        self.assertEqual("绿波", crawler.select_candidate(all_matches, 157, "bottom").value)

    def test_ignores_double_wave_inside_formula_page(self):
        documents = ["公式杀波\n152期双波中特〔红波蓝波〕\n第152期杀蓝波√"]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 152, "top")
        self.assertIsNotNone(picked)
        self.assertEqual("蓝波", picked.value)

    def test_explicit_wave_overrides_same_issue_double_wave(self):
        documents = ["153期双波必中《绿波蓝波》\n153期：绝杀一波 (蓝波）开？00准"]
        matches = crawler.extract_candidates(documents)
        picked = crawler.select_candidate(matches, 153, "top")
        self.assertIsNotNone(picked)
        self.assertEqual("蓝波", picked.value)

    def test_formats_success_output(self):
        output = crawler.format_success(
            [
                crawler.SuccessResult("甲", "红波"),
                crawler.SuccessResult("乙", "蓝波"),
                crawler.SuccessResult("丙", "红波"),
            ]
        )
        self.assertEqual(
            "内容 名称\n红波 甲\n蓝波 乙\n红波 丙\n\n内容 次数 排名\n红波 2 1\n蓝波 1 2\n",
            output,
        )

    def test_rejects_large_candidate_set_outside_top_window(self):
        candidates = [
            crawler.Candidate(100 + index, "红波", f"{100 + index}期", index)
            for index in range(40)
        ]
        picked = crawler.select_candidate(candidates, 135, "top")
        self.assertIsNone(picked)

    def test_missing_target_issue_reports_missing_even_in_large_set(self):
        candidates = [
            crawler.Candidate(100 + index, "红波", f"{100 + index}期", index)
            for index in range(40)
        ]
        picked, reason = crawler.select_candidate_with_reason(candidates, 200, "top")
        self.assertIsNone(picked)
        self.assertEqual("未找到指定期数", reason)

    def test_accepts_large_candidate_set_inside_bottom_window(self):
        candidates = [
            crawler.Candidate(100 + index, "红波", f"{100 + index}期", index)
            for index in range(40)
        ]
        picked = crawler.select_candidate(candidates, 135, "bottom")
        self.assertIsNotNone(picked)
        self.assertEqual(135, picked.issue)

    def test_ignores_other_duplicate_issue_for_target_selection(self):
        candidates = [
            crawler.Candidate(100 + index, "红波", f"{100 + index}期", index)
            for index in range(5)
        ]
        candidates.extend(
            [
                crawler.Candidate(101, "蓝波", "101期 蓝波", 5),
                crawler.Candidate(151, "绿波", "151期 绿波", 6),
            ]
        )
        picked = crawler.select_candidate(candidates, 151, "top")
        self.assertIsNotNone(picked)
        self.assertEqual("绿波", picked.value)

    def test_rejects_duplicate_target_issue(self):
        candidates = [
            crawler.Candidate(151, "蓝波", "151期 蓝波", 0),
            crawler.Candidate(151, "绿波", "151期 绿波", 1),
        ]
        picked, reason = crawler.select_candidate_with_reason(candidates, 151, "top")
        self.assertIsNone(picked)
        self.assertEqual("指定期数存在多条冲突数据", reason)

    def test_detects_conflicting_target_candidates(self):
        candidates = [
            crawler.Candidate(151, "蓝波", "151期 蓝波", 0),
            crawler.Candidate(151, "绿波", "151期 绿波", 1),
            crawler.Candidate(150, "蓝波", "150期 蓝波", 2),
        ]

        self.assertTrue(crawler.has_conflicting_target_candidates(candidates, 151))
        self.assertFalse(crawler.has_conflicting_target_candidates(candidates, 150))

    def test_extracts_exact_sha_yibo_candidates_only(self):
        documents = [
            "159期:必中两波:(红波蓝波)\n"
            "159期：絕殺一波 (紅波）開？00准\n"
            "158期绝杀一波【绿波】开兔16错"
        ]

        matches = crawler.extract_exact_sha_yibo_candidates(documents)

        self.assertEqual([(159, "红波"), (158, "绿波")], [(item.issue, item.value) for item in matches])

    def test_select_candidate_in_top_three_region(self):
        candidates = [
            crawler.Candidate(159, "红波", "159期", 0),
            crawler.Candidate(158, "绿波", "158期", 1),
            crawler.Candidate(157, "蓝波", "157期", 2),
            crawler.Candidate(156, "蓝波", "156期", 3),
        ]

        picked, reason = crawler.select_candidate_in_region_limit(candidates, 157, "top", 3)
        missed, missed_reason = crawler.select_candidate_in_region_limit(candidates, 156, "top", 3)

        self.assertEqual("蓝波", picked.value)
        self.assertIsNone(reason)
        self.assertIsNone(missed)
        self.assertEqual("指定期数不在顶部3组范围", missed_reason)

    def test_chitu_exact_sha_yibo_top_three_values(self):
        documents = [
            "澳门赤兔☯绝杀一波☯\n"
            "159期绝杀一波【绿波】开:0000准\n"
            "158期绝杀一波【红波】开:兔16准\n"
            "157期绝杀一波【蓝波】开:兔40准\n"
            "156期绝杀一波【绿波】开:马01准"
        ]

        candidates = crawler.extract_exact_sha_yibo_candidates(documents)
        picked, reason = crawler.select_candidate_in_region_limit(candidates, 157, "top", 3)
        missed, missed_reason = crawler.select_candidate_in_region_limit(candidates, 156, "top", 3)

        self.assertEqual("蓝波", picked.value)
        self.assertIsNone(reason)
        self.assertIsNone(missed)
        self.assertEqual("指定期数不在顶部3组范围", missed_reason)

    def test_focus_candidates_do_not_match_longer_prefix_names(self):
        documents = [
            "广东八二站第二版\n"
            "163期绝杀一波【红波】开马37准\n"
            "广东八二站\n"
            "164期绝杀一波【蓝波】开0000准"
        ]

        matches = crawler.extract_focus_candidates(documents, "广东八二站")

        self.assertEqual([(164, "蓝波")], [(item.issue, item.value) for item in matches])

    def test_accepts_duplicate_target_issue_when_values_match(self):
        candidates = [
            crawler.Candidate(151, "绿波", "151期:绝杀➡绿波【开:0000】✔", 0),
            crawler.Candidate(151, "绿波", "151期:绝杀➡绿波【开:0000】✔.advert img{}", 1),
        ]

        picked, reason = crawler.select_candidate_with_reason(candidates, 151, "bottom")

        self.assertIsNotNone(picked)
        self.assertIsNone(reason)
        self.assertEqual("绿波", picked.value)

    def test_rejects_top_candidate_when_conflict_is_outside_window(self):
        candidates = [
            crawler.Candidate(153, "蓝波", "153期 蓝波", 0),
            crawler.Candidate(152, "红波", "152期 红波", 1),
            crawler.Candidate(151, "绿波", "151期 绿波", 2),
            crawler.Candidate(150, "蓝波", "150期 蓝波", 3),
            crawler.Candidate(149, "红波", "149期 红波", 4),
        ]
        candidates.extend(
            crawler.Candidate(100 + index, "绿波", f"{100 + index}期 绿波", 5 + index)
            for index in range(30)
        )
        candidates.append(crawler.Candidate(153, "红波", "153期 红波", 35))

        picked, reason = crawler.select_candidate_with_reason(candidates, 153, "top")

        self.assertIsNone(picked)
        self.assertEqual("指定期数存在多条冲突数据", reason)

    def test_update_recent_cache_keeps_only_ten_periods(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "recent_10_cache.json"
            site = crawler.Site("甲", "https://example.test", "top")

            for period in range(151, 162):
                crawler.update_recent_cache(
                    path,
                    period,
                    [site],
                    [crawler.SuccessResult("甲", f"{period}波")],
                )

            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual([161, 160, 159, 158, 157, 156, 155, 154, 153, 152], data["periods"])
        self.assertNotIn("151", data["sites"]["甲"]["data"])
        self.assertEqual("161波", data["sites"]["甲"]["data"]["161"])

    def test_update_recent_cache_preserves_site_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "recent_10_cache.json"
            site = crawler.Site("乙", "https://example.test/a", "bottom", "双波中特")

            crawler.update_recent_cache(path, 157, [site], [crawler.SuccessResult("乙", "红波")])
            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual("https://example.test/a", data["sites"]["乙"]["url"])
        self.assertEqual("bottom", data["sites"]["乙"]["pick"])
        self.assertEqual("双波中特", data["sites"]["乙"]["keyword"])
        self.assertEqual("红波", data["sites"]["乙"]["data"]["157"])

    def test_update_recent_cache_skips_empty_result_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "recent_10_cache.json"
            site = crawler.Site("丙", "https://example.test/b", "top")

            crawler.update_recent_cache(path, 157, [site], [])

            self.assertFalse(path.exists())

    def test_build_site_history_uses_top_order(self):
        candidates = [
            crawler.Candidate(157, "红波", "157期 红波", 0),
            crawler.Candidate(156, "蓝波", "156期 蓝波", 1),
            crawler.Candidate(155, "绿波", "155期 绿波", 2),
        ]

        history = crawler.build_site_history(candidates, "top", keep=2)

        self.assertEqual({157: "红波", 156: "蓝波"}, history)

    def test_build_site_history_uses_bottom_order(self):
        candidates = [
            crawler.Candidate(155, "绿波", "155期 绿波", 0),
            crawler.Candidate(156, "蓝波", "156期 蓝波", 1),
            crawler.Candidate(157, "红波", "157期 红波", 2),
        ]

        history = crawler.build_site_history(candidates, "bottom", keep=2)

        self.assertEqual({157: "红波", 156: "蓝波"}, history)

    def test_duplicate_site_names_use_unique_cache_keys(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            crawler, "collect_site_history", side_effect=[{157: "红波"}, {157: "蓝波"}]
        ):
            sites = [
                crawler.Site("同名", "https://a.example", "top"),
                crawler.Site("同名", "https://b.example", "top"),
            ]
            cache, failures = crawler.rebuild_recent_cache(Path(tmp) / "cache.json", sites, workers=1)

        self.assertEqual([], failures)
        self.assertEqual(2, len(cache["sites"]))

    def test_rebuild_recent_cache_reuses_complete_existing_cache(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(crawler, "collect_site_history") as mocked:
            path = Path(tmp) / "cache.json"
            path.write_text(
                json.dumps(
                    {
                        "updated_at": "old",
                        "periods": [157, 156],
                        "sites": {
                            "甲": {
                                "name": "甲",
                                "url": "https://example.test",
                                "pick": "top",
                                "data": {str(157 - index): "红波" for index in range(10)},
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            cache, failures = crawler.rebuild_recent_cache(
                path,
                [crawler.Site("甲", "https://example.test", "top")],
                keep=10,
                workers=1,
            )

        mocked.assert_not_called()
        self.assertEqual([], failures)
        self.assertEqual(10, len(cache["sites"]["甲"]["data"]))

    def test_rebuild_recent_cache_reuses_partial_existing_cache_by_default(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(crawler, "collect_site_history") as mocked:
            path = Path(tmp) / "cache.json"
            path.write_text(
                json.dumps(
                    {
                        "updated_at": "old",
                        "periods": [157],
                        "sites": {
                            "甲": {
                                "name": "甲",
                                "url": "https://example.test",
                                "pick": "top",
                                "data": {"157": "红波"},
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            cache, failures = crawler.rebuild_recent_cache(
                path,
                [crawler.Site("甲", "https://example.test", "top")],
                keep=10,
                workers=1,
            )

        mocked.assert_not_called()
        self.assertEqual([], failures)
        self.assertEqual("红波", cache["sites"]["甲"]["data"]["157"])

    def test_rebuild_recent_cache_reuses_empty_existing_cache_by_default(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(crawler, "collect_site_history") as mocked:
            path = Path(tmp) / "cache.json"
            path.write_text(
                json.dumps(
                    {
                        "updated_at": "old",
                        "periods": [157],
                        "sites": {
                            "甲": {
                                "name": "甲",
                                "url": "https://example.test",
                                "pick": "top",
                                "data": {},
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            cache, failures = crawler.rebuild_recent_cache(
                path, [crawler.Site("甲", "https://example.test", "top")], keep=10, workers=1
            )

        mocked.assert_not_called()
        self.assertEqual([], failures)
        self.assertEqual({}, cache["sites"]["甲"]["data"])

    def test_rebuild_recent_cache_adds_empty_entry_for_missing_site_when_cache_exists(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(crawler, "collect_site_history") as mocked:
            path = Path(tmp) / "cache.json"
            path.write_text(
                json.dumps(
                    {
                        "updated_at": "old",
                        "periods": [157],
                        "sites": {
                            "旧站": {
                                "name": "旧站",
                                "url": "https://old.example",
                                "pick": "top",
                                "data": {"157": "红波"},
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            cache, failures = crawler.rebuild_recent_cache(
                path, [crawler.Site("新缺失", "https://new.example", "top")], keep=10, workers=1
            )

        mocked.assert_not_called()
        self.assertEqual([], failures)
        self.assertEqual({}, cache["sites"]["新缺失"]["data"])

    def test_rebuild_recent_cache_keeps_old_data_when_refresh_fails(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            crawler, "collect_site_history", side_effect=RuntimeError("boom")
        ):
            path = Path(tmp) / "cache.json"
            path.write_text(
                json.dumps(
                    {
                        "updated_at": "old",
                        "periods": [157],
                        "sites": {
                            "甲": {
                                "name": "甲",
                                "url": "https://example.test",
                                "pick": "top",
                                "data": {"157": "红波"},
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            cache, failures = crawler.rebuild_recent_cache(
                path,
                [crawler.Site("甲", "https://example.test", "top")],
                keep=10,
                workers=1,
                fill_incomplete=True,
            )

        self.assertEqual(1, len(failures))
        self.assertEqual("红波", cache["sites"]["甲"]["data"]["157"])

    def test_rebuild_recent_cache_keeps_empty_entry_when_refresh_fails_without_old_data(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            crawler, "collect_site_history", side_effect=RuntimeError("boom")
        ):
            cache, failures = crawler.rebuild_recent_cache(
                Path(tmp) / "cache.json", [crawler.Site("甲", "https://example.test", "top")], keep=10, workers=1
            )

        self.assertEqual(1, len(failures))
        self.assertIn("甲", cache["sites"])
        self.assertEqual({}, cache["sites"]["甲"]["data"])

    def test_rebuild_recent_cache_progress_prints_failure_reason(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            crawler, "collect_site_history", side_effect=RuntimeError("")
        ), patch("sys.stdout", output):
            crawler.rebuild_recent_cache(
                Path(tmp) / "cache.json",
                [crawler.Site("甲", "https://example.test", "top")],
                keep=10,
                workers=1,
                progress=True,
            )

        self.assertIn("失败原因: 抓取失败: RuntimeError: 无异常详情", output.getvalue())


if __name__ == "__main__":
    unittest.main()

def test_keyword_on_normal_site_without_registered_parser_fails(monkeypatch):
    calls = []

    def fake_collect_documents(url):
        calls.append(("normal", url))
        return ["<div>专属栏目</div><div>169期 绝杀一波 红波 开0000准</div>"]

    def fake_reference_documents(url, keyword, issue=None):
        calls.append(("reference", url, keyword, issue))
        return []

    monkeypatch.setattr(crawler, "collect_documents", fake_collect_documents)
    monkeypatch.setattr(crawler, "collect_reference_post_documents", fake_reference_documents)

    site = crawler.Site("普通站", "https://example.test/topic/1.html", "top", "专属栏目")

    result, error = crawler.crawl_site(site, 169)

    assert result is None
    assert "未登记站点级专属解析" in error
    assert calls == [("normal", "https://example.test/topic/1.html")]


def test_manual_crawl_rejects_undesignated_generic_focus_match(monkeypatch) -> None:
    site = crawler.Site("甲站", "https://example.test/a", "top", "甲站")
    documents = ["甲站\n188期绝杀一波【红波】开0000准"]

    monkeypatch.setattr(crawler, "collect_documents", lambda url: documents)
    monkeypatch.setattr(crawler, "collect_rendered_documents", lambda url: documents)

    result, error = crawler.crawl_site(site, 188)

    assert result is None
    assert "未登记站点级专属解析" in error


def test_existing_registered_focus_site_can_still_use_anchored_parser(monkeypatch) -> None:
    site = crawler.Site("彩民书籍", "https://example.test/", "bottom", "绝杀一波")
    documents = ["彩民书籍\n188期绝杀一波【红波】开0000准"]

    monkeypatch.setattr(crawler, "collect_documents", lambda url: documents)
    monkeypatch.setattr(crawler, "collect_rendered_documents", lambda url: documents)

    result, error = crawler.crawl_site(site, 188)

    assert error is None
    assert result == crawler.SuccessResult("彩民书籍", "红波")


def test_exact_sha_yibo_reads_spaced_juesha_wave() -> None:
    candidates = crawler.extract_exact_sha_yibo_candidates(["169期:绝 杀 红 波"])

    assert candidates == [crawler.Candidate(169, "红波", "169期:绝 杀 红 波", 0)]


def test_keyword_exact_sha_yibo_parser_uses_spaced_juesha_wave() -> None:
    documents = ["港澳彩资讯网【绝杀一波】\n169期:绝 杀 红 波"]
    site = crawler.Site("港澳彩资讯", "https://example.test/", "top", "绝杀一波精准")

    candidates = crawler.extract_primary_candidates(documents, site)

    assert candidates == [crawler.Candidate(169, "红波", "169期:绝 杀 红 波", 0)]



def test_reference_user_exact_sha_yibo_formats_from_screenshots() -> None:
    samples = {
        "迷人教授": "177期::绝杀一波、【绿波】开0000准\n176期::绝杀一波、【蓝波】开鸡10错",
        "帅气成衣": "177期：绝杀一波【绿波】开:0000准\n176期：绝杀一波【蓝波】开鸡10错",
        "好奇好奇": "177期：【绝杀一波】【绿波】开00准\n176期：【绝杀一波】【红波】开鸡10准",
        "拥挤门": "095期.绝杀一波【绿波】开猴35准\n096期.绝杀一波【蓝波】开鼠43准\n097期.绝杀一波【红波】开猴11准",
    }

    for name, document in samples.items():
        site = crawler.Site(name, "https://qvuuqqs.8imf7-hteuh-ylwuqv.xyz/#/users/1", "bottom" if name == "拥挤门" else "top", "绝杀一波")
        candidates = crawler.extract_primary_candidates([document], site)

        assert candidates, name
        assert all("绝杀一波" in item.line for item in candidates)


def test_miren_jiaoshou_config_uses_reference_navigation() -> None:
    site = next(item for item in crawler.load_sites(crawler.SCRIPT_DIR / "sites.json") if item.name == "迷人教授")

    assert site.keyword == "绝杀一波"
    assert crawler.uses_reference_navigation(site)

def test_baoma_uses_exact_sha_yibo_special_parser() -> None:
    site = crawler.Site("宝码玄机", "https://example.test/", "top")
    document = "178期:绝杀一波【蓝波】开:??准\n177期:绝杀一波【绿波】开:蛇14准"

    candidates = crawler.extract_primary_candidates([document], site)

    assert [(item.issue, item.value) for item in candidates] == [(178, "蓝波"), (177, "绿波")]


def test_qianren_yimian_uses_classic_two_wave_special_parser() -> None:
    site = crawler.Site("千人一面", "https://example.test/", "bottom")
    document = "178期【千人一面】【经典两波】\n177期【其他栏目】【经典两波】\n178期:【经典两波】【红波绿波】开：0000准\n177期:【经典两波】【绿波红波】开：蛇14错"

    candidates = crawler.extract_primary_candidates([document], site)

    assert [(item.issue, item.value) for item in candidates] == [(178, "蓝波"), (177, "蓝波")]


def test_yuanjia_dashao_uses_two_wave_special_parser() -> None:
    site = crawler.Site("袁家大少", "https://example.test/", "top")
    document = "178期:【两波中特】\n作者：袁家大少\n178期: ☸两波中特☸ 【红波蓝波】 开??准\n176期: ☸两波中特☸ 【红波蓝波】 开10鸡准"

    candidates = crawler.extract_primary_candidates([document], site)

    assert [(item.issue, item.value) for item in candidates] == [(178, "绿波"), (176, "绿波")]



def test_hehua_lianou_uses_bose_zhongte_special_parser() -> None:
    site = crawler.Site("荷花莲藕", "https://example.test/", "top")
    document = "178期:【波色中特】独家提供\n作者:荷花莲藕\n178期❦波色中特❦【绿波红波】❦开0000准\n177期❦波色中特❦【绿波蓝波】❦开蛇14准"

    candidates = crawler.extract_primary_candidates([document], site)

    assert [(item.issue, item.value) for item in candidates] == [(178, "蓝波"), (177, "红波")]



def test_reference_exact_user_page_uses_structured_user_collector(monkeypatch) -> None:
    calls = []

    def fake_user_documents(site, period):
        calls.append(("user", site, period))
        return ["178期：绝杀一波【红波】开:0000准"]

    monkeypatch.setattr(crawler, "collect_qvuuqs_user_documents", fake_user_documents)

    site = crawler.Site("帅气成衣", "https://qvuuqqs.8imf7-hteuh-ylwuqv.xyz/#/users/1572", "top", "绝杀一波")

    result, error = crawler.crawl_site(site, 178)

    assert error is None
    assert result == crawler.SuccessResult("帅气成衣", "红波")
    assert calls == [("user", site, 178)]


def test_unregistered_dynamic_user_page_does_not_use_first_card(monkeypatch) -> None:
    site = crawler.Site("未登记", "https://example.test/#/users/123", "top", "绝杀一波")

    with pytest.raises(ValueError, match="未登记动态用户页专属解析"):
        crawler.collect_documents_for_site(site, 178)


def test_iframe_topic_url_id_is_required_and_must_match_final_url() -> None:
    assert crawler.extract_topic_record_id("https://example.test/topic/625836.html") == "625836"

    with pytest.raises(ValueError, match="topic文章ID"):
        crawler.extract_topic_record_id("https://example.test/iframe/3/25.html")

    with pytest.raises(ValueError, match="URL文章ID不一致"):
        crawler.validate_iframe_topic_page(
            final_url="https://example.test/topic/625967.html",
            expected_topic_id="625836",
            site_name="针锋相对",
            article_count=1,
            heading="精华资料 201期: 针锋相对「绝杀一波」",
            body="201期：绝杀一波【红波】开：0000准",
        )


def test_iframe_topic_parser_keeps_title_and_body_in_one_record() -> None:
    documents = crawler.validate_iframe_topic_page(
        final_url="https://example.test/topic/625836.html",
        expected_topic_id="625836",
        site_name="针锋相对",
        article_count=1,
        heading="精华资料 201期: 针锋相对「绝杀一波」",
        body="针锋相对 发表于 07月19日\n201期：绝杀一波【红波】开：0000准",
    )

    assert documents == [
        "精华资料 201期: 针锋相对「绝杀一波」",
        "针锋相对 发表于 07月19日\n201期：绝杀一波【红波】开：0000准",
    ]

    with pytest.raises(ValueError, match="文章容器不唯一"):
        crawler.validate_iframe_topic_page(
            final_url="https://example.test/topic/625836.html",
            expected_topic_id="625836",
            site_name="针锋相对",
            article_count=2,
            heading="精华资料 201期: 针锋相对「绝杀一波」",
            body="201期：绝杀一波【红波】开：0000准",
        )


def test_iframe_topic_site_uses_dedicated_outer_record_collector(monkeypatch) -> None:
    calls = []

    def fake_topic_documents(site, period):
        calls.append((site, period))
        return ["精华资料 201期: 针锋相对「绝杀一波」", "201期：绝杀一波【红波】开：0000准"]

    monkeypatch.setattr(crawler, "collect_iframe_topic_documents", fake_topic_documents)
    site = crawler.Site("针锋相对", "https://example.test/topic/625836.html", "bottom")

    documents = crawler.collect_documents_for_site(site, 201)

    assert documents[1].startswith("201期")
    assert calls == [(site, 201)]


def test_iframe_topic_sites_use_exact_outer_body_parser() -> None:
    site = crawler.Site("自强不息", "https://example.test/topic/625967.html", "top")
    documents = [
        "杀肖区 201期: 自强不息「绝杀一波」",
        "自强不息 发表于 07月20日\n201期:【绝杀一波】【红波】开：0000准\n200期:【绝杀一波】【蓝波】开：龙39准",
    ]

    candidates = crawler.extract_primary_candidates(documents, site)

    assert [(item.issue, item.value) for item in candidates] == [(201, "红波"), (200, "蓝波")]




def test_anju_ziliaoyuan_uses_dedicated_reference_collector(monkeypatch) -> None:
    calls = []

    def fake_anju_documents(url, period):
        calls.append((url, period))
        return ["179期:绝杀一波【绿波】开:000准"]

    monkeypatch.setattr(crawler, "collect_anju_ziliaoyuan_documents", fake_anju_documents)

    site = crawler.Site("安居资料员", "https://qvuuqqs.8imf7-hteuh-ylwuqv.xyz/#/users/4710/references/15339310", "top", "绝杀一波")

    result, error = crawler.crawl_site(site, 179)

    assert error is None
    assert result == crawler.SuccessResult("安居资料员", "绿波")
    assert calls == [(site.url, 179)]


def test_anju_ziliaoyuan_collector_validates_target_issue(monkeypatch) -> None:
    def fake_reference_documents(url, keyword, timeout=20, issue=None):
        return ["179期:绝杀一波【绿波】开:000准"]

    monkeypatch.setattr(crawler, "collect_reference_post_documents", fake_reference_documents)

    documents = crawler.collect_anju_ziliaoyuan_documents("https://example.test/", 179)

    assert documents == ["179期:绝杀一波【绿波】开:000准"]


def test_pending_duplicate_name_is_rejected_before_fetch(monkeypatch) -> None:
    import check_pending_against_cache as pending_check

    site = crawler.Site("已有站", "https://new.example/", "top")
    existing_sites = [crawler.Site("已有站", "https://old.example/", "bottom")]

    rejected = pending_check.find_same_name_rejection(site, existing_sites)

    assert rejected == {
        "name": "已有站",
        "url": "https://new.example/",
        "status": "duplicate_name",
        "error": "失败原因: 新增站点名称与已有站点同名，直接拒收: 已有站",
    }


def test_pending_different_name_is_not_rejected() -> None:
    import check_pending_against_cache as pending_check

    site = crawler.Site("新站", "https://new.example/", "top")
    existing_sites = [crawler.Site("已有站", "https://old.example/", "bottom")]

    assert pending_check.find_same_name_rejection(site, existing_sites) is None


def test_pending_duplicate_name_uses_sites_file(monkeypatch, tmp_path) -> None:
    import check_pending_against_cache as pending_check

    sites_file = tmp_path / "sites.json"
    sites_file.write_text('[{"name":"港澳彩资讯","url":"https://old.example/","pick":"top"}]', encoding="utf-8")
    monkeypatch.setattr(pending_check, "SITES_FILE", sites_file)

    existing_sites = pending_check.load_existing_sites()
    rejected = pending_check.find_same_name_rejection(crawler.Site("港澳彩资讯", "https://new.example/", "top"), existing_sites)

    assert rejected is not None
    assert rejected["status"] == "duplicate_name"


def test_pending_report_declares_cache_only_duplicate_source() -> None:
    import check_pending_against_cache as pending_check

    report = pending_check.new_report({"periods": [188, 187]})

    assert report["detector"] == "check_pending_against_cache"
    assert report["duplicate_source"] == "recent_10_cache.json"
    assert report["source_policy"] == "cache_only"
    assert "analyze_latest.py" in report["legacy_duplicate_detectors_blocked"]
    assert report["periods"] == [188, 187]


def test_new_pending_standard_exact_sha_yibo_names_use_exact_parser() -> None:
    for name in ["无错绝杀", "金吊桶", "宝马玄机"]:
        site = crawler.Site(name, "https://example.test/", "top")
        candidates = crawler.extract_primary_candidates(["180期绝杀一波【绿波】开00准\n179期砍杀一波【红波】开龙15准"], site)
        assert candidates[0].value == "绿波"


def test_liuxuanwang_reads_aocai_section_with_parenthesized_wave() -> None:
    site = crawler.Site("六玄网", "https://example.test/#87127", "top")
    document = """
    澳彩六玄网【绝杀一波】
    184期绝杀一波（绿波）开？00准
    183期绝杀一波（蓝波）开羊24准
    182期绝杀一波（绿波）开虎41准
    """

    candidates = crawler.extract_primary_candidates([document], site)

    assert [(item.issue, item.value) for item in candidates] == [(184, "绿波"), (183, "蓝波"), (182, "绿波")]


def test_liuxuanwang_reads_split_aocai_section_title() -> None:
    site = crawler.Site("六玄网", "https://example.test/#87127", "top")
    document = """
    澳彩六玄网
    【绝杀一波】
    188期绝杀一波〖红波〗开？00准
    187期绝杀一波〖绿波〗开马01准
    """

    candidates = crawler.extract_primary_candidates([document], site)

    assert [(item.issue, item.value) for item in candidates] == [(188, "红波"), (187, "绿波")]


def test_liuxuanwang_collector_reads_syibo_script_first(monkeypatch) -> None:
    calls = []

    def fake_fetch_text(url, timeout=20):
        calls.append(url)
        return 'document.writeln(" <th>澳彩六玄网【绝杀一波】</th>");\n' \
            'document.writeln(" <td>190期绝杀一波<font color=\'#FF0000\'>〖蓝波〗</font>开？00准</td>");'

    monkeypatch.setattr(crawler, "fetch_text", fake_fetch_text)
    monkeypatch.setattr(crawler, "collect_rendered_documents", lambda url: (_ for _ in ()).throw(AssertionError("不应走渲染回退")))

    site = crawler.Site("六玄网", "https://example.test/#87127", "top")
    documents = crawler.collect_documents_for_site(site, 190)

    candidates = crawler.extract_primary_candidates(documents, site)
    assert [(item.issue, item.value) for item in candidates] == [(190, "蓝波")]
    assert calls == ["https://example.test/cj/syibo.js"]


def test_liuxuanwang_collector_retries_original_url_when_script_has_no_candidates(monkeypatch) -> None:
    calls = []

    def fake_rendered_documents(url):
        calls.append(url)
        if url.endswith("/915577.html"):
            return ["普通页面，没有绝杀一波数据"]
        return ["澳彩六玄网【绝杀一波】\n188期绝杀一波〖红波〗开？00准"]

    monkeypatch.setattr(crawler, "fetch_text", lambda url, timeout=20: "普通脚本")
    monkeypatch.setattr(crawler, "collect_rendered_documents", fake_rendered_documents)

    site = crawler.Site("六玄网", "https://example.test/#87127", "top")
    documents = crawler.collect_documents_for_site(site, 188)

    candidates = crawler.extract_primary_candidates(documents, site)
    assert [(item.issue, item.value) for item in candidates] == [(188, "红波")]
    assert calls == ["https://example.test/915577.html", "https://example.test/#87127"]


def test_crawl_keeps_missing_period_reason_when_fallback_has_no_section(monkeypatch) -> None:
    site = crawler.Site("六玄网", "https://example.test/#87127", "top")

    monkeypatch.setattr(
        crawler,
        "collect_documents_for_site",
        lambda site, period: ["澳彩六玄网【绝杀一波】\n190期绝杀一波〖蓝波〗开？00准"],
    )
    monkeypatch.setattr(crawler, "collect_rendered_documents", lambda url: ["普通页面，没有绝杀一波数据"])

    result, error = crawler.crawl_site(site, 189)

    assert result is None
    assert "未找到指定期数" in error


def test_erxiao_sima_uses_only_named_juesha_yibo_section() -> None:
    site = crawler.Site("二肖四码", "https://example.test/", "top")
    document = """
    澳门二肖四码
    『绝杀一波』
    183期:绝杀一波【绿波】→开:0000中
    182期:绝杀一波【红波】→开:虎41中
    181期:绝杀一波【蓝波】→开:鼠19中
    澳门二肖四码
    『综合绝杀区』
    183期：絕殺一波 (藍波）開？00准
    182期：絕殺一波 (綠波）開虎41准
    """

    candidates = crawler.extract_primary_candidates([document], site)

    assert [(item.issue, item.value) for item in candidates] == [(183, "绿波"), (182, "红波"), (181, "蓝波")]


def test_erxiao_sima_accepts_html_wrapped_juesha_yibo_title() -> None:
    site = crawler.Site("二肖四码", "https://example.test/", "top")
    document = """
    &lt;span style="color: #ffffff;"&gt;澳门二肖四码&lt;/span&gt;
    &lt;span style="color: #ffffff;"&gt;『绝杀一波』&lt;/span&gt;
    186期:绝杀一波【蓝波】→开:0000中
    185期:绝杀一波【绿波】→开:羊36中
    183期:绝杀一波【绿波】→开:羊24中
    186期：絕殺一波 (綠波）開？00准
    """

    candidates = crawler.extract_primary_candidates([document], site)

    assert [(item.issue, item.value) for item in candidates] == [(186, "蓝波"), (185, "绿波"), (183, "绿波")]




def test_liuhehuang_uses_juesha_series_section_only() -> None:
    site = crawler.Site("六合皇", "https://example.test/", "top")
    document = """
    <div id="con_jsxl_5" style="display: none;">
      <p>188期☯杀一波色☯【绿波】开？？准</p>
      <p>187期☯杀一波色☯【蓝波】开马01准</p>
    </div>
    <div id="con_jsxl_6">
      <p>188期☯杀一波色☯【红波】开？00准</p>
    </div>
    """

    candidates = crawler.extract_primary_candidates([document], site)

    assert [(item.issue, item.value) for item in candidates] == [(188, "绿波"), (187, "蓝波")]


def test_new_pending_missing_wave_names_use_missing_wave_parser() -> None:
    samples = {
        "澳门118开奖": "180期主二波【蓝波】防【绿波】开000准",
        "藏宝图": "180期 主蓝波,防绿波 开0000准",
        "目中无人": "180期主【绿波】 防【红波】 开??准",
        "牵肠挂肚": "180期☞双波中特☜【红波防绿波】开:0000准",
        "波王波王": "180期 波王一波【蓝波】\n波王双波【蓝波红波】开??准",
    }
    for name, document in samples.items():
        site = crawler.Site(name, "https://example.test/", "top")
        candidates = crawler.extract_primary_candidates([document], site)
        assert candidates == [crawler.Candidate(180, "红波" if name in {"澳门118开奖", "藏宝图"} else "蓝波" if name in {"目中无人", "牵肠挂肚"} else "绿波", candidates[0].line, 0)]


def test_two_wave_missing_sites_use_their_exact_rendered_formats() -> None:
    zhuojin = crawler.Site("捉襟见肘", "https://example.test/", "top")
    pusuo = crawler.Site("扑朔迷离", "https://example.test/", "top")

    zhuojin_candidates = crawler.extract_primary_candidates(
        ["192期《两波中特》《红波绿波》开0000准\n191期《两波中特》《蓝波绿波》开虎29错"],
        zhuojin,
    )
    pusuo_candidates = crawler.extract_primary_candidates(
        ["192期：【两波中特】（绿波红波）开0000准\n191期：【两波中特】（绿波蓝波）开虎29错"],
        pusuo,
    )

    assert [(item.issue, item.value) for item in zhuojin_candidates] == [(192, "蓝波"), (191, "红波")]
    assert [(item.issue, item.value) for item in pusuo_candidates] == [(192, "蓝波"), (191, "红波")]


def test_youya_xiaoshu_uses_single_bracket_two_wave_format() -> None:
    site = crawler.Site("优雅小树", "https://example.test/", "top")
    documents = [
        "196期【优雅小树】【双波中特】已公开\n"
        "196期:两波中特【红波蓝波】开？00中\n"
        "195期:两波中特【绿波蓝波】开马25中\n"
        "194期:其他栏目【红波绿波】开马26中"
    ]

    candidates = crawler.extract_primary_candidates(documents, site)

    assert [(item.issue, item.value) for item in candidates] == [(196, "绿波"), (195, "红波")]


def test_xiashuo_baidao_uses_own_two_wave_section_and_ignores_duplicate_pair() -> None:
    site = crawler.Site("瞎说白道", "https://example.test/", "top")
    document = (
        "199期：【两波中特】瞎说白道\n"
        "199期【两波中特】【红波+红波】开0000准\n"
        "198期【两波中特】【红波+蓝波】开鼠07准\n"
        "197期【两波中特】【红波+绿波】开猪08准\n"
        "199期：【绝杀半波】其他栏目\n"
        "199期：绝杀一波【蓝波】开0000准"
    )

    candidates = crawler.extract_primary_candidates([document], site)

    assert [(item.issue, item.value) for item in candidates] == [(198, "绿波"), (197, "蓝波")]


def test_houqi_zhixiu_stops_at_next_section_title() -> None:
    site = crawler.Site("后起之秀", "https://example.test/", "top")
    document = (
        "特码料199期:【绝杀一波】后起之秀\n"
        "198期：绝杀一波【绿波】开0000准\n"
        "197期：绝杀一波【蓝波】开猪08准\n"
        "特码料199期:【绝杀一行】其他栏目\n"
        "199期：绝杀一波【红波】开0000准"
    )

    candidates = crawler.extract_primary_candidates([document], site)

    assert [(item.issue, item.value) for item in candidates] == [(198, "绿波"), (197, "蓝波")]


def test_new_pending_table_names_read_sha_yibo_column() -> None:
    document = "期数 杀一肖 杀尾 杀一波 杀一头 结果\n180期 牛 5尾 红波 3头 0000\n179期 兔 4尾 绿波 0头 龙15"
    for name in ["招财猫", "玄机", "玄机阁", "今日闲情"]:
        site = crawler.Site(name, "https://example.test/", "top")
        candidates = crawler.extract_primary_candidates([document], site)
        assert [(item.issue, item.value) for item in candidates[:2]] == [(180, "红波"), (179, "绿波")]


def test_new_pending_special_color_formats() -> None:
    fruit = crawler.extract_primary_candidates(["180期 ※绝杀一波※【红单】 开??准"], crawler.Site("水果奶奶", "https://example.test/", "top"))
    assert [(item.issue, item.value) for item in fruit] == [(180, "红波")]

    instant = crawler.extract_primary_candidates(["179期: 瞬杀一波 开:龙15准\n【红】"], crawler.Site("瞬杀一波", "https://example.test/", "bottom"))
    assert [(item.issue, item.value) for item in instant] == [(179, "红波")]

    king = crawler.extract_primary_candidates(["180期杀号统计(特开0000)\n杀一波图:【绿波】"], crawler.Site("王者", "https://example.test/", "top"))
    assert [(item.issue, item.value) for item in king] == [(180, "绿波")]

def test_clean_pending_site_specific_parsers() -> None:
    samples = {
        "白蛇传": ("159期:走势杀波【蓝波】开:龙39准\n177期:走势杀波【红波】开:蛇14准", [(159, "蓝波"), (177, "红波")]),
        "潮余诗音": ("180期边缘爱情稳杀【红波】开？00准\n179期边缘爱情稳杀【蓝波】开龙15错", [(180, "红波"), (179, "蓝波")]),
            "后起之秀": (
                "特码料179期:【绝杀一波】后起之秀\n"
                "179期：绝杀一波【蓝波】开龙15错\n178期：绝杀一波【绿波】开牛18准",
                [(179, "蓝波"), (178, "绿波")],
            ),
    }
    for name, (document, expected) in samples.items():
        site = crawler.Site(name, "https://example.test/", "top")
        candidates = crawler.extract_primary_candidates([document], site)
        assert [(item.issue, item.value) for item in candidates] == expected

def test_failed_pending_keyword_variant_parsers() -> None:
    samples = {
        "签牌": ("179期绝杀一波【红波】开0000准\n178期绝杀一波【蓝波】开牛18准", [(179, "红波"), (178, "蓝波")]),
        "巫马沉璧": ("180期杀一波【蓝波】开0000√\n179期杀一波【红波】开龙15√", [(180, "蓝波"), (179, "红波")]),
        "身强体壮": ("180期:✍必杀一波✍【绿波】开0000准\n179期:✍必杀一波✍【红波】开龙15准", [(180, "绿波"), (179, "红波")]),
        "寄人篱下": ("180期:绝杀一波【红波】开:？00准\n179期:绝杀一波【绿波】开:龙15准", [(180, "红波"), (179, "绿波")]),
        "一台二妙": ("180期：≮必杀一波≯【绿波】 开??准\n179期：≮必杀一波≯【绿波】 开龙15准", [(180, "绿波"), (179, "绿波")]),
        "王牌特工": ("180期:精杀一波【红波】开 ?? 准\n177期:精杀一波【绿波】开 蛇14 准", [(180, "红波"), (177, "绿波")]),
        "塞翁失马": ("180期 [绝杀一波]【红双】开 ?? 准\n178期 [绝杀一波]【蓝双】开 18牛 准", [(180, "红波"), (178, "蓝波")]),
    }
    for name, (document, expected) in samples.items():
        site = crawler.Site(name, "https://example.test/", "top")
        candidates = crawler.extract_primary_candidates([document], site)
        assert [(item.issue, item.value) for item in candidates] == expected


def test_failed_pending_inline_and_t_equals_wave_parsers() -> None:
    soft = crawler.extract_primary_candidates([
        "177期【柔情杀手】【绝杀绿波】T14√ 178期【柔情杀手】【绝杀蓝波】T18√ 179期【柔情杀手】【绝杀红波】T15√"
    ], crawler.Site("柔情杀手", "https://example.test/", "bottom"))
    assert [(item.issue, item.value) for item in soft] == [(177, "绿波"), (178, "蓝波"), (179, "红波")]

    accurate = crawler.extract_primary_candidates([
        "178期 26-46-22-44-31-17 T18=绿波√\n179期 特杀一波：绿波"
    ], crawler.Site("准杀一波", "https://example.test/", "bottom"))
    assert [(item.issue, item.value) for item in accurate] == [(178, "绿波"), (179, "绿波")]


