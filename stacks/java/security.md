# Java 安全规则

## 输入验证
- 所有外部输入必须校验（@Valid + @Validated）
- 字符串长度限制：name ≤ 100，description ≤ 1000
- 数字范围校验：age 0-150，price ≥ 0
- 文件上传：限制类型（白名单）和大小（≤ 10MB）

## SQL 注入防护
- MyBatis 使用 #{param}，禁止 ${param}
- 动态 SQL 使用 <if> <where> 标签，避免字符串拼接
- JPA/Hibernate 使用参数绑定，禁止字符串拼接

## 权限控制
- 接口必须加权限注解（@PreAuthorize 或自定义注解）
- 数据权限：查询必须带租户 ID 或用户 ID，防止越权
- 敏感操作（删除、修改）必须校验资源归属
- 管理员接口使用独立 Controller，禁止混用

## 敏感信息
- 日志禁止打印密码、token、身份证号
- 配置文件使用环境变量或配置中心，禁止明文密码
- 响应体禁止返回密码、盐值等敏感字段
- 使用 @JsonIgnore 或 DTO 过滤敏感字段

## 依赖安全
- 定期扫描依赖漏洞（OWASP Dependency-Check）
- 禁止使用已废弃的 API（如 MD5、SHA1 做密码哈希）
- 密码使用 BCrypt 或 Argon2
- HTTPS 强制，禁止 HTTP 明文传输
