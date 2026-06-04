#!/usr/bin/env bash
# notifykit 一鍵安裝：建 venv → 升級 pip → editable 安裝 → 備好 config.json
#
#   ./install.sh            # 預設裝進 ./.venv
#   ./install.sh --yaml     # 同時裝 PyYAML（要用 .yaml 設定檔才需要）
#   VENV=~/.venv-nk ./install.sh   # 自訂 venv 路徑
set -euo pipefail

cd "$(dirname "$0")"

VENV="${VENV:-.venv}"
EXTRAS=""
for arg in "$@"; do
  case "$arg" in
    --yaml) EXTRAS="[yaml]" ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "未知參數：$arg（用 --help 看用法）" >&2; exit 2 ;;
  esac
done

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null || { echo "找不到 $PY，請先安裝 Python 3.8+" >&2; exit 1; }

echo "→ 建立 venv：$VENV"
"$PY" -m venv "$VENV"

echo "→ 升級 pip"
"$VENV/bin/python" -m pip install --quiet --upgrade pip

echo "→ 安裝 notifykit（editable${EXTRAS:+ + extras $EXTRAS}）"
"$VENV/bin/python" -m pip install -e ".$EXTRAS"

if [ ! -f config.json ]; then
  cp config.example.json config.json
  echo "→ 已從範本建立 config.json（記得填 token/webhook；它已被 .gitignore 忽略）"
fi

echo
echo "✓ 安裝完成。試跑（免 token 的 dry-run）："
echo "    $VENV/bin/notifykit --config config.json --dry-run run"
echo "  或先啟用 venv，之後直接打 notifykit："
echo "    source $VENV/bin/activate"
