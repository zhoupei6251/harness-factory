# evals/ — 行为评测

**目的**：harness 改版后能不能证明「v0.2 比 v0.1 真变好」。区别于 `tests/`（编译对不对，golden render）。

## 不做的事

- 不上 CI 自动跑（跑 LLM-as-judge 的 token 成本高于它的信息量）
- 不做 A/B 多臂台架（单人无 CI；模型本身边界在动，benchmark 也会过期）
- 不让 rubric 分数决定 git 状态——**rubric 是给人看的，不给机器看**

## 一个 case 长这样

```
evals/<route>/<case-id>/
├── input.md         用户话术 + 复现条件（不带答案）
├── context/         该 case 跑时需要的仓库快照或 minimal 复现（不与现有仓库冲突）
├── expected.md      期望产物 + 通过判据（人写的，含可观察的输出片段）
└── rubric.yaml      5 项评分，每项 ≥10 分（人在跑完后填，LLM-as-judge 做分数复核）
```

## case 数量

- code / writing / news 三条路线，每条 ≤4 个；
- 总数 ≤12；新增一个就先删一个；
- 命名 `<case-id>` 用语义（`bug-fix-001` / `breaking-news-001`），不用 `test42`。

## 什么时候跑

发版前（语义版本号变 `2.1.x` → `2.2.0` 那一类）手动跑一次：

```
node --experimental-strip-types compiler/render.ts
node --experimental-strip-types compiler/lint.ts
node --experimental-strip-types compiler/evals-runner.ts   # 暂未实现
```

跑出来的总表贴进 CHANGELOG 的「行为变化」段。**不准引用分数做「质量更好」的断言**——只贴分，结论看分差且附原始 rubric。

## 当前目录结构

```
evals/
├── coding/    待 Step 3 写首批 case（code 路线 ≤4 个）
├── writing/   同上
└── news/      同上
```

三个子目录**先建空**——这是设计意图：路线定案了，case 是后填的，目录骨架在评测思路还没细化到 case 时就先有个家。**空目录不会被 lint 判失败**（lint 看的是 engine/skills/agents，不扫 evals/）。