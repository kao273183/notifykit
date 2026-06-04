"""notifykit — 通用多通道通知器（Slack / Telegram / LINE）。

零依賴（只用 Python stdlib）。資料源可插（command / static / 自訂），
通道可插，訊息以中性 Message 模型表達、各通道自行 render 成該平台格式。

用法見 README.md；CLI：`python -m notifykit --config X.json {send|run} [--dry-run]`
"""
__version__ = "0.1.0"
