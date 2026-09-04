#!/usr/bin/env bash
# validate-plugins.sh — 审查链依赖插件存在性检查
#
# 目的：code 审查链依赖 ecc（java-reviewer 等）和 superpowers（brainstorming 等）
# 插件。插件缺失时 Claude 会静默降级（忽略不存在的 skill/agent 引用，不报错）。
# 本脚本在启动/验证时显式检查，缺失则明确告警。
#
# 检查对象（从 ~/.claude/settings.json enabledPlugins 读取 + 目录存在性验证）：
#   ecc@ecc                      → java-reviewer / security-reviewer 等审查 agent
#   superpowers@claude-plugins-official → brainstorming / systematic-debugging 等流程 skill
#
# 用法：
#   bash tests/validate-plugins.sh          # 检查，缺失则退出 1
#   bash tests/validate-plugins.sh --warn   # 检查，缺失只告警不失败（CI 宽容模式）

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

WARN_ONLY=0
[[ "${1:-}" == "--warn" ]] && WARN_ONLY=1
[[ "${1:-}" == "--strict" ]] && STRICT=1
# 2026-09-04 phase-0: ecc 已降级为可选插件——缺失仅告警，不计入 hard-fail。
# 本地副本 agents/ecc-*.md 仍提供 java/security/database reviewer 兜底。
WARN_ONLY_PLUGINS=("ecc@ecc")
is_warn_only() {
  local p="$1"
  for w in "${WARN_ONLY_PLUGINS[@]}"; do
    [[ "$p" == "$w" ]] && return 0
  done
  return 1
}

CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
SETTINGS="$CLAUDE_DIR/settings.json"
PLUGINS_DIR="$CLAUDE_DIR/plugins"
MISSING=0
WARN_MISSING=0

echo "==> 插件依赖检查"

# 1. settings.json 存在性
if [[ ! -f "$SETTINGS" ]]; then
  echo "  ⚠️  settings.json 不存在: $SETTINGS（可能未初始化 Claude Code）"
  MISSING=$((MISSING + 1))
else
  echo "  ✅ settings.json 存在"
fi

# 2. 检查关键插件（settings.json 启用 + 目录存在）
check_plugin() {
  local plugin_id="$1" dir_name="$2" reason="$3"
  local warn_only=0
  is_warn_only "$plugin_id" && warn_only=1
  local enabled=""
  if [[ -f "$SETTINGS" ]]; then
    enabled="$(python - "$SETTINGS" "$plugin_id" <<'PYEOF' 2>/dev/null || echo ""
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        cfg = json.load(f)
    enabled = cfg.get("enabledPlugins", cfg.get("plugins", {}))
    print("1" if enabled.get(sys.argv[2]) else "0")
except Exception:
    print("0")
PYEOF
)"
  fi

  if [[ "$enabled" == "1" ]]; then
    echo "  ✅ $plugin_id 已在 settings.json 启用"
  else
    if [[ "$warn_only" -eq 1 ]]; then
      echo "  ⚠️  $plugin_id 未在 settings.json 启用（已降级为可选，本地 agents/ecc-*.md 兜底）"
      WARN_MISSING=$((WARN_MISSING + 1))
    else
      echo "  ⚠️  $plugin_id 未在 settings.json 启用（$reason）"
      MISSING=$((MISSING + 1))
    fi
    return
  fi

  # 目录存在性验证
  if [[ -d "$PLUGINS_DIR/marketplaces/$dir_name" ]]; then
    echo "  ✅ 插件目录存在: $dir_name"
  else
    if [[ "$warn_only" -eq 1 ]]; then
      echo "  ⚠️  插件目录缺失: $PLUGINS_DIR/marketplaces/$dir_name（已降级为可选）"
      WARN_MISSING=$((WARN_MISSING + 1))
    else
      echo "  ❌ 插件目录缺失: $PLUGINS_DIR/marketplaces/$dir_name（$reason）"
      MISSING=$((MISSING + 1))
    fi
  fi
}

check_plugin "ecc@ecc" "ecc" "code 审查链（java-reviewer/security-reviewer）将静默失效"
check_plugin "superpowers@claude-plugins-official" "claude-plugins-official" "流程 skill（brainstorming/systematic-debugging）将静默失效"

echo ""
if [[ "$MISSING" -eq 0 && "$WARN_MISSING" -eq 0 ]]; then
  echo "✅ 插件依赖完整"
  exit 0
elif [[ "$MISSING" -eq 0 ]]; then
  # 只有可选插件缺失：默认通过，仅告警
  echo "⚠️  有 $WARN_MISSING 项可选插件缺失（已降级到本地 agents/ecc-*.md 兜底，不影响流程）"
  echo "   可选恢复: claude plugin marketplace add ecc https://github.com/affaan-m/ECC"
  echo "              claude plugin install ecc@ecc"
  exit 0
elif [[ "$WARN_ONLY" -eq 1 ]]; then
  echo "⚠️  有 $MISSING 项必需插件缺失 + $WARN_MISSING 项可选缺失（--warn 模式，仅告警）"
  echo "   修复: claude plugin marketplace add ecc https://github.com/affaan-m/ECC"
  echo "         claude plugin install ecc@ecc"
  echo "         claude plugin install superpowers@claude-plugins-official"
  exit 0
else
  echo "❌ 有 $MISSING 项必需插件缺失 + $WARN_MISSING 项可选缺失"
  echo "   修复: claude plugin marketplace add ecc https://github.com/affaan-m/ECC"
  echo "         claude plugin install ecc@ecc"
  echo "         claude plugin install superpowers@claude-plugins-official"
  exit 1
fi
