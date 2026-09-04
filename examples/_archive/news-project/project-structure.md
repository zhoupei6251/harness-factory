# 新闻项目示例

新闻采编项目接入 harness-foundry 的示例。

## 项目结构

```
my-news/
├── README.md                   # 项目简介
├── 选题库/
│   ├── 热点追踪.md
│   └── 选题计划.md
├── 稿件/
│   └── <稿件名>.md
├── 素材库/
│   ├── 参考资料/
│   └── 数据源.md
├── harness-foundry/            # AI 协作框架
│   ├── core/
│   ├── rules/news/             # 新闻规则
│   ├── contexts/news.md        # 新闻场景上下文
│   ├── commands/news.md        # 新闻命令
│   ├── hooks/hooks.json        # Hook 配置
│   ├── agents/
│   ├── skills/
│   └── ...
└── MEMORY.md                   # 项目记忆
```

## 接入步骤

### 1. 初始化新闻项目
```bash
bash harness-foundry/scripts/news-init.sh my-news
```

### 2. 复制 harness-foundry
```bash
cp -r harness-foundry/ my-news/
```

### 3. 配置新闻规则
编辑 `harness-foundry/rules/news/`，根据定位调整。

### 4. 配置 Hooks
编辑 `harness-foundry/hooks/hooks.json`，启用新闻域 Hooks。

### 5. 开始采编
```bash
cd my-news
# 输入 /news 进入新闻采编模式
# 输入 /hot 追踪热点
# 输入 /fact 事实核查
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `/news` | 进入新闻采编模式 |
| `/hot` | 热点追踪 |
| `/fact` | 事实核查 |
| `/brief` | 生成日报 |

## 注意事项

- 事实核查是核心环节，不可省略
- 信源要标注清楚
- 敏感话题需法务审核
- 定期更新热点追踪记录
