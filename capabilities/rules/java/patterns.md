# Java 编码模式

## 编码标准基准（所有 Java 代码）

每段代码必须同时满足三套标准，`harness-java-reviewer` 审查按此验收（若 ecc 插件已装可走 `spawn ecc:java-reviewer`，缺失回退到本地 `agents/ecc-java-reviewer.md`）：

- **Alibaba Java Coding Guidelines** — 阿里巴巴 Java 开发手册（命名、常量、集合、并发、异常、日志、安全规约）
- **Google Java Style** — 4 空格缩进、行宽 120、导入顺序、空白规则
- **Clean Code** — 命名自解释、单一职责、依赖清晰、消除重复

### 禁止（硬性拦截，违反即打回重构）

| 禁止项 | 判定标准 |
|--------|----------|
| 巨型方法 | 方法体 > 60 行；或嵌套 ≥ 3 层、多出口 return |
| 巨型 Controller | > 300 行；或单方法混编业务编排 + 持久化 + 外部调用 |
| Service 超长 | `*ServiceImpl` 单文件 > 1000 行；或单方法 > 60 行 |
| 重复代码 | 同段逻辑出现 2 处以上（抽取私有方法/工具类） |
| 隐式异常 | 空 catch、吞异常不记日志、catch 后静默继续、不抛不滚 |
| 魔法数字 | 业务含义裸数字/裸字符串；必须提取常量/枚举并注释含义 |

### 必须（审查检查项）

1. **清晰命名** — 类/方法/变量自解释；布尔返回用 `is/has/can`；禁止拼音与歧义缩写
2. **单一职责** — 一个方法只做一件事；Controller 编排 / Service 业务 / Mapper 持久化
3. **完整异常处理** — 可预期失败抛 `ServiceException`；catch 记录类型与堆栈；finally 释放资源
4. **日志规范** — `@Slf4j`，关键路径记录业务标识与分支决策；禁打密钥/Token/证件号；高频循环禁刷屏
5. **并发安全** — 共享状态线程安全；跨线程上下文用线程内传递（如 `TenantHelper.dynamicLocal`）；禁无界线程池

## 核心原则
- 优先使用不可变对象（final + record）
- 避免 null，使用 Optional 或 @Nullable
- 优先组合而非继承
- 异常处理：要么处理，要么上抛，禁止吞异常

## Spring Boot 模式
- Controller 只做参数校验和路由，业务逻辑在 Service
- 使用 @Transactional 管理事务，避免在 Controller 层开启
- 异步任务使用 @Async + CompletableFuture，注意事务传播
- 配置类使用 @ConfigurationProperties，避免 @Value 散落

## 并发模式
- 优先使用 ConcurrentHashMap、AtomicInteger 等并发集合
- 分布式锁使用 Redisson，避免自己实现
- 线程池使用 ThreadPoolExecutor，禁止 Executors.newFixedThreadPool
- 虚拟线程场景避免 synchronized，改用 ReentrantLock

## 数据访问
- MyBatis 使用 #{param}，禁止 ${param} 防 SQL 注入
- 分页使用 PageHelper 或游标分页，避免深分页 LIMIT offset
- 批量操作使用 batch insert/update，避免循环单条
- 事务内避免 RPC 调用，防止长事务

## 代码组织
- 包结构：controller / service / repository / model / config / util
- Service 类不超过 1000 行，超过则拆分
- 工具类使用静态方法，禁止实例化（private constructor）
- 常量使用 enum 或 static final，禁止魔法值
