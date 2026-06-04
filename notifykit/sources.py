"""資料源：產出中性 Message。可插（static / command / rss / github / http_json / jira）。

新資料源：寫一個 Source 子類（實作 fetch()->Message）並註冊到 REGISTRY。
全部零依賴（urllib + xml.etree + base64，stdlib）。
"""
import base64
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .message import Message, Section


# ---- HTTP / 解析小工具 ----
def _get(url, headers=None, timeout=20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "notifykit", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:  # 帶回 API 回應 body，方便看出錯在哪
        body = e.read().decode("utf-8", "replace").strip()
        raise RuntimeError(f"HTTP {e.code}：{body or e.reason}") from None


def _get_json(url, headers=None, timeout=20):
    return json.loads(_get(url, {"Accept": "application/json", **(headers or {})}, timeout).decode("utf-8", "replace"))


def _dig(obj, path: str):
    """用 dot path 取值，支援數字索引：'data.items.0.title'。取不到回 None。"""
    if not path:
        return obj
    for seg in path.split("."):
        if seg == "":
            continue
        if isinstance(obj, list):
            try:
                obj = obj[int(seg)]
            except (ValueError, IndexError):
                return None
        elif isinstance(obj, dict):
            obj = obj.get(seg)
        else:
            return None
        if obj is None:
            return None
    return obj


def _local(tag: str) -> str:  # 去掉 XML namespace，只留 local name
    return tag.split("}")[-1]


def _first_local(el, name):
    for c in el.iter():
        if c is not el and _local(c.tag) == name:
            return c
    return None


def _text_local(el, name) -> str:
    c = _first_local(el, name)
    return (c.text or "").strip() if c is not None else ""


# ---- Sources ----
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


class RssSource(Source):
    """RSS / Atom feed → 最新 N 則標題 + 連結（namespace 無關）。
    cfg: url（必填）, title, limit（預設 10）。"""

    def __init__(self, cfg):
        self.cfg = cfg

    def fetch(self):
        root = ET.fromstring(_get(self.cfg["url"]))
        items = [c for c in root.iter() if _local(c.tag) in ("item", "entry")]
        lines = []
        for it in items[: self.cfg.get("limit", 10)]:
            title = _text_local(it, "title") or "(no title)"
            link_el = _first_local(it, "link")
            link = (link_el.get("href") or (link_el.text or "")).strip() if link_el is not None else ""
            lines.append(f"- [{title}]({link})" if link else f"- {title}")
        title = self.cfg.get("title") or _text_local(root, "title") or "RSS"
        return Message(title=title, sections=[Section(lines=lines or ["(empty feed)"])])


class GithubSource(Source):
    """GitHub repo 最新動態（REST API）。
    cfg: repo（'owner/name' 必填）, kind（releases|commits|pulls，預設 releases）,
         token（可選，提高 rate limit）, limit（預設 10）, title。"""

    def __init__(self, cfg):
        self.cfg = cfg

    def fetch(self):
        repo, kind = self.cfg["repo"], self.cfg.get("kind", "releases")
        if kind not in ("releases", "commits", "pulls"):
            raise ValueError(f"未知 github kind：{kind}（releases|commits|pulls）")
        limit = self.cfg.get("limit", 10)
        headers = {"Accept": "application/vnd.github+json"}
        if self.cfg.get("token"):
            headers["Authorization"] = f"Bearer {self.cfg['token']}"
        data = _get_json(f"https://api.github.com/repos/{repo}/{kind}?per_page={limit}", headers)
        lines = []
        for it in data[:limit]:
            url = it.get("html_url", "")
            if kind == "releases":
                name = it.get("name") or it.get("tag_name") or "(release)"
                lines.append(f"- [{name}]({url})")
            elif kind == "commits":
                first = ((it.get("commit") or {}).get("message", "") or "").splitlines()
                lines.append(f"- [{(it.get('sha') or '')[:7]}]({url}) {first[0] if first else '(commit)'}")
            else:  # pulls
                lines.append(f"- [#{it.get('number')} {it.get('title', '')}]({url})")
        title = self.cfg.get("title") or f"GitHub {repo} · {kind}"
        return Message(title=title, sections=[Section(lines=lines or ["(無資料)"])])


class HttpJsonSource(Source):
    """GET 一個 JSON API，用 dot path 抽欄位組成列表。
    cfg: url（必填）, headers（dict 可選）, list_path（指向陣列的 dot path，可選）,
         title_key（item 內 dot path，預設 title）, url_key（可選 dot path）, limit（預設 10）, title。"""

    def __init__(self, cfg):
        self.cfg = cfg

    def fetch(self):
        items = _dig(_get_json(self.cfg["url"], self.cfg.get("headers")), self.cfg.get("list_path", ""))
        if not isinstance(items, list):
            items = [items]
        tkey, ukey = self.cfg.get("title_key", "title"), self.cfg.get("url_key")
        lines = []
        for it in items[: self.cfg.get("limit", 10)]:
            t = _dig(it, tkey)
            t = "(no title)" if t in (None, "") else str(t)
            u = _dig(it, ukey) if ukey else None
            lines.append(f"- [{t}]({u})" if u else f"- {t}")
        return Message(title=self.cfg.get("title", "HTTP JSON"), sections=[Section(lines=lines or ["(無資料)"])])


class JiraSource(Source):
    """Jira issues（JQL）→ 列表。用 email:token 做 Basic auth（Atlassian API token）。
    cfg: base_url（如 https://x.atlassian.net 必填）, email, token, jql（必填）,
         limit（預設 20）, title。"""

    def __init__(self, cfg):
        self.cfg = cfg

    def fetch(self):
        base = self.cfg["base_url"].rstrip("/")
        limit = self.cfg.get("limit", 20)
        url = (f"{base}/rest/api/2/search?jql={urllib.parse.quote(self.cfg['jql'])}"
               f"&maxResults={limit}&fields=summary,status")
        headers = {}
        if self.cfg.get("email") and self.cfg.get("token"):
            cred = base64.b64encode(f"{self.cfg['email']}:{self.cfg['token']}".encode()).decode()
            headers["Authorization"] = f"Basic {cred}"
        lines = []
        for it in _get_json(url, headers).get("issues", [])[:limit]:
            key, f = it.get("key", ""), it.get("fields", {})
            status = (f.get("status") or {}).get("name", "")
            lines.append(f"- [{key}]({base}/browse/{key}) {f.get('summary', '')}"
                         + (f" — {status}" if status else ""))
        return Message(title=self.cfg.get("title") or "Jira",
                       sections=[Section(lines=lines or ["(無符合 issue)"])])


REGISTRY = {
    "static": StaticSource,
    "command": CommandSource,
    "rss": RssSource,
    "github": GithubSource,
    "http_json": HttpJsonSource,
    "jira": JiraSource,
}


def build_source(cfg: dict) -> Source:
    t = cfg.get("type")
    if t not in REGISTRY:
        raise ValueError(f"未知資料源 type：{t}（支援：{', '.join(REGISTRY)}）")
    return REGISTRY[t](cfg)
