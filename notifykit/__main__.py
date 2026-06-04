"""CLI：python -m notifykit --config X.json {send|run} [--dry-run]

  send  --title T --body B   手動訊息（body 為 - 則讀 stdin；支援 [文字](url)）
  run                         跑 config.source 產生訊息
共通：--dry-run 只印各通道 render 結果、不實際送出（免 token 即可測）。
"""
import argparse
import sys

from .channels import build_channel
from .config import load
from .message import Message
from .sources import build_source


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="notifykit", description="通用多通道通知（Slack/Telegram/LINE）")
    p.add_argument("--config", required=True, help="設定檔（.json，或裝了 pyyaml 的 .yaml）")
    p.add_argument("--dry-run", action="store_true", help="只印 render、不送出")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("send", help="手動訊息")
    sp.add_argument("--title", default="")
    sp.add_argument("--body", default="-", help="訊息內文；'-' 讀 stdin")
    sub.add_parser("run", help="跑 config.source")
    a = p.parse_args(argv)

    cfg = load(a.config)
    channels = [build_channel(c) for c in cfg.get("channels", []) if c.get("enabled", True)]
    if not channels:
        print("（沒有啟用的通道）", file=sys.stderr)
        return 1

    if a.cmd == "send":
        body = sys.stdin.read() if a.body == "-" else a.body
        msg = Message.from_body(a.title, body)
    else:  # run
        if "source" not in cfg:
            print("config 缺 source", file=sys.stderr)
            return 1
        msg = build_source(cfg["source"]).fetch()

    rc = 0
    for ch in channels:
        try:
            res = ch.deliver(msg, dry_run=a.dry_run)
            if a.dry_run:
                print(f"\n===== [{ch.name}] =====\n{res[1]}")
            else:
                status, _ = res
                print(f"[{ch.name}] 已送出（HTTP {status}）")
        except Exception as e:  # noqa: BLE001 — 一個通道失敗不擋其他
            print(f"[{ch.name}] 失敗：{e}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
