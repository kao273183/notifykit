"""通道 adapter：把 Message render 後送到 Slack / Telegram / LINE / Lark。零依賴（urllib）。"""
import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request

from .render import render_slack, render_telegram, render_line, render_lark


def _post(url, payload, headers=None, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:  # 帶回 API 回應 body，方便看出錯在哪
        body = e.read().decode("utf-8", "replace").strip()
        raise RuntimeError(f"HTTP {e.code}：{body or e.reason}") from None


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
            "text": r[:4096],  # Telegram 單則上限 4096 字元
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


class LarkChannel(Channel):
    name = "lark"

    def render(self, msg):
        return render_lark(msg)

    def _send(self, r):
        # Lark / 飛書 自訂機器人 webhook；互動卡片用 lark_md 保留連結
        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "elements": [{"tag": "markdown", "content": r}],
            },
        }
        secret = self.cfg.get("secret")
        if secret:  # 機器人若開啟「簽名校驗」，需帶 timestamp + sign（HMAC-SHA256）
            ts = str(int(time.time()))
            sign = base64.b64encode(
                hmac.new(f"{ts}\n{secret}".encode("utf-8"), digestmod=hashlib.sha256).digest()
            ).decode("utf-8")
            payload["timestamp"] = ts
            payload["sign"] = sign
        status, body = _post(self.cfg["webhook_url"], payload)
        # Lark 即使參數錯也回 HTTP 200，錯誤藏在 body 的 code≠0，需自行檢查
        try:
            data = json.loads(body)
            if isinstance(data, dict) and data.get("code", 0):
                raise RuntimeError(f"Lark API code {data['code']}：{data.get('msg', '')}")
        except json.JSONDecodeError:
            pass
        return status, body


REGISTRY = {"slack": SlackChannel, "telegram": TelegramChannel,
            "line": LineChannel, "lark": LarkChannel}


def build_channel(cfg: dict) -> Channel:
    t = cfg.get("type")
    if t not in REGISTRY:
        raise ValueError(f"未知通道 type：{t}（支援：{', '.join(REGISTRY)}）")
    return REGISTRY[t](cfg)
