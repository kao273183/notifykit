"""通道 adapter：把 Message render 後送到 Slack / Telegram / LINE。零依賴（urllib）。"""
import json
import urllib.request

from .render import render_slack, render_telegram, render_line


def _post(url, payload, headers=None, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


class Channel:
    name = "base"

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def render(self, msg) -> str:
        raise NotImplementedError

    def _send(self, rendered: str):
        raise NotImplementedError

    def deliver(self, msg, dry_run=False):
        r = self.render(msg)
        if dry_run:
            return ("DRY", r)
        return self._send(r)


class SlackChannel(Channel):
    name = "slack"

    def render(self, msg):
        return render_slack(msg)

    def _send(self, r):
        # Incoming Webhook；或之後可擴 bot token chat.postMessage
        return _post(self.cfg["webhook_url"], {"text": r})


class TelegramChannel(Channel):
    name = "telegram"

    def render(self, msg):
        return render_telegram(msg)

    def _send(self, r):
        url = f"https://api.telegram.org/bot{self.cfg['token']}/sendMessage"
        return _post(url, {
            "chat_id": self.cfg["chat_id"],
            "text": r,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        })


class LineChannel(Channel):
    name = "line"

    def render(self, msg):
        return render_line(msg)

    def _send(self, r):
        # LINE Messaging API push（LINE Notify 已於 2025 停用）
        url = "https://api.line.me/v2/bot/message/push"
        return _post(url, {
            "to": self.cfg["to"],
            "messages": [{"type": "text", "text": r[:4900]}],  # LINE 單則上限 5000
        }, headers={"Authorization": f"Bearer {self.cfg['token']}"})


REGISTRY = {"slack": SlackChannel, "telegram": TelegramChannel, "line": LineChannel}


def build_channel(cfg: dict) -> Channel:
    t = cfg.get("type")
    if t not in REGISTRY:
        raise ValueError(f"未知通道 type：{t}（支援：{', '.join(REGISTRY)}）")
    return REGISTRY[t](cfg)
