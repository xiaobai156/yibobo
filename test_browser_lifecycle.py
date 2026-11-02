import sys
import types

import sha_yibo_crawler as crawler


class FakePage:
    def __init__(self, browser):
        self.browser = browser
        self.closed = False

    def goto(self, url, **kwargs):
        self.url = url

    def locator(self, selector):
        return self

    def inner_text(self, **kwargs):
        return "body"

    def content(self):
        return "<body>body</body>"

    def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self):
        self.pages = []
        self.closed = False

    def new_page(self, **kwargs):
        page = FakePage(self)
        self.pages.append(page)
        return page

    def close(self):
        self.closed = True


class FakePlaywright:
    def __init__(self, state):
        self.state = state
        self.chromium = self

    def launch(self, **kwargs):
        self.state["launches"] += 1
        self.state["browser"] = FakeBrowser()
        return self.state["browser"]

    def stop(self):
        self.state["stopped"] += 1


class FakeFlakyPage(FakePage):
    """前 N 次 goto 抛导航超时，之后成功，用于验证渲染兜底必须重试。"""

    def __init__(self, browser, failures_left):
        super().__init__(browser)
        self.failures_left = failures_left
        self.waits = []

    def goto(self, url, **kwargs):
        self.waits.append(kwargs.get("wait_until"))
        if self.failures_left > 0:
            self.failures_left -= 1
            raise TimeoutError(f'Page.goto: Timeout {kwargs.get("timeout")}ms exceeded')
        return super().goto(url, **kwargs)

    def wait_for_timeout(self, milliseconds):
        return None


class FakeFlakyBrowser(FakeBrowser):
    def __init__(self, failures):
        super().__init__()
        self.failures = failures

    def new_page(self, **kwargs):
        page = FakeFlakyPage(self, self.failures)
        self.pages.append(page)
        return page


class FakeFlakyPlaywright(FakePlaywright):
    def __init__(self, state, failures):
        super().__init__(state)
        self.failures = failures

    def launch(self, **kwargs):
        self.state["launches"] += 1
        self.state["browser"] = FakeFlakyBrowser(self.failures)
        return self.state["browser"]


def test_rendered_documents_retries_navigation_timeout(monkeypatch):
    """渲染兜底导航超时（本次 268 期一台二妙的失败形态）必须重试而不是直接失败。"""
    crawler._close_browser_sessions()
    state = {"launches": 0, "stopped": 0, "browser": None}

    # 第一轮 networkidle + domcontentloaded 都超时，第二轮恢复
    fake_module = types.SimpleNamespace(
        sync_playwright=lambda: FakeFlakyPlaywright(state, failures=3)
    )
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_module)

    documents = crawler.collect_rendered_documents("https://example.test/flaky")

    assert documents == ["body", "<body>body</body>"]
    page = state["browser"].pages[0]
    assert page.waits == ["networkidle", "domcontentloaded", "networkidle", "domcontentloaded"]
    crawler._close_browser_sessions()


def test_rendered_calls_reuse_browser_and_close_each_page(monkeypatch):
    crawler._close_browser_sessions()
    state = {"launches": 0, "stopped": 0, "browser": None}

    fake_module = types.SimpleNamespace(
        sync_playwright=lambda: FakePlaywright(state)
    )
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_module)

    crawler.collect_rendered_documents("https://example.test/one")
    crawler.collect_rendered_documents("https://example.test/two")

    assert state["launches"] == 1
    assert len(state["browser"].pages) == 2
    assert all(page.closed for page in state["browser"].pages)
    crawler._close_browser_sessions()
    assert state["browser"].closed
    assert state["stopped"] == 1
