# Project Profile — AIGC Platform Backend

本文件由 `ruoyi-aigc-backend-developer` skill 与项目 `pom.xml` 综合生成。

## 项目身份

- 项目名：AIGC Platfrom Backend（`aigc_platfrom_back`）
- 组织：`org.xywh`
- 版本：5.5.0
- 类型：多模块 Maven / SpringBoot 微服务后端平台

## 技术栈

| 层 | 技术 | 版本 |
| --- | --- | --- |
| 语言 | JDK | 21 |
| 框架 | SpringBoot | 3.5.6 |
| 基座 | RuoYi-Vue-Plus | 5.5.0 |
| ORM | MyBatis-Plus | 3.5.14 |
| 鉴权 | Sa-Token | 1.44.0 |
| 工具 | Hutool | 5.8.40 |
| 缓存/锁 | Redis / Redisson / Lock4j | — |
| 数据库 | MySQL 8.0 + Dynamic-DS 多数据源 | — |
| 文档 | springdoc-openapi | 2.8.13 |
| 定时任务 | snail-job | 1.8.0 |
| 工作流 | warm-flow | 1.8.1 |
| 对象映射 | MapStruct-Plus + Lombok | — |
| OSS | AWS SDK v2 | 2.28.22 |
| 部署 | Docker / Ubuntu 22.04 | — |

## 主要目录

| 路径 | 职责 |
| --- | --- |
| `ruoyi-admin/` | 主应用入口，SpringBoot 启动类 |
| `ruoyi-common/` | 公共模块（25+ 子模块：core/db/redis/web/oss/sms/log/security/…） |
| `ruoyi-modules/ruoyi-aigc/` | **核心业务模块** — AIGC 平台实现 |
| `ruoyi-modules/ruoyi-system/` | 系统管理（用户/角色/菜单/部门） |
| `ruoyi-modules/ruoyi-generator/` | 代码生成器 |
| `ruoyi-modules/ruoyi-job/` | 定时任务模块 |
| `ruoyi-modules/ruoyi-workflow/` | 工作流模块 |
| `ruoyi-extend/` | 扩展：Admin 监控 / snail-job 服务端 |
| `harness-kit/` | Harness 编排与项目配置 |
| `docs/` | 项目文档 |
| `script/` | 部署/运维脚本 |

## 编码规范（来自 `ruoyi-aigc-backend-developer` skill）

1. 分层架构：controller → service → domain → mapper
2. 命名规范：XxxController / IXxxService / XxxServiceImpl / XxxMapper
3. 优先使用 Hutool 及框架原生工具
4. IO 密集操作使用 JDK21 虚拟线程池
5. 关键路径必须加日志，代码必须有注释
6. 业务优先、可读优先、规范优先、落地优先
7. 遵循阿里 Java 规范 + RuoYi 规范

## 绝对禁令

- Controller 中不得写业务逻辑
- 禁止循环 SQL（N+1 查询）
- 禁止空 catch 块
- 禁止泄露敏感信息（密码/密钥/Token）

## 禁区

- 不得修改 RuoYi-Vue-Plus 框架核心代码（`ruoyi-common-core/`、`ruoyi-common-web/` 等公共模块中非项目定制的部分）
- 不得绕过 Sa-Token 鉴权体系
- 不得直接拼接 SQL（使用 MyBatis-Plus 或参数化查询）

## 交付口径

- 代码可直接编译通过（`mvn compile`）
- 遵循本文件编码规范与禁令
- 新增/修改的 Service 方法应有对应注释
- 涉及数据库变更时同步更新对应的 mapper/entity

## 技能关联

本项目的首选编码技能：**`ruoyi-aigc-backend-developer`**（位于 `r1` 技能根）
补充技能（按需）：`test-driven-development`、`refactor-safely`、`systematic-debugging`、`code-review`

## 推断项

> 以下为生成时推断，待人工确认。

- `ruoyi-modules/ruoyi-demo/` 为示例模块，不应修改
- 配置文件位于各模块 `src/main/resources/` 下
- CI/CD 使用 Docker 部署

## codebase-memory 知识图谱

本项目已通过 `DeusData/codebase-memory-mcp` 建立知识图谱索引。

- **索引文件**: `C:/Users/zhoupei/.cache/codebase-memory-mcp/D-work-xinyue-aigc_platfrom_back.db`
- **索引统计**: 30,856 节点 / 108,720 边
- **MCP server**: `config.toml` → `[mcp_servers.codebase_memory]`
- **可用工具**: `search_graph`, `trace_path`, `get_code_snippet`, `query_graph`, `get_graph_schema`, `detect_changes`, `index_status`, `search_code`

查找代码时优先使用 knowledge graph 工具，grep/rg 仅作为回退。
