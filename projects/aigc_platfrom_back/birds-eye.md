# 项目鸟瞰 — aigc_platfrom_back

基于 **RuoYi-Vue-Plus 5.5.x** 的 **AIGC 平台后端**，Spring Boot 单体多模块工程。
入口 `org.xywh.DromaraApplication`（`ruoyi-admin` 模块），默认端口 8080；AIGC 业务包根 `org.xywh.aigc`。
完整说明见同目录 `CLAUDE.md`，编码习惯见 `CODING_CONVENTIONS.md`。

## 技术栈

- Java 21（虚拟线程已开）、Spring Boot 3.5.6、Undertow
- MyBatis-Plus + MySQL、Redis / Redisson、Sa-Token
- MapStruct-Plus、Hutool；对象存储走 S3 兼容 SDK

## 目录结构

```
ruoyi-admin/        # Web 启动、application-*.yml
ruoyi-common/       # core / web / mybatis / satoken / redis / log / oss / tenant ...
ruoyi-modules/
  ruoyi-aigc/       # ★ AIGC 核心：basic(任务/项目/分镜/第三方API)、drama、n2s
  ruoyi-system/     # 用户、角色、菜单
  ruoyi-workflow/   # warm-flow
ruoyi-extend/       # monitor-admin、snailjob-server
script/             # SQL、Docker、Jenkins
```

## 关键约定

- 最小改动，对齐同模块现有 Controller → Service → Mapper 风格；Controller 不写业务
- 复用 `ruoyi-common` 已有能力，不重复造轮子
- 阻塞 IO 用虚拟线程；禁止把密码 / API Key / 私钥写进仓库
- 验证命令只列出供人工执行，不自动跑 `mvn` 或启动服务
