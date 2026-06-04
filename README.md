# notifykit

通用多通道通知器 — 把任何資料源的摘要，發到 **Slack / Telegram / LINE**。
零依賴（只用 Python 3 stdlib）、專案無關、可當 CLI 或 import 模組。

## 設計

```
資料源(Source) → 中性 Message(title + sections + [文字](url)) → 各通道 render + 送出
  ├ static / command（內建）          ├ Slack    (mrkdwn, webhook)
  └ 自訂(jira/github/rss…)            ├ Telegram (HTML, Bot API)
                                      └ LINE     (純文字, Messaging API push)
```

訊息用中性模型表達，連結寫 `[文字](url)`，各通道自動轉成該平台格式。

## 快速開始

```bash
# 1. 複製設定
cp config.example.json config.json   # 填入各通道 token/webhook

# 2. 免 token 先 dry-run 看各平台 render 長怎樣
python3 -m notifykit --config config.json --dry-run run

# 3. 手動發一則（body 支援 [文字](url)；'-' 讀 stdin）
python3 -m notifykit --config config.json send --title "部署完成" --body "v1.2.3 上線\n- [release](https://x/r/1.2.3)"
echo "管線也行" | python3 -m notifykit --config config.json send --title "Build"

# 4. 跑設定裡的 source（例：command source 包你的腳本）
python3 -m notifykit --config config.json run
```

放進排程（cron / launchd）即每日通知。任何腳本只要 `python3 -m notifykit ... run` 或 `send` 就能多通道發送。

## 通道設定

### Slack（最簡單）
Slack App → Incoming Webhooks → 開啟 → Add New Webhook → 複製 URL 填 `webhook_url`。

### Telegram（簡單、免費）
1. 跟 **@BotFather** 對話 → `/newbot` → 拿 **bot token**。
2. 把 bot 加進你的群／私訊它，發一則訊息。
3. 取 **chat_id**：開 `https://api.telegram.org/bot<TOKEN>/getUpdates`，看 `chat.id`。
4. 填 `token` + `chat_id`。

### LINE（較麻煩；LINE Notify 已於 2025 停用）
走 **Messaging API**：
1. [LINE Developers](https://developers.line.biz) 建 Provider + Messaging API channel（會有一個 LINE 官方帳號）。
2. 取 **Channel access token**（長期）填 `token`。
3. 取收訊者 **userId / groupId**（加好友後從 webhook event 拿，或用自己的 userId）填 `to`。
4. 免費方案 push 訊息有額度限制。

## 設定檔

`config.json`（或裝了 `pyyaml` 後用 `.yaml`）：
```json
{
  "source": { "type": "command", "title": "每日摘要", "command": "your-script.sh" },
  "channels": [
    { "type": "slack",    "enabled": true,  "webhook_url": "..." },
    { "type": "telegram", "enabled": true,  "token": "...", "chat_id": "..." },
    { "type": "line",     "enabled": false, "token": "...", "to": "..." }
  ]
}
```
`enabled:false` 的通道會跳過。**token/webhook 是機密，config.json 勿進 git**（用 `.gitignore`）。

## 擴充

- **新通道**：在 `channels.py` 加一個 `Channel` 子類（實作 `render` + `_send`）並註冊到 `REGISTRY`。
- **新資料源**：在 `sources.py` 加 `Source` 子類（實作 `fetch()->Message`）並註冊。
  - 例：把現有 jira-daily 包成 `CommandSource`（`command` 指向那支腳本）即可串通；之後再寫原生 `JiraSource`。

## 模組用法
```python
from notifykit.message import Message, Section
from notifykit.channels import build_channel
msg = Message(title="X", sections=[Section(heading="變化", lines=["- [PR](url)"])])
build_channel({"type":"telegram","token":"...","chat_id":"..."}).deliver(msg)
```
