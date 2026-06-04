"""資料源：產出中性 Message。可插（command / static / 之後加 jira / github / rss…）。"""
import subprocess

from .message import Message


class Source:
    def fetch(self) -> Message:
        raise NotImplementedError


class StaticSource(Source):
    """固定文字（測試 / 簡單通知用）。cfg: title, body。"""

    def __init__(self, cfg):
        self.cfg = cfg

    def fetch(self):
        return Message.from_body(self.cfg.get("title", "Notification"), self.cfg.get("body", ""))


class CommandSource(Source):
    """跑一個 shell 指令，stdout 當訊息 body → 任何腳本都能餵 notifykit。
    cfg: command（必填）, title, timeout。body 支援 [文字](url) 行內連結。"""

    def __init__(self, cfg):
        self.cfg = cfg

    def fetch(self):
        out = subprocess.run(
            self.cfg["command"], shell=True, capture_output=True, text=True,
            timeout=self.cfg.get("timeout", 120),
        )
        body = (out.stdout or "").strip() or "(no output)"
        return Message.from_body(self.cfg.get("title", "Notification"), body)


# TODO（後續）：JiraSource — 把 jira-daily 的 fetch/diff 移植過來，
#   cfg: base_url, email, token, jql；產出 Message（new/status/comment/stale 區塊）。
#   先用 CommandSource 包現有 jira-daily 腳本即可串通。

REGISTRY = {"static": StaticSource, "command": CommandSource}


def build_source(cfg: dict) -> Source:
    t = cfg.get("type")
    if t not in REGISTRY:
        raise ValueError(f"未知資料源 type：{t}（支援：{', '.join(REGISTRY)}）")
    return REGISTRY[t](cfg)
