# -*- coding: utf-8 -*-
"""表格单元格分行版本测试：每个单元格单独成行时仍须按"杀一波"列取波色。"""
from __future__ import annotations

import sha_yibo_crawler as crawler


def build_cells(rows: list[list[str]]) -> str:
    """HTML 结构里每个 <td> 独占一行，模拟招财猫/今日闲情的分行单元格。"""
    cells = "".join(f"<td>{cell}</td>\n" for row in rows for cell in row)
    return f"<table>\n{cells}</table>"


ZHAOCAI_HEADER = ["期数", "杀一肖", "杀一波", "杀一尾", "杀一头", "开奖结果"]
ZHAOCAI_ROWS = [
    ["317期", "(羊)", "(红)", "(2)", "(1)", "开:發00准"],
    ["316期", "(鸡)", "(绿)", "(3)", "(3)", "开:龙03准"],
    ["315期", "(兔)", "(红)", "(7)", "(1)", "开:兔15准"],
]

XIANQING_HEADER = ["期数", "杀肖", "杀尾", "杀一波", "杀一头", "结果"]
XIANQING_ROWS = [
    ["317期", "马", "3尾", "蓝波", "4头", "000准"],
    ["316期", "蛇", "7尾", "绿波", "2头", "龙03准"],
    ["315期", "牛", "9尾", "红波", "3头", "羊48准"],
]


def test_split_cell_table_reads_wave_column() -> None:
    document = build_cells([ZHAOCAI_HEADER, *ZHAOCAI_ROWS])
    candidates = crawler.extract_table_sha_yibo_column_candidates([document])
    assert [(item.issue, item.value) for item in candidates] == [
        (317, "红波"),
        (316, "绿波"),
        (315, "红波"),
    ]


def test_split_cell_wave_written_as_full_word() -> None:
    document = build_cells([XIANQING_HEADER, *XIANQING_ROWS])
    candidates = crawler.extract_table_sha_yibo_column_candidates([document])
    assert [(item.issue, item.value) for item in candidates] == [
        (317, "蓝波"),
        (316, "绿波"),
        (315, "红波"),
    ]


def test_inline_row_table_still_uses_original_parser() -> None:
    document = (
        "<table>"
        "<tr><td>期数</td><td>生肖</td><td>杀尾</td><td>杀一波</td><td>杀一头</td><td>结果</td></tr>"
        "<tr><td>317期</td><td>虎</td><td>7尾</td><td>绿波</td><td>0头</td><td>0000</td></tr>"
        "<tr><td>316期</td><td>龙</td><td>3尾</td><td>红波</td><td>1头</td><td>1111</td></tr>"
        "</table>"
    )
    candidates = crawler.extract_table_sha_yibo_column_candidates([document])
    assert [(item.issue, item.value) for item in candidates] == [(317, "绿波"), (316, "红波")]


def test_table_without_wave_column_returns_nothing() -> None:
    header = ["期数", "杀肖", "杀尾", "杀一头", "结果"]
    rows = [["317期", "马", "3尾", "4头", "000准"]]
    document = build_cells([header, *rows])
    assert crawler.extract_table_sha_yibo_column_candidates([document]) == []
