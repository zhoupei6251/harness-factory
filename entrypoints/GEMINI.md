# GEMINI.md

项目背景：**aigc_platfrom_back** 是基于 RuoYi-Vue-Plus 5.5.x 的 AIGC 平台后端，Spring Boot 3.5 单体多模块工程（JDK 21、虚拟线程）。核心业务在 `ruoyi-modules/ruoyi-aigc`（任务、短剧、Novel2Script 等），Web 入口 `ruoyi-admin`（端口 8080）；持久化 MyBatis-Plus + MySQL，安全 Sa-Token，缓存 Redis/Redisson。编码约定见 `CODING_CONVENTIONS.md` 与 `.cursor/skills/aigc-platform-rules/`。

## Harness（Gemini）

共享规则正文：**`harness-factory/entrypoints/HARNESS-PLATFORM-ENTRY.md`**（与 `CLAUDE.md` 相同）。

1. 读取上述共享入口 + 根目录 `AGENTS.md`（Harness 覆盖层）
2. **Codex / omx** 多 task 实现：`omx ultrawork` 或 `harness-factory/entrypoints/AGENTS.omx.md`

若本文件与 `AGENTS.md` 冲突，以 `AGENTS.md` 为准。
