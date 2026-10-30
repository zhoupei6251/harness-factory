---
name: hf-debug
description: "定位测试失败、回归和难复现问题；按 Superpowers 的根因调查方法先取证，再修复。"
---

# 根因调试

读取本技能目录内 upstream/SKILL.md，再执行其中调查 → 对照 → 假设 → 修复的步骤。深层调用问题按需读 upstream/root-cause-tracing.md；异步时序按需读 upstream/condition-based-waiting.md。

以当前项目和用户授权为准：已有复现、计划或测试证据直接复用；不自动启动另一套规划、worktree、提交或子 Agent 流程。用已有测试框架验证根因，修复共享调用链。上游 Bash 辅助脚本只在环境支持且确实需要时使用，Windows 优先项目现有命令。
