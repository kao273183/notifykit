"""把中性 Message render 成各平台格式。

- Slack：mrkdwn（`*粗*`、連結 `<url|文字>`）
- Telegram：HTML parse_mode（`<b>`、`<a href>`；escape 只需處理 & < >，比 MarkdownV2 省事）
- LINE：純文字（text message 不吃 markdown）
"""
import html as _html
import re

_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


# ---- Slack ----
def _slack_esc(s: str) -> str:
    # Slack text 需 escape & < >（否則內文的這些字元會被當特殊語法）
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _slack_inline(t: str) -> str:
    # 先把連結外的文字 escape，再放回 <url|文字>（url/文字本身也 escape）
    parts, last = [], 0
    for m in _LINK.finditer(t):
        parts.append(_slack_esc(t[last:m.start()]))
        parts.append(f"<{_slack_esc(m.group(2))}|{_slack_esc(m.group(1))}>")
        last = m.end()
    parts.append(_slack_esc(t[last:]))
    return "".join(parts)


def render_slack(msg) -> str:
    out = []
    if msg.title:
        out.append(f"*{_slack_inline(msg.title)}*")
    for s in msg.sections:
        if s.heading:
            out.append(f"\n*{_slack_inline(s.heading)}*")
        out.extend(_slack_inline(ln) for ln in s.lines)
    if msg.footer:
        out.append(f"\n{_slack_inline(msg.footer)}")
    return "\n".join(out)


# ---- Telegram (HTML) ----
def _tg_inline(t: str) -> str:
    parts, last = [], 0
    for m in _LINK.finditer(t):
        parts.append(_html.escape(t[last:m.start()], quote=False))
        parts.append(f'<a href="{_html.escape(m.group(2))}">{_html.escape(m.group(1), quote=False)}</a>')
        last = m.end()
    parts.append(_html.escape(t[last:], quote=False))
    return "".join(parts)


def render_telegram(msg) -> str:
    out = []
    if msg.title:
        out.append(f"<b>{_tg_inline(msg.title)}</b>")
    for s in msg.sections:
        if s.heading:
            out.append(f"\n<b>{_tg_inline(s.heading)}</b>")
        out.extend(_tg_inline(ln) for ln in s.lines)
    if msg.footer:
        out.append(f"\n{_tg_inline(msg.footer)}")
    return "\n".join(out)


# ---- LINE (plain text) ----
def _line_inline(t: str) -> str:
    return _LINK.sub(lambda m: f"{m.group(1)}: {m.group(2)}", t)


def render_line(msg) -> str:
    out = []
    if msg.title:
        out.append(f"■ {_line_inline(msg.title)}")
    for s in msg.sections:
        if s.heading:
            out.append(f"\n— {_line_inline(s.heading)} —")
        out.extend(_line_inline(ln) for ln in s.lines)
    if msg.footer:
        out.append(f"\n{_line_inline(msg.footer)}")
    return "\n".join(out)
