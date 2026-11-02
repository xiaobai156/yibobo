# -*- coding: utf-8 -*-
"""修正：页面顶部未开奖的下一期（开0000/开：00/开？00）不得被判为旧年数据。"""
from pathlib import Path
P = Path(r"C:/Users/Administrator/Desktop/每天工具/爬虫合集/杀一波/sha_yibo_crawler.py")
src = P.read_text(encoding="utf-8")

helper = '''
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


'''

anchor = "def _looks_like_stale_year_block(issues: list[int], issue: int) -> bool:"
assert src.count(anchor) == 1
src = src.replace(anchor, helper.lstrip("\n") + anchor, 1)

old = '''    issues = [item.issue for item in candidates]
    # 先判整段旧年：即便目标期根本不在里面，也要给出准确原因
    if _looks_like_stale_year_block(issues, issue):
        return [], "列表已绕回，疑似旧年数据"
'''
new = '''    issues = [item.issue for item in candidates]
    # 先判整段旧年：即便目标期根本不在里面，也要给出准确原因。
    # 顶部未开奖的下一期不算旧年证据。
    effective_issues = [
        item.issue for item in candidates if not _is_pending_period_candidate(item, issue)
    ]
    if _looks_like_stale_year_block(effective_issues, issue):
        return [], "列表已绕回，疑似旧年数据"
'''
assert src.count(old) == 1
src = src.replace(old, new, 1)
P.write_text(src, encoding="utf-8")
print("已打补丁")
