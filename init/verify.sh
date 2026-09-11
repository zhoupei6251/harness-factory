# verify.sh — .harness/ 完整性检查（也可独立调用）
# 用法：./verify.sh [target=.harness]
set -euo pipefail
TARGET="${1:-.harness}"
FAIL=0

echo "=== verifying $TARGET ==="
for d in state code novel news rendered; do
  if [ ! -d "$TARGET/$d" ]; then echo "MISSING DIR: $TARGET/$d"; FAIL=1; fi
done
for f in state/config.md state/MEMORY.md state/state.json state/profile.md; do
  [ -f "$TARGET/$f" ] || { echo "MISSING FILE: $TARGET/$f"; FAIL=1; }
done
for f in rendered/AGENTS.md rendered/CLAUDE.md rendered/CODEBUDDY.md; do
  [ -f "$TARGET/$f" ] || { echo "MISSING FILE: $TARGET/$f"; FAIL=1; }
done

if [ $FAIL -eq 0 ]; then echo "=== OK: $TARGET 完整 ==="; else echo "=== FAIL ==="; exit 1; fi