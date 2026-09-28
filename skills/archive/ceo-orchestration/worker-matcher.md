---
name: ceo-worker-matcher
description: "Worker 经验学习匹配 — CEO 基于历史绩效和领域标签推荐最佳 Worker"
---

# Worker Matcher（Worker 经验学习匹配）

## 激活条件

- CEO 生成 `handoff/ceo-task.md` 时自动调用
- 用户说 "推荐 Worker" 时触发
- S-2 新增子 Skill

## 工作流程

### 1. 提取任务标签

从任务描述中提取领域关键词：
```
"写一本修仙小说" → ["修仙", "小说", "写作"]
"修一个 Java 空指针 bug" → ["Java", "bugfix", "后端"]
```

### 2. 查询 Worker 标签

从 `performance/worker-stats.json` 读取每个 Worker 的历史标签和成功率。

### 3. 计算匹配度

```javascript
function matchScore(taskTags, worker) {
  // Jaccard 相似度
  const taskSet = new Set(taskTags);
  const workerSet = new Set(Object.keys(worker.tags || {}));
  const intersection = [...taskSet].filter(t => workerSet.has(t));
  const union = new Set([...taskSet, ...workerSet]);

  const jaccard = union.size === 0 ? 0 : intersection.length / union.size;

  // 标签内成功率加权
  let tagWeight = 0;
  intersection.forEach(tag => {
    tagWeight += worker.tags[tag] || 0.5;
  });
  const avgTagWeight = intersection.length > 0 ? tagWeight / intersection.length : 0.5;

  // 综合得分: Jaccard * 0.4 + 标签权重 * 0.3 + 成功率 * 0.3
  return jaccard * 0.4 + avgTagWeight * 0.3 + (worker.success_rate || 0.5) * 0.3;
}
```

### 4. 输出推荐

```markdown
## Worker 推荐

任务: 写一本修仙小说
推荐 Worker:
1. Writer (匹配度: 0.92) — 修仙标签成功率 95%，总成功率 90%
2. NovelWriter (匹配度: 0.85) — 小说标签成功率 88%

建议: 派发给 Writer
```

## 标签更新

每次 WU 完成后，Domain Leader 在 `handoff/<domain>-result.md` 中标记 tag：

```markdown
## Worker 绩效
- Writer: WU=1, success=1, rework=0, tags=修仙,小说
```

CEO 读取后更新 Worker 的标签成功率。

## 输出

更新 `performance/worker-stats.json` 的 `tags` 和匹配记录字段。

## 关联

- 数据源：`performance/worker-stats.json`
- 匹配算法：Jaccard 相似度 + 标签成功率加权
- 绩效分析：performance-analyst Skill
