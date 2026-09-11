# harness-factory

让 Claude / Codex / Trae / WorkBuddy 四个 AI 平台，在 **代码 / 长篇小说 / 新闻** 三条路线上按同一套流程纪律工作。完整设计见 [`docs/design.md`](docs/design.md)（唯一事实源）；本文件是入口地图。

## 三本账（§5.4）

任何文件先问：会不会被下次任务当事实读。**会** → `harness-factory/.workspaces/<proj>/`；**不会** → 项目根 `.ai-runtime-artifacts/`；是**程序** → 在这里。

## 顶层目录

```
harness-factory/
├── README.md            本文件
├── LICENSE
├── package.json tsconfig.json   scripts: harness / check；零运行时依赖（§13）
├── .gitignore .gitattributes
│
├── engine/              17 个文件，规则源。AI 读的唯一正文
│                        ├── START.md  gates.md  routes/  contracts/  runbooks/  platforms/
├── agents/              10 个文件，组织图（§8.2，名单见 agents/README.md）
│                        ├── README.md  leader.md  8 × 职员
├── .agents/skills/      ≤100 个技能：「怎么做」，跨工具收敛
│                        ├── shared/  code/  novel/  news/
│                        路径以 agentskills.io 规范为准，**不可挪动**——
│                        Trae / Codex 通过 `.agents/skills/` 直读
├── compiler/            TS，唯一允许存在平台差异的地方（§2b）
│                        ├── render.ts lint.ts sync-skills.ts evals-runner.ts
│                        ├── platforms/  hooks/  verify/
├── tests/               单元 + golden render（§15）
├── evals/               ≤12 case：行为评测（§15）
│                        ├── README.md  coding/ writing/ news/
├── docs/design.md       唯一设计事实源（约 28 KB / 14 节）
└── .workspaces/         每项目一个子目录，gitignored 状态
                         ├── aigc_platfrom_back/  <novel>/  <news>/
```

`engine/` 与 `.agents/skills/` 不合并：前者是**编译输入**（薄），后者是**正文库**（厚）；
硬并导致一页纸要么太长要么引用太多。
`agents/` 与 `.agents/skills/` 不同名：技能跨工具收敛（一份四家吃），agent 各家格式互不相认（这里只是薄薄的母版，渲染成四份平台产物）——**可共享性相反**。

## 5 分钟上手

```bash
npm install                              # devDeps 仅 typescript + @types/node
npm run harness                          # 渲染（产物落进各项目根，见 §3）
npm run check                            # lint（CI 闸门）
```

Step 0 之前只有 `engine/START.md` `engine/gates.md` `engine/routes/code.md` `engine/platforms/codex.md` 是真文件；
其余目录先建骨架是 §16 的顺序原则（**先证引擎、后退旧账、最后铺面**）。

## 已否决

`docs/design.md` §17 全表 15 条，包括：四平台 hook 分写、Trae 按可能有 hook 来设计、产物提交进项目仓、`<100 技能原文 vendor`、bootstrap 投影 stub。新决策冲突先查 §17。