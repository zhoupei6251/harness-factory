# TypeScript 编码模式

## 核心原则
- 严格模式（strict: true）
- 优先使用 interface 定义对象类型
- 避免 any，使用 unknown 或具体类型
- 优先使用 const 和 let，禁止 var

## 类型系统
```typescript
// 正确：使用 interface
interface User {
  id: number
  name: string
  email?: string
}

// 正确：使用 type 定义联合类型
type Status = 'pending' | 'active' | 'inactive'

// 错误：使用 any
const data: any = fetchData()

// 正确：使用 unknown
const data: unknown = fetchData()
if (typeof data === 'object' && data !== null) {
  // 类型守卫
}
```

## 函数设计
- 参数和返回值必须标注类型
- 使用泛型提高复用性
- 避免函数超过 50 行
- 使用可选参数和默认值

## 异步编程
- 使用 async/await 而非 Promise.then
- 错误处理使用 try-catch
- 并发请求使用 Promise.all
- 避免回调地狱

## 代码组织
- 使用 ES6 模块（import/export）
- 文件命名：kebab-case（user-card.ts）
- 类命名：PascalCase（UserCard）
- 常量大写：UPPER_SNAKE_CASE
