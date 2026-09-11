#!/usr/bin/env bash
# init.sh — 在当前目录的项目根建 .harness/ 骨架
# 用法：./init.sh [create|--reset|--verify]
set -euo pipefail

MODE="${1:-create}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATES="$SCRIPT_DIR/templates"
TARGET=".harness"

case "$MODE" in
  --verify)
    echo "=== verifying $TARGET ==="
    if [ ! -d "$TARGET" ]; then echo "FAIL: $TARGET not found"; exit 1; fi
    for f in state/config.md state/MEMORY.md state/state.json state/profile.md; do
      [ -f "$TARGET/$f" ] || echo "MISSING: $TARGET/$f"
    done
    echo "=== done ==="
    ;;
  --reset)
    echo "WARN: --reset 会删除 $TARGET 全部内容（AI 持久状态）"
    read -p "确认 nuke? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then echo "aborted"; exit 1; fi
    rm -rf "$TARGET"
    mkdir -p "$TARGET"
    cp -r "$TEMPLATES/." "$TARGET/"
    echo "=== done; .harness/ 已建（reset） ==="
    ;;
  create|"")
    mkdir -p "$TARGET"
    cp -r "$TEMPLATES/." "$TARGET/"
    echo "=== done; .harness/ 已建 ==="
    ;;
  *)
    echo "usage: $0 [create|--reset|--verify]"; exit 2 ;;
esac