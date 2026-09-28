# TypeScript 测试规则

## 单元测试
- 使用 Vitest 或 Jest
- 测试文件命名：*.test.ts 或 *.spec.ts
- 测试函数命名：should_<预期>_when_<条件>
- 使用 AAA 模式（Arrange-Act-Assert）

## 测试结构
```typescript
import { describe, it, expect } from 'vitest'
import { add } from './math'

describe('add', () => {
  it('should return sum when given two numbers', () => {
    // Arrange
    const a = 1
    const b = 2
    
    // Act
    const result = add(a, b)
    
    // Assert
    expect(result).toBe(3)
  })
})
```

## Mock 和 Stub
- 使用 vi.mock 或 jest.mock
- Mock 外部依赖（API、数据库）
- 避免过度 Mock
- 使用 vi.fn 创建 Mock 函数

## 覆盖率
- 核心逻辑覆盖率 ≥ 80%
- 工具函数覆盖率 ≥ 90%
- 使用 c8 或 istanbul 生成报告

## 类型测试
- 使用 tsd 或 expect-type 测试类型
- 确保泛型正确推导
- 验证类型错误场景
