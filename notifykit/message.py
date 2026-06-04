"""中性訊息模型 — 與平台無關。各通道的 render 再轉成 Slack/TG/LINE 格式。

行內連結用 markdown 寫法 `[文字](url)`，render 時各平台轉自己的格式：
  Slack `<url|文字>` · Telegram `<a href="url">文字</a>` · LINE `文字: url`
"""
from dataclasses import dataclass, field


@dataclass
class Section:
    heading: str = ""
    lines: list = field(default_factory=list)  # list[str]，可含 [文字](url)


@dataclass
class Message:
    title: str = ""
    sections: list = field(default_factory=list)  # list[Section]
    footer: str = ""

    @classmethod
    def from_body(cls, title: str, body: str) -> "Message":
        """把一段純文字 body（多行）包成單一 section 的 Message。"""
        lines = (body or "").splitlines()
        return cls(title=title or "", sections=[Section(lines=lines)])
