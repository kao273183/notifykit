<#
.SYNOPSIS
  notifykit 一鍵安裝（Windows / PowerShell）：建 venv → 升級 pip → editable 安裝 → 備好 config.json
.EXAMPLE
  .\install.ps1               # 預設裝進 .\.venv
  .\install.ps1 -Yaml         # 同時裝 PyYAML（要用 .yaml 設定檔才需要）
  .\install.ps1 -Venv C:\venv-nk   # 自訂 venv 路徑
.NOTES
  若遇到「無法載入...因為這個系統上已停用指令碼執行」，先在 PowerShell 跑：
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#>
[CmdletBinding()]
param(
    [switch]$Yaml,
    [string]$Venv = ".venv"
)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$extras = if ($Yaml) { "[yaml]" } else { "" }

# 找 Python 建 venv：優先用 py launcher，否則 python（建好後一律用 venv 內的 python）
Write-Host "→ 建立 venv：$Venv"
if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv $Venv }
elseif (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv $Venv }
else { Write-Error "找不到 Python，請先安裝 Python 3.8+（記得勾選 Add to PATH）"; exit 1 }

$vpy = Join-Path $Venv "Scripts\python.exe"

Write-Host "→ 升級 pip"
& $vpy -m pip install --quiet --upgrade pip

Write-Host "→ 安裝 notifykit（editable$(if($extras){" + extras $extras"}))"
& $vpy -m pip install -e ".$extras"

if (-not (Test-Path "config.json")) {
    Copy-Item "config.example.json" "config.json"
    Write-Host "→ 已從範本建立 config.json（記得填 token/webhook；它已被 .gitignore 忽略）"
}

$exe = Join-Path $Venv "Scripts\notifykit.exe"
Write-Host ""
Write-Host "✓ 安裝完成。試跑（免 token 的 dry-run）："
Write-Host "    $exe --config config.json --dry-run run"
Write-Host "  或先啟用 venv，之後直接打 notifykit："
Write-Host "    $Venv\Scripts\Activate.ps1"
