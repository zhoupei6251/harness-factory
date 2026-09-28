# Java Hooks

## PreToolUse

### 编译检查
- 触发：Edit/Write *.java
- 行为：运行 `mvn compile -q` 或 `gradle build -x test`
- 目的：确保语法正确，避免编译错误

### 代码格式化
- 触发：Edit/Write *.java
- 行为：运行 `mvn spotless:apply` 或 `gradle spotlessApply`
- 目的：统一代码风格（Google Java Format 或自定义）

## PostToolUse

### 单元测试
- 触发：Edit/Write *Test.java
- 行为：运行对应测试类 `mvn test -Dtest=ClassName`
- 目的：确保测试通过，避免回归

### 依赖检查
- 触发：Edit pom.xml / build.gradle
- 行为：运行 `mvn dependency:tree` 或 `gradle dependencies`
- 目的：检查依赖冲突和版本问题

## Stop

### 代码质量
- 触发：每次响应结束
- 行为：运行 Checkstyle / SpotBugs / PMD
- 目的：检查代码规范、潜在 bug、复杂度

### 测试覆盖率
- 触发：修改 Service 层代码后
- 行为：运行 JaCoCo 生成覆盖率报告
- 目的：确保覆盖率 ≥ 80%
