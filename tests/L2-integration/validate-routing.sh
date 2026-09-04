#!/bin/bash
# L2 Integration: Routing 完整性检查
# 验证 intent-routing.md 中所有引用路径不存在死链接

FOUNDRY_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
ROUTING_FILE="$FOUNDRY_DIR/core/intent-routing.md"
ISSUES=0

echo "=== L2-Integration: Routing 完整性 ==="

if [ ! -f "$ROUTING_FILE" ]; then
    echo "  ❌ intent-routing.md not found"
    exit 1
fi

# 提取所有引用的文件路径
echo ""
echo "--- 引用完整性 ---"

check_ref() {
    local ref="$1"
    local desc="$2"
    # 移除行内代码标记
    ref=$(echo "$ref" | sed 's/`//g')
    local full_path="$FOUNDRY_DIR/$ref"
    if [ -f "$full_path" ] || [ -d "$full_path" ]; then
        echo "  ✅ $desc → $ref"
    else
        echo "  ❌ $desc → $ref (不存在)"
        ISSUES=$((ISSUES + 1))
    fi
}

# core 引用
check_ref "core/NEVER.md" "NEVER 清单"
check_ref "core/orchestration/dispatcher-workflow.md" "调度器工作流"
check_ref "core/orchestration/domain-config.yaml" "域编排配置"
check_ref "core/orchestration/skill-preferences.md" "技能偏好路由"
check_ref "core/orchestration/execution-context/provider-protocol.md" "execution-context 协议 (P0-1)"
check_ref "core/capabilities/registry.md" "capability 注册表"
check_ref "core/principles.md" "核心原则"

# hooks 引用（2026-09 phase-2 删除 hooks/guardrails/，改走 skills/agent-shield/SKILL.md fallback）
# check_ref "hooks/guardrails/guardrail-config.json" "guardrail 配置 (P0-2)"

# tracking 引用
check_ref "core/orchestration/tracking/schema.md" "追踪 schema"

echo "--- tactical 引用 ---"
# tactical 层技能 (codebase-memory / ripgrep / LSP 三层栈)
check_ref "core/intelligence/tactical/_config.yaml" "tactical 配置 (codebase-memory + ripgrep + LSP)"
check_ref "skills/ripgrep-search/SKILL.md" "ripgrep-search 技能"
check_ref "skills/lsp-query/SKILL.md" "lsp-query 技能"
check_ref "skills/code-insight-stack/SKILL.md" "code-insight-stack 编排"


echo ""
if [ "$ISSUES" -gt 0 ]; then
    echo "❌ Routing 完整性: $ISSUES dead links found"
    exit 1
else
    echo "✅ Routing 完整性检查通过"
fi
