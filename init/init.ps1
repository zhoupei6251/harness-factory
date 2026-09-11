# init.ps1 — Windows PowerShell 版本
# 用法：.\init.ps1 [-Reset | -Verify]
param(
  [switch]$Reset,
  [switch]$Verify
)

$ErrorActionPreference = "Stop"
$TEMPLATES = Join-Path $PSScriptRoot "templates"
$TARGET = ".harness"

if ($Verify) {
  Write-Host "=== verifying $TARGET ==="
  if (-not (Test-Path $TARGET)) { Write-Host "FAIL: $TARGET not found"; exit 1 }
  foreach ($f in @("state/config.md","state/MEMORY.md","state/state.json","state/profile.md")) {
    if (-not (Test-Path (Join-Path $TARGET $f))) { Write-Host "MISSING: $TARGET/$f" }
  }
  Write-Host "=== done ==="
  return
}

if ($Reset) {
  Write-Host "WARN: -Reset 会删除 $TARGET 全部内容"
  $confirm = Read-Host "确认 nuke? (yes/no)"
  if ($confirm -ne "yes") { Write-Host "aborted"; exit 1 }
  Remove-Item -Recurse -Force $TARGET
}

Write-Host "=== init $TARGET ==="
New-Item -ItemType Directory -Force -Path $TARGET | Out-Null
Copy-Item -Recurse -Force (Join-Path $TEMPLATES "*") $TARGET
Write-Host "=== done; .harness/ 已建 ==="
