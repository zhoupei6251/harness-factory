# 小说项目示例

长篇网文项目接入 harness-foundry 的示例。

## 项目结构

```
my-novel/
├── README.md                   # 小说简介
├── 大纲.md                      # 故事大纲
├── 章节目录.md                   # 章节索引
├── 人物设定/
│   ├── 主角.md
│   ├── 配角.md
│   └── 反派.md
├── 章节正文/
│   ├── 第001章_xxx.md
│   └── 第002章_xxx.md
├── 素材库/
│   ├── 情节灵感.md
│   └── 环境描写.md
├── harness-foundry/            # AI 协作框架
│   ├── core/
│   ├── rules/novel/            # 小说规则
│   ├── contexts/novel.md       # 小说场景上下文
│   ├── commands/novel.md       # 小说命令
│   ├── hooks/hooks.json        # Hook 配置
│   ├── agents/
│   ├── skills/
│   └── ...
└── MEMORY.md                   # 项目记忆
```

## 接入步骤

### 1. 初始化小说项目
```bash
bash harness-foundry/scripts/novel-init.sh my-novel
```

### 2. 复制 harness-foundry
```bash
cp -r harness-foundry/ my-novel/
```

### 3. 配置小说规则
编辑 `harness-foundry/rules/novel/`，根据题材调整。

### 4. 配置 Hooks
编辑 `harness-foundry/hooks/hooks.json`，启用小说域 Hooks。

### 5. 创建大纲和人物设定
在 `大纲.md` 和 `人物设定/` 中填写内容。

### 6. 开始创作
```bash
cd my-novel
# 输入 /novel 进入小说创作模式
# 输入 /outline 写大纲
# 输入 /write 写章节
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `/novel` | 进入小说创作模式 |
| `/outline` | 写大纲 |
| `/write` | 写章节 |
| `/evaluate` | 审稿评分 |
| `/polish` | 润色去 AI 味 |

## 注意事项

- 每章写完后自动检查 AI 痕迹
- 定期同步 MEMORY.md 保持连贯性
- 人物设定要及时更新
- 伏笔要记录并追踪
