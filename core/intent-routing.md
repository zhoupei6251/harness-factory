# intent-routing.md - how to decide what to load

Every task starts with: classify the intent, then load the minimum doc set.

## Intent classification

| Trigger | Intent | Load |
|---------|--------|------|
| design / spec / architecture | design | `principles.md` + `routing.md` |
| plan / wbs / breakdown | plan | `routing.md` + `runbooks.md` |
| implement / code / build | implement | `NEVER.md` + `karpathy-guidelines.md` |
| bug / fix / broken | bug | `NEVER.md` + `runbooks.md#bug` |
| review / audit | review | `NEVER.md` + `principles.md` |
| config / setup | config | `runbooks.md#bootstrap` |
| news / article / hot topic / column | news — **archived** | 不自动装载，见下方「归档中的路由」 |

## 归档中的路由（news / novel）

2026-10-22 起 news 与 novel 两个域**从本仓库退役中**，实现与规格整体迁往独立仓库 `D:\zhoupei\heron`。
归档期内的规则：**目录仍在、仍可运行，但不再作为意图路由的目标自动装载**。要做新闻视频，
去 heron；本仓库只接代码域任务。

新闻链本身（归档材料，非本仓库路由）：`skills/news-workflow/SKILL.md` 是入口，它逐段点名
hot-topic-content-maker / media-short-video-copy / viral-script-writer → fact-check → douyin-pro
Path B → douyin-upload。治理文档**不**枚举这条链：v1 文本链（`news-generator` → `news-polish` →
`humanizer`）曾在这里被复述两遍，把 news 一路引到已退役的轨道上。那几个 skill 作为独立文本工具仍在。

## Anti-pattern: pre-loading everything

Do not read all 7 governance docs at session start. Read by intent.
Token cost of pre-loading all 7: ~3000 tokens. Per-intent load: ~500 tokens.
