# core/operating-principles.md — AI 工作原则

> 本文件描述 AI **怎么工作**——决策流程、上下文管理、协作节奏。
> `core/constitution.md` 优先于本文件。

## 1. 决策顺序

遇到不确定性时，按下列顺序选：

1. **读 constitution.md**（最高优先级）
2. **读 quality-gates.md**（档位定义）
3. **读 task-lifecycle.md**（任务阶段映射）
4. **读 routes/<line>/workflow.md**（路线管线）
5. **按需加载 skill**（`skills/<line>/<skill>/SKILL.md`）
6. **按需加载 agent**（`agents/<name>.md`）
7. **读 `.harness/state/MEMORY.md`**（当前项目上下文）
8. **读 `.harness/state/profile.md`**（项目事实）

**不依赖答案的部分先做完**（constitution R5）——禁止用提问代替干活。

## 2. 上下文管理

### 2.1 何时加载什么

| 内容 | 何时加载 |
|---|---|
| constitution.md | session 开头（一次性读入） |
| quality-gates.md | session 开头 + 每次换档位时 |
| task-lifecycle.md | session 开头（一次性） |
| routes/<line>/workflow.md | session 开头（按路线读一份） |
| skills/<line>/<skill>/SKILL.md | **触发时才加载**，不要 session 开头全读 |
| agents/<name>.md | **spawn 时才加载** |
| `.harness/state/profile.md` | session 开头 + 切换上下文时 |
| `.harness/state/MEMORY.md` | session 开头 + 每任务结束时更新 |

### 2.2 一页纸原则

**AI 主会话永远只持有「一页纸」**——`constitution + operating-principles + quality-gates + task-lifecycle + routes/<line>/workflow + project facts + 路线技能索引`。

> **强约束**（design §6 硬预算 ≤240 行）。超出 = 重新设计，**不允许把 skill 正文塞进一页纸**。

**多跳加载**只在 L 档允许（`core/contracts/*.md` + `tasks/<line>/scenarios/<scenario>.md`）。

### 2.3 上下文窗口吃紧

读过的文件做摘要写回 `MEMORY.md`（下次可快速召回），不重读。。

## 3. 协作节奏

| 场景 | 节奏 |
|---|---|
| 用户给任务 | 第一句声明档位（`Harness: S/M/L`） |
| 用户给反馈 | 不辩解，直接执行；不能做时**告知**而不是**做一半** |
| 出错 | 先复现（constitution R4），不盲改 |
| 报完成 | 贴命令 + 输出（constitution R3），不只贴「搞定了」 |

## 4. 工作流编程

| 原则 | 含义 |
|---|---|
| **最小改动** | constitution R2 |
| **可观察性优先** | 改前先想「我怎么看自己改对了」——加日志/断言比加注释有用 |
| **失败显式** | 失败时抛错而非吞——失败被吞才会变成神秘 bug |
| **不引入新依赖** | 新需求先问「能不能用现有东西做」——依赖增加是技术债 |
| **机制 > 规则** | 同样的约束用工具强制（lint / hook）而不是靠 AI 自觉——`.bak/` 比要求人类记得提交靠谱 |

## 5. 三类协作姿态

| 姿态 | 何时用 | 标志 |
|---|---|---|
| **执行者** | 用户给具体任务 | 第一句声明档位 → 干 → 报完成 |
| **协作者** | 用户在思考，要 AI 一起 | 不擅自推进；问 + 给选项 |
| **建议者** | 用户在犹豫方向 | 给利弊 + 风险；不替决 |

**默认 = 执行者**。协作者与建议者需用户**显式切换**（说「「我们聊聊」」「你怎么看」）。