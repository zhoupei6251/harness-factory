# 代码项目示例

Java + Vue 全栈项目接入 harness-foundry 的示例。

## 项目结构

```
my-project/
├── backend/                    # Java 后端
│   ├── src/
│   ├── pom.xml
│   └── ...
├── frontend/                   # Vue 前端
│   ├── src/
│   ├── package.json
│   └── ...
├── harness-foundry/            # AI 协作框架
│   ├── core/
│   ├── rules/code/java/        # Java 规则
│   ├── rules/code/vue/         # Vue 规则
│   ├── rules/common/           # 通用规则
│   ├── contexts/code.md        # 代码场景上下文
│   ├── commands/code.md        # 代码命令
│   ├── hooks/hooks.json        # Hook 配置
│   ├── agents/
│   ├── skills/
│   └── ...
└── MEMORY.md                   # 项目记忆
```

## 接入步骤

### 1. 复制 harness-foundry
```bash
cp -r harness-foundry/ my-project/
```

### 2. 配置技术栈规则
编辑 `harness-foundry/rules/code/java/` 和 `rules/code/vue/`，根据项目需求调整。

### 3. 配置 Hooks
编辑 `harness-foundry/hooks/hooks.json`，启用代码域 Hooks。

### 4. 初始化项目记忆
创建 `MEMORY.md`，记录项目关键信息。

### 5. 开始使用
```bash
cd my-project
# 输入 /code 进入代码开发模式
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `/code` | 进入代码开发模式 |
| `/review` | 代码审查 |
| `/test` | TDD 模式 |
| `/debug` | 调试模式 |

## 注意事项

- 后端和前端可以共用一个 harness-foundry
- 根据技术栈加载对应规则（java/ + vue/）
- 通用规则（common/）始终加载
- 定期更新 MEMORY.md 保持上下文连贯
