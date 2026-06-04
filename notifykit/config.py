"""設定載入。預設 JSON（零依賴）；若裝了 PyYAML 且副檔名 .yaml 也支援。"""
import json
import os


def load(path: str) -> dict:
    path = os.path.expanduser(path)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml  # 可選依賴
        except ImportError as e:
            raise SystemExit("讀 .yaml 需要 PyYAML（pip install pyyaml），或改用 .json") from e
        return yaml.safe_load(text)
    return json.loads(text)
