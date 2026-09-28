# TypeScript Hooks

## PreToolUse

### 类型检查
- 触发：Edit/Write *.ts *.tsx
- 行为：运行 `tsc --noEmit`
- 目的：确保类型正确

### 代码格式化
- 触发：Edit/Write *.ts *.tsx
- 行为：运行 `prettier --write`
- 目的：统一代码风格

## PostToolUse

### ESLint 检查
- 触发：Edit/Write *.ts *.tsx
- 行为：运行 `eslint --fix`
- 目的：检查代码规范

### 单元测试
- 触发：Edit/Write *.test.ts *.spec.ts
- 行为：运行 `vitest run`
- 目的：确保测试通过

## Stop

### 构建检查
- 触发：修改核心代码后
- 行为：运行 `tsc` 或 `npm run build`
- 目的：确保构建成功

### 依赖检查
- 触发：修改 package.json 后
- 行为：运行 `npm audit`
- 目的：扫描依赖漏洞
