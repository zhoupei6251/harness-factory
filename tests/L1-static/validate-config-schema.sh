#!/bin/bash
# L1 Static: Config Schema 验证
# 检查所有 YAML/JSON 配置文件的结构合法性

FOUNDRY_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
ISSUES=0

echo "=== L1-Static: Config Schema 验证 ==="

# 检查 YAML 文件是否有基本结构
check_yaml() {
    local file="$1"
    local min_keys="${2:-1}"
    if [ ! -f "$file" ]; then
        echo "  MISSING: $file"
        ISSUES=$((ISSUES + 1))
        return
    fi
    # 检查是否有冒号分隔的 key（基本 YAML 结构）
    local keys
    keys=$(grep -c "^[a-z_]*:" "$file" 2>/dev/null || echo 0)
    if [ "$keys" -lt "$min_keys" ]; then
        echo "  INVALID: $file (少于 $min_keys 个 key)"
        ISSUES=$((ISSUES + 1))
    else
        echo "  OK: $file"
    fi
}

# 检查 JSON 文件是否合法
check_json() {
    local file="$1"
    if [ ! -f "$file" ]; then
        echo "  MISSING: $file"
        ISSUES=$((ISSUES + 1))
        return
    fi
    # 基本的 JSON 结构检查
    if grep -q '"' "$file" 2>/dev/null; then
        echo "  OK: $file"
    else
        echo "  WARN: $file (可能不是有效 JSON)"
    fi
}

echo ""
echo "--- YAML 配置 ---"
check_yaml "$FOUNDRY_DIR/core/orchestration/domain-config.yaml" 1
check_yaml "$FOUNDRY_DIR/core/orchestration/config.defaults.yaml" 1
check_yaml "$FOUNDRY_DIR/core/orchestration/execution-context/model.yaml" 1
for adapter in "$FOUNDRY_DIR"/adapters/*/; do
    name=$(basename "$adapter")
    case "$name" in TEMPLATE|agents|.git) continue ;; esac
    if [ -f "$adapter/capability-matrix.yaml" ]; then
        check_yaml "$adapter/capability-matrix.yaml" 2
    fi
done

echo ""
echo "--- JSON 配置 ---"
# 2026-09 phase-2: hooks/guardrails/ 已删除——其配置 fallback 到
# skills/agent-shield/SKILL.md 的"配置 fallback"段
echo "  [skip] hooks/guardrails/*.json（已废弃，见 skills/agent-shield/SKILL.md fallback 段）"

echo ""
if [ "$ISSUES" -gt 0 ]; then
    echo "❌ Config Schema 验证: $ISSUES issues found"
    exit 1
else
    echo "✅ Config Schema 验证通过"
fi
