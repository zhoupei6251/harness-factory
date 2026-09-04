#!/bin/bash
# L1 Static: NEVER.md 规则可检测性检查
# 验证 NEVER.md 中的规则是否可被 guardrail/agent 检测

FOUNDRY_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
NEVER_FILE="$FOUNDRY_DIR/core/NEVER.md"
ISSUES=0

echo "=== L1-Static: NEVER.md 规则可检测性 ==="

if [ ! -f "$NEVER_FILE" ]; then
    echo "  ❌ NEVER.md not found"
    exit 1
fi

# 统计规则数量
rule_count=$(grep -c "^\- 🚫" "$NEVER_FILE" 2>/dev/null || echo 0)
echo "  NEVER 规则总数: $rule_count"

# 检查是否有明确的可检测模式
detectable=0
undetectable=0

# 每条规则应有关键词用于 pattern match
while IFS= read -r line; do
    if echo "$line" | grep -q "^\- 🚫"; then
        # 提取规则内容
        rule=$(echo "$line" | sed 's/.*🚫 //')
        # 检查规则中是否包含可搜索的关键词
        if echo "$rule" | grep -qE "(禁止|不得|不能|必须|应|不可)"; then
            detectable=$((detectable + 1))
        else
            undetectable=$((undetectable + 1))
        fi
    fi
done < "$NEVER_FILE"

echo "  可检测规则: $detectable"
echo "  难以自动检测: $undetectable"

# 检查 guardrail-config.json 是否覆盖了 NEVER 规则
# 2026-09 phase-2: hooks/guardrails/ 已删除；guardrail 覆盖检查迁移到
# skills/agent-shield/SKILL.md 的"配置 fallback"段
GUARDRAIL_CONFIG="$FOUNDRY_DIR/hooks/guardrails/guardrail-config.json"
if [ -f "$GUARDRAIL_CONFIG" ]; then
    echo ""
    echo "--- Guardrail 覆盖检查 ---"
    # 检查几个关键 NEVER 规则是否在 guardrail 中有对应
    checks=(
        "shell.*文本文件:shell 写文本文件"
        "静默吞错误:静默吞错误不报告"
        "自动 push:自动 push"
        "自动 commit:自动 commit"
        "未声明 Route:未声明 Route"
        "AI 味写作:AI 味写作"
    )

    for check in "${checks[@]}"; do
        key="${check%%:*}"
        desc="${check##*:}"
        if grep -q "$key" "$GUARDRAIL_CONFIG" 2>/dev/null; then
            echo "    ✅ $desc"
        else
            echo "    ⚠️  $desc — 未被 guardrail 覆盖"
        fi
    done
fi

echo ""
echo "✅ NEVER.md 可检测性检查完成"
