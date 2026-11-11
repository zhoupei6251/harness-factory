# CLAUDE.md — aigc_platfrom_back

本文档为 **AI 助手与人类协作者** 提供本仓库的上下文：技术栈、目录、构建方式与编码约定。修改代码前请先阅读本节，并保持与现有风格一致。

## 项目是什么

- **名称**: `aigc_platfrom_back`（Maven `artifactId`），**groupId**: `org.xywh`，**版本**: `${revision}` → 当前 **5.5.0**（见根 `pom.xml`）。
- **定位**: 基于 **RuoYi-Vue-Plus（Dromara）5.5.x** 的 **AIGC 平台后端**，Spring Boot 单体多模块工程。
- **入口应用**: `ruoyi-admin` 模块，主类 `org.xywh.DromaraApplication`。
- **默认 HTTP**: 端口 `8080`，`context-path: /`（见 `ruoyi-admin/src/main/resources/application.yml`）。
- **业务包根路径**: `org.xywh`；AIGC 业务主要在 `org.xywh.aigc`。

## 技术栈（摘要）

| 类别 | 说明 |
|------|------|
| 语言 / 运行时 | Java **21**（`spring.threads.virtual.enabled: true`） |
| 框架 | Spring Boot **3.5.6** |
| Web 容器 | Undertow |
| 持久化 | **MyBatis-Plus 3.5.x**，MySQL（驱动在 `ruoyi-admin`） |
| 安全 | **Sa-Token 1.44.x** |
| 缓存 / 锁 | Redis、**Redisson**、Lock4j |
| 对象映射 | **MapStruct-Plus**（`MapstructUtils`） |
| 工具库 | **Hutool 5.8.x** |
| API 文档 | SpringDoc（OpenAPI），路径见 `application.yml` 中 `springdoc` |
| 任务调度 | SnailJob（扩展模块 `ruoyi-snailjob-server`） |
| 工作流 | warm-flow **1.8.x**（`ruoyi-workflow`） |
| 多租户 / 多数据源 | `ruoyi-common-tenant`、dynamic-datasource |
| 对象存储 | AWS SDK S3 兼容（`ruoyi-common-oss`） |

版本与依赖以根 **`pom.xml`** 的 `properties`、`dependencyManagement` 及 **`${revision}`** 为权威来源；勿在文档中硬编码会过期的次要版本号。

## 仓库结构

```
aigc_platfrom_back/
├── ruoyi-admin/              # Web 启动、聚合运行配置（application-*.yml）
├── ruoyi-common/             # 公共能力（见下表）
├── ruoyi-modules/            # 业务模块
│   ├── ruoyi-aigc/           # ★ AIGC 核心业务
│   ├── ruoyi-system/         # 系统管理（用户、角色、菜单等）
│   ├── ruoyi-workflow/       # 工作流
│   ├── ruoyi-job/            # 定时 / SnailJob 客户端
│   ├── ruoyi-generator/      # 代码生成
│   └── ruoyi-demo/           # 示例
├── ruoyi-extend/             # 独立部署的扩展服务
│   ├── ruoyi-monitor-admin/  # Spring Boot Admin 监控
│   └── ruoyi-snailjob-server/
├── script/                   # SQL 脚本、Docker、Jenkins、启动脚本
├── .cursor/skills/           # Cursor 技能（如 aigc-platform-rules）
├── CLAUDE.md                 # 本文件：项目鸟瞰
├── CODING_CONVENTIONS.md     # 编码习惯（须遵守）
└── pom.xml                   # 父 POM
```

### `ruoyi-common` 子模块（按需引用）

| 模块 | 职责 |
|------|------|
| `ruoyi-common-core` | 核心工具、`R`、`ServiceException`、校验分组 |
| `ruoyi-common-web` | `BaseController`、Undertow、全局 Web 配置 |
| `ruoyi-common-mybatis` | `BaseMapperPlus`、`PageQuery`、`TableDataInfo` |
| `ruoyi-common-satoken` / `security` | 登录、权限、安全过滤 |
| `ruoyi-common-redis` | 缓存、分布式锁 |
| `ruoyi-common-log` | `@Log` 操作日志 |
| `ruoyi-common-oss` / `sms` / `mail` | 对象存储、短信、邮件 |
| `ruoyi-common-tenant` | 多租户 |
| `ruoyi-common-json` / `excel` / `encrypt` | JSON、导入导出、加解密 |
| 其他 | `doc`、`idempotent`、`ratelimiter`、`sse`、`websocket` 等 |

### `ruoyi-aigc` 包结构（改业务时优先看这里）

```
org.xywh.aigc/
├── basic/          # 通用 AIGC：任务、项目、分镜、小说、聊天、提示词模板、第三方 API
│   ├── controller/   # 路由前缀多为 /aigc/*
│   ├── service/      # I*Service + *ServiceImpl（直接注入 Mapper，非 MyBatis ServiceImpl 基类）
│   ├── service/api/  # 第三方模型调用（ThirdPartyApiManager、*ApiServiceImpl）
│   ├── mapper/
│   ├── domain/       # 实体；domain/bo、vo、dto
│   ├── enums/、strategy/、helper/
├── drama/          # 短剧 / 分集 / 镜头 / 角色等业务
├── n2s/            # Novel2Script 读接口（`aigc_n2s_*`，`/aigc/n2s/**`）
├── config/         # AIGC 专用配置、线程池（含虚拟线程池）
├── job/            # 异步任务、缩略图等
├── utils/、constants/
└── resources/
    ├── prompts/    # LLM 提示词 Markdown（见 CODING_CONVENTIONS.md）
    └── mapper/aigc/{basic|drama|n2s}/*.xml
```

## 配置与环境

| 用途 | 路径 |
|------|------|
| 主配置 | `ruoyi-admin/src/main/resources/application.yml` |
| 环境配置 | `application-dev.yml` / `application-test.yml` / `application-prod.yml` |
| Maven 环境 | 根 `pom.xml` 的 profile：`dev`（默认）、`test`、`prod` → 过滤为 `@profiles.active@` |
| AIGC 业务配置 | `ruoyi-modules/ruoyi-aigc` 内 `config` 包及对应 yml（若有） |
| 日志 | `classpath:logback-plus.xml`，包 `org.xywh` 级别由 Maven 属性注入 |

**安全**：禁止将真实密码、API Key、私钥写入仓库；使用 profile、占位符或部署环境变量。

## 数据库与脚本

- **框架基线 SQL**: `script/sql/ry_vue_5.X.sql` 及 `ry_job.sql`、`ry_workflow.sql` 等。
- **AIGC 业务表**: `script/sql/aigc_drama.sql` 等（以 `script/sql/` 下实际文件为准）。
- **版本升级脚本**: `script/sql/update/`。
- **Docker / CI**: `script/docker/`（`test`、`prod` 环境）、`script/bin/ry.sh` / `ry.bat`。

## 构建与运行

在项目根目录执行（需本机 **JDK 21**、**Maven**）：

```bash
# 编译打包（根 POM 默认 skipTests=true）
mvn clean package

# 仅编译
mvn compile

# 跑单元测试（须显式关闭跳过）
mvn test -DskipTests=false

# 回归门禁：只跑 *GuardTest / *RegressionTest（手动/CI 执行，不挂 pre-push）
script/bin/guard-tests.sh
```

运行主应用：

```bash
cd ruoyi-admin
mvn spring-boot:run
```

开发时也可在 IDE 中直接运行 `DromaraApplication`。环境通过 **Spring profile** 切换，与 Maven profile 及 `application-{profile}.yml` 对应。

## 常见改动入口（给 AI）

| 需求 | 建议先看 |
|------|----------|
| 新增 / 修改 HTTP 接口 | 同模块现有 `*Controller` → `I*Service` → `*Mapper` |
| 任务、生成、历史记录 | `basic/controller/AigcTaskController`、`AigcTaskServiceImpl` |
| 调用大模型 / 画图 / 视频 API | `basic/service/api/`、`ThirdPartyApiManager` |
| 修改 LLM 提示词 | `resources/prompts/` + 引用该文件的 Java（`ClassPathResource` / `ResourceUtil`） |
| 短剧 / 镜头 / 分集 | `drama/` 包下 controller / service |
| Novel2Script（`aigc_n2s_*`） | `org.xywh.aigc.n2s` 包、`/aigc/n2s/**`；表已对齐 RuoYi 审计字段（`N2sTenantEntity` + `del_flag`）；**章节序号全链路 1-based**（第一章 = 1，见 `CODING_CONVENTIONS.md`）；集成测试 `org.xywh.aigc.test.n2s.N2sReadTest`（`AigcTestRunner` 选项 7） |
| 权限、登录用户 | `LoginHelper`、`@SaCheckPermission`（与 `ruoyi-system` 菜单权限码一致） |
| 多租户上下文 | `TenantHelper`、`TenantEntity` 子类实体 |

## 编码约定（硬约束摘要）

1. **最小改动**：只改完成任务所需的文件与行。
2. **对齐现有模式**：详见 **`CODING_CONVENTIONS.md`**（Controller / Service / Mapper / 领域对象 / 日志 / 提示词等）。
3. **复用公共模块**：优先 `ruoyi-common` 已有能力，不重复造轮子。
4. **Controller 不写业务**：编排与校验在 Web 层，业务在 Service。
5. **阻塞 IO**：JDK 21 下优先虚拟线程（与 `application.yml`、`AigcTaskThreadPoolConfig` 等现有用法一致）。
6. **防复发**：`fix` 提交必须新增或修改 `*GuardTest` / `*RegressionTest`（`@Tag("local")` 必带）；无法断言的约束登记到 **`docs/traps.md`**。改既有逻辑前先读该文件相关行。详见 `CODING_CONVENTIONS.md`「Bug 修复与防复发」。

## 文档与工具链关系

| 文件 | 用途 |
|------|------|
| **`CLAUDE.md`**（本文件） | 项目级鸟瞰：结构、配置、入口索引 |
| **`CODING_CONVENTIONS.md`** | 本仓库必须遵守的编码习惯（实现时以同模块现有类为准） |
| **`docs/traps.md`** | 本项目「踩过一次、别改回去」的陷阱表；改既有逻辑前先读相关行 |
| **`.cursor/skills/aigc-platform-rules/SKILL.md`** | Cursor 技能：技术栈、禁令、自检清单 |
| **`.cursor/rules/*.mdc`** | 若存在，为编辑器按文件类型附加的规则片段 |

**冲突时**：以 **仓库内实际代码风格** 为准；改完对照 `CODING_CONVENTIONS.md` 自检。

若使用其他支持「项目说明文件」的工具，可将本文件配置为仓库根 `CLAUDE.md`，或将要点复制到该工具要求的文件名。

## Harness Factory（code 域）

本项目使用仓库内 `harness-factory/`（本机目录，已在 `.gitignore`）作为 code 域开发工作流框架。旧版 `harness-foundry` / `harness-kit` 已废弃删除，勿再引用。

### 核心流程

```
想法 → brainstorming → 设计批准 → writing-plans → 实现 → 审查 → 完成
```

### 意图路由（首句声明）

| 用户意图 | 动作 |
|---------|------|
| 设计、方案、架构 | brainstorming → 写 spec → **暂停等确认** |
| 计划、拆分任务 | writing-plans → 写 plan → **暂停等确认** |
| 开始实现、并行实现 | 拆 WU → 并行派发（≤5 Worker） |
| quick-fix、小改动 | Leader 直改，不派兵 |
| 审查、review | requesting-code-review |
| 测试、TDD | test-driven-development |
| 调试 bug | systematic-debugging |
| Git 操作 | git-xywh |

### 阶段门禁（不可跳过）

1. **spec/plan 写完后** → 必须暂停，等用户「批准/开始实现」
2. **实现完成后** → 进入尾盘（测试 + 审查）
3. **小改动** → 可直接处理，但须遵守 NEVER.md

### 必读文件

| 文件 | 说明 |
|------|------|
| `harness-factory/rules/NEVER.md` | 硬性禁止清单 |
| `harness-factory/guides/intent-routing.md` | 意图路由表 |
| `harness-factory/guides/routing.md` | 路由与运行时细则 |
| `harness-factory/ENTRY.md` | 统一入口（治理文档索引） |
| `harness-factory/references/traps.md` | 已知陷阱（踩坑后追加） |

### 核心 Skills（code 域）

| Skill | 命令 | 何时用 |
|-------|------|--------|
| brainstorming | `/skill brainstorming` | 设计新功能 |
| writing-plans | `/skill writing-plans` | 制定实施计划 |
| test-driven-development | `/skill test-driven-development` | TDD 开发 |
| systematic-debugging | `/skill systematic-debugging` | 调试 bug |
| requesting-code-review | `/skill requesting-code-review` | 代码审查 |
| verification-before-completion | `/skill verification-before-completion` | 交付前验证 |
| claude-orchestration | `/skill claude-orchestration` | 并行多 task 编排 |

### 禁用约束

- ❌ 不经设计直接实现复杂功能
- ❌ spec/plan 未批准就实现
- ❌ 提交未审查的代码
- ❌ 硬编码 secrets（使用环境变量）
- ❌ 自动运行 `mvn` / 启动项目（验证命令仅列出供用户手动执行）

---

### 文档优先级

`harness-factory/guides/routing.md` § 阶段门禁 > `harness-factory/rules/NEVER.md` > `harness-factory/ENTRY.md` > 本文件一般章节 > `CODING_CONVENTIONS.md`。
