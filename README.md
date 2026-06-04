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

## 安裝

零執行期依賴、跨平台（macOS / Linux / Windows）。免安裝可直接 `python3 -m notifykit ...`；想要 `notifykit` 指令就裝起來。

**一鍵安裝腳本**（建 venv → editable 安裝 → 備好 config.json）：

```bash
# macOS / Linux
./install.sh                 # 加 --yaml 連 PyYAML 一起裝
```
```powershell
# Windows（PowerShell）
.\install.ps1                # 加 -Yaml 連 PyYAML 一起裝
# 若被執行原則擋下：Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**或手動**：

```bash
# macOS / Linux
python3 -m venv .venv
.venv/bin/pip install -e .            # .yaml 設定檔：.venv/bin/pip install -e '.[yaml]'
.venv/bin/notifykit --help
```
```powershell
# Windows（PowerShell）
py -3 -m venv .venv
.venv\Scripts\pip install -e .        # .yaml 設定檔：.venv\Scripts\pip install -e '.[yaml]'
.venv\Scripts\notifykit --help
```

或用 **pipx** 當全域 CLI 工具（兩平台皆可）：`pipx install .`

裝好後下面的 `python3 -m notifykit` 都可改成 `notifykit`（Windows venv 執行檔在 `.venv\Scripts\`）。

## 快速開始

```bash
# 1. 複製設定
cp config.example.json config.json   # 填入各通道 token/webhook

# 2. 免 token 先 dry-run 看各平台 render 長怎樣
python3 -m notifykit --config config.json --dry-run run

# 3. 手動發一則（body 支援 [文字](url)；'-' 讀 stdin）
#    多行：bash/zsh 用 $'...\n...'；PowerShell 用 "...`n..."（雙引號內反引號 n）
python3 -m notifykit --config config.json send --title "部署完成" --body $'v1.2.3 上線\n- [release](https://x/r/1.2.3)'
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
`command` source 的指令會經 shell 執行（`shell=True`），**勿放不可信內容**。

## 資料源（source.type）

全部零依賴（`urllib` / `xml.etree` / `base64`），`run` 時會 `fetch()` 成 Message：

| type | 用途 | 必填 | 可選 |
|------|------|------|------|
| `static` | 固定文字 | — | `title`, `body` |
| `command` | 跑 shell 指令、stdout 當 body（可包任何腳本） | `command` | `title`, `timeout` |
| `rss` | RSS / Atom feed 最新 N 則標題+連結 | `url` | `title`, `limit`(10) |
| `github` | repo 最新 releases / commits / pulls | `repo`(`owner/name`) | `kind`(releases), `token`, `limit`(10), `title` |
| `http_json` | GET 任意 JSON API，用 dot path 抽欄位 | `url` | `headers`, `list_path`, `title_key`(title), `url_key`, `limit`(10), `title` |
| `jira` | JQL 撈 issues（Atlassian API token，Basic auth） | `base_url`, `jql` | `email`, `token`, `limit`(20), `title` |

```jsonc
{ "type": "rss",    "url": "https://github.com/python/cpython/releases.atom", "limit": 5 }
{ "type": "github", "repo": "pallets/flask", "kind": "releases", "token": "ghp_..." }
{ "type": "http_json", "url": "https://api.example.com/news",
  "list_path": "data.items", "title_key": "headline", "url_key": "link" }
{ "type": "jira", "base_url": "https://you.atlassian.net",
  "jql": "assignee=currentUser() AND statusCategory!=Done ORDER BY updated DESC",
  "email": "you@x.com", "token": "ATATT..." }
```
`http_json` 的 `list_path` / `title_key` / `url_key` 支援 dot path（含數字索引，如 `data.items.0.title`）；省略 `list_path` 則整個 response 當單筆/陣列。

## 擴充

- **新通道**：在 `channels.py` 加一個 `Channel` 子類（實作 `render` + `_send`）並註冊到 `REGISTRY`。
- **新資料源**：在 `sources.py` 加 `Source` 子類（實作 `fetch()->Message`）並註冊到 `REGISTRY`。

## 模組用法
```python
from notifykit.message import Message, Section
from notifykit.channels import build_channel
msg = Message(title="X", sections=[Section(heading="變化", lines=["- [PR](url)"])])
build_channel({"type":"telegram","token":"...","chat_id":"..."}).deliver(msg)
```
