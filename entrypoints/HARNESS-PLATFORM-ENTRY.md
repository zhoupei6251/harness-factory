# Harness Platform Entry（Claude / Gemini 共享）

项目背景：**aigc_platfrom_back** 是基于 RuoYi-Vue-Plus 5.5.x 的 AIGC 平台后端，Spring Boot 3.5 单体多模块工程（JDK 21、虚拟线程）。核心业务在 `ruoyi-modules/ruoyi-aigc`（任务、短剧、Novel2Script 等），Web 入口 `ruoyi-admin`（端口 8080）；持久化 MyBatis-Plus + MySQL，安全 Sa-Token，缓存 Redis/Redisson。编码约定见 `CODING_CONVENTIONS.md` 与 `.cursor/skills/aigc-platform-rules/`。

> Claude/Gemini 会话须同时读根目录 **`AGENTS.md`**（Harness 覆盖层优先）。

---

## Harness 规则（强制）

本项目使用 `harness-factory/` 工程标准。

### 任务前（与 `AGENTS.md` 覆盖层对齐）

1. `harness-factory/core/harness.md`
2. `harness-factory/project/profile.md`
3. `harness-factory/context-map.md`
4. `harness-factory/project/git.md`（Git 任务或用户要求提交 / 开 MR 时）
5. `harness-factory/core/routing.md`（路由、阶段门禁、小改动判定）
6. `harness-factory/core/artifacts.md`
7. `harness-factory/project/verification.md`
8. `harness-factory/core/verification.md`
9. 任务匹配时：`harness-factory/core/runbooks.md`

### 约束

- **强制声明：** 回复第一行须为 `「Harness：<route 或 "小改动，直接处理">」`
- **未声明时：** 读取根目录 `CLAUDE.md` 或 `GEMINI.md` 与 `harness-factory/core/routing.md` 后重试
- 非琐碎任务前声明路由、技能与来源；完成声明须附验证证据
- 用户指定 skill 为附加项，不替代默认 route（除非用户明确排除）

若与根目录 `AGENTS.md` 冲突，以 `AGENTS.md` 为准。
