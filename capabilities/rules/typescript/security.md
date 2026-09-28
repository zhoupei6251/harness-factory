# TypeScript 安全规则

## 类型安全
- 启用 strict 模式
- 避免类型断言（as），使用类型守卫
- 外部数据必须验证（zod、io-ts）
- API 响应使用类型安全的 HTTP 客户端（axios + 类型定义）

## 输入验证
- 使用 zod 进行运行时验证
- 表单数据必须验证
- URL 参数必须验证
- 环境变量必须验证

## 依赖安全
- 定期运行 npm audit
- 锁定依赖版本
- 避免使用不维护的库
- 使用 @types/* 提供类型定义

## 敏感信息
- 环境变量存储密钥
- 禁止在代码中硬编码密码
- 日志脱敏处理
- 使用 .env 文件，加入 .gitignore

## XSS 防护
- 避免使用 innerHTML
- 用户输入必须转义
- URL 参数使用 URLSearchParams
- 避免直接拼接 HTML 字符串
