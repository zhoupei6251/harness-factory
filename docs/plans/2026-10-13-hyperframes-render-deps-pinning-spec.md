# 渲染依赖锁定与 GSAP 本地化 — Spec

日期：2026-10-13
范围：新闻域 Path B / Path C 渲染链（`skills/douyin-pro`）+ Vue Tier3（`src/web`）
状态：待拆票（供 `to-tickets` 使用）

---

## 1. 问题陈述

判据 4a（固定发射 → 固定渲染 → 字节一致的 H.264 流）已经是台账 ProduceID 的地基。但**渲染输入里有两个外部依赖完全没有被固定**，它们都能在发射器不变的前提下静默改变成片字节：

### 1.1 GSAP：一条 CDN 依赖 + 一个版本分裂

静态模板路（当前生产在跑的）把 GSAP 写成远端 script：

| 位置 | 内容 |
|---|---|
| `templates/hyperframes_path_b/news-coral/host.html:5` | `<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js">` |
| `templates/hyperframes_path_b/index.html:24` | 同上 |
| `scripts/hf_compile.py:666` | 同上（编译发射器写死） |
| `templates/hyperframes_path_c/news-editorial-warm/host.html:5` | 同上 |
| `skills/video-render-engine/SKILL.md:801` | 同上（文档同步项） |

Vue Tier3 路已经把 GSAP 改成 npm 打包，**且版本不同**：

- `package.json:27` → `"gsap": "^3.15.0"`，实装 `3.15.0`
- `src/web/lib/gsap-runtime.ts` 注释写"gsap 主版本对齐原 CDN 版本 3.14.x（避免动画曲线参数兼容性问题）"，**与 `^3.15.0` 矛盾**

三个后果：
1. **离线/CDN 抖动 = 渲染失败或无动画成片**。`gsap-runtime.ts` 自己的文件头就写了这条理由（"hyperframes 可能在无网环境渲染，CDN 引用会失败"），但静态模板路没有执行它。
2. **同一个新闻域，两条路跑两个 GSAP 版本**，补间曲线不保证一致。
3. `^` 范围意味着 `npm install` 可以漂到 3.16，GSAP 的 ease 实现在 minor 里动过。

### 1.2 HyperFrames 引擎：版本不记录、不锁定

`hyperframes_candidates()`（`path_b_build.py:787-805`）的解析优先级是 旗标 > 项目 `node_modules/.bin` > npx 缓存 > 回落 `npx -y`（`:815`，注释自己写着"每次重装，慢"）。

实测当前状态：
- `package.json` 无 `hyperframes` 依赖 → 项目 `node_modules` 那一档是空的
- 实际落在 npx 缓存 `702923228c2ce1e6`，版本 `0.8.151`；npm latest 也是 `0.8.151`（今天是）
- 没有任何地方把引擎版本写进产物元数据

即：**渲染器版本由一个 gitignore 之外的本机缓存目录决定**。缓存一旦失效（清理、换机、`--hyperframes-bin` 指错），下一次渲染走 `npx -y` 现场拉最新引擎，成片字节变，而台账不记版本 → 无法解释也无法复现。

---

## 2. 方案概述

把两个外部依赖变成**仓库内的固定字节**，并在渲染前的闸门处 fail-closed 校验。

- GSAP：静态模板路停用 CDN，改走已有的「从 `node_modules` 拷进 `work_dir`、HTML 相对引用」机制 —— 与 Vue runtime 完全同形（见 §3 先例），不发明新装载方式。
- GSAP 版本：`^3.15.0` → 钉 exact，两条路统一到同一个版本号。
- 引擎：`hyperframes` 加进 `devDependencies` 钉 exact，让 `hyperframes_candidates()` 的第一档（项目 `node_modules`）命中；再加一条版本断言，覆盖万一落到 `npx -y` 的分支。
- 引擎与 GSAP 版本作为**溯源字段**写进编译元数据（只记录，不参与 ProduceID 计算）。

---

## 3. 复用先例（不新建机制）

Vue runtime 本地化已经走通，逐条照抄即可：

| 环节 | 先例位置 |
|---|---|
| HTML 相对引用 | `path_b_build.py:493` `<script src="vue/vue.runtime.global.prod.js">` |
| 从 node_modules 定位并拷贝 | `path_b_build.py:2801-2806`（`node_modules/vue/dist/…` → `work_dir/vue/`） |
| 缺失时告警不静默 | `path_b_build.py:2808` |
| selftest 断言已本地化 | `path_b_selftest.py:4279`（含）、`:4298`（不含，反向用例） |

GSAP 目标形态：`node_modules/gsap/dist/gsap.min.js`（已存在，72 927 B）→ `work_dir/gsap/gsap.min.js`，模板引用 `gsap/gsap.min.js`。

---

## 4. 用户故事

每条可独立验证；标 🎦 的 needing 真渲染，其余纯静态/单测可判。

**GSAP 本地化**

1. 作为发射器维护者，静态模板（Path B / Path C / `index.html` / `hf_compile.py` 的 head 模板）不再出现 `cdn.jsdelivr.net`，以便离线渲染必出动画。
   验证：`grep -rn "cdn.jsdelivr.net" skills/douyin-pro` 命中数 = 0（`SKILL.md:801` 的文档示例一并改掉）。
2. 作为发射器维护者，`work_dir/gsap/gsap.min.js` 由构建步从 `node_modules/gsap/dist/gsap.min.js` 拷入，与 Vue runtime 同一函数内完成。
   验证：selftest 新增用例，喂一个假 `node_modules`，断言目标文件存在且字节等于源文件。
3. 作为产线操作者，GSAP 源文件缺失时构建**停机**而不是告警继续 —— 差异点见 §7-D3（Vue runtime 今天是 `⚠` + 继续，因为 404 会在渲染里暴露；GSAP 缺失会让 lint 通过而出无动画成片，必须硬失败）。
   验证：单测构造缺失场景，断言抛错。
4. 作为渲染复核者，改完后同一次发射的成片与改前**逐字节一致**（GSAP 同版本时）或**明确不一致并记录原因**（跨 3.14.2→3.15.0 时）。🎦
   验证：判据 4a 流程，比 demuxed H.264 流哈希，不比整片 md5。

**版本锁定**

5. 作为台账维护者，`package.json` 里 `gsap` 是 exact 版本（无 `^`/`~`）。验证：读 `package.json` 断言。
6. 作为台账维护者，`hyperframes` 出现在 `devDependencies` 且为 exact 版本。验证：`node_modules/hyperframes/package.json` 可读且版本 == 声明值。
7. 作为产线操作者，`hyperframes_candidates()` 的第一命中档变成「项目 node_modules」，而不是「npx 缓存」。
   验证：直接调 `resolve_hyperframes()`，断言返回的真出处字符串以 `项目 node_modules` 开头。该函数已是纯参数注入形态（`root=` / `npx_root=` / `force_bin=`），可喂假目录单测，零渲染。
8. 作为产线操作者，渲染前的门禁（与 `check --strict` 同批，`path_b_build.py:2841` 附近）校验实际调用的引擎版本 == 期望常量，不等则 fail-closed。
   验证：单测 mock 版本输出为错值，断言闸门拒绝。
9. 作为复核者，编译元数据里能读到 `hyperframes` 与 `gsap` 的版本号。
   验证：断言 emit 出的元数据含这两个字段；**断言 ProduceID 计算公式的输入未包含它们**（见 §6-N1）。

**一致性收口**

10. 作为后来者，`gsap-runtime.ts` 的文件头注释与实际 `package.json` 版本不再矛盾。验证：人工读，或加一条 selftest 字符串比对。
11. 作为维护者，`news-coral/README.md`、`video-render-engine/SKILL.md`、`hyperframes_path_b/index.html` 的示例 head 与实际发射器引用形态一致（都是相对路径），文档不再是"照抄就错"的来源。

---

## 5. 接缝（测试在哪）

全案只跨 **1 个新接缝**，其余复用既有：

| 接缝 | 性质 | 用在哪 |
|---|---|---|
| `resolve_hyperframes()` / `hyperframes_candidates()` | 已有，纯函数、参数可注入 | US 7 直接喂假 root，不渲染 |
| `path_b_selftest.py` 挂载契约断言带（`:2504-2509` argv 支、`:4279/4298` 本地化对） | 已有 | US 2/3/8 加在同一段，不新建测试文件 |
| 判据 4a 双渲染流哈希 | 已有端到端缝 | US 4/9 |
| emit 元数据字段 | **新**（唯一新增面） | US 9 |

理由：`hyperframes_candidates` 已经是三档优先级的可注入函数，把"版本锁定"表达成"优先级第一档必须命中"，就完全不需要新机制——锁定 = 让已有的高档位有内容。

---

## 6. 明确不做

- **N1 不动 ProduceID 公式**。它是 GB 45438 合规元数据；版本信息只作为旁路溯源字段记录，绝不进哈希输入。owner 已就此明确 flag 过。
- **N2 不引入 Lottie / Three.js / TypeGPU**。GSAP-only 是字节确定性的前提（WebGL 上下文、异步资源加载、build-time 随机数都破判据 4a），不是能力欠缺。
- **N3 不接 `hyperframes add` / catalog / registry**。与「真源化 / 自持模板」方向相反，属独立决策。
- **N4 不动 `--at-transitions` 生产不用的现状**（law 15，`evidence/2026-10-09-template-v2-p1-contract.md:83`）。
- **N5 不修 Vue Tier3 的 `data-composition-src` 黑屏风险**（`docs/plans/2026-10-13-hyperframes-vue-tier3-host-integration-spec.md:101` 未决项）。那是另一个接缝，混在一起会让本案的字节比对失去解释力。
- **N6 不做 `--batch` / cloud / lambda / Docker**。云端渲染受 CJK 字体 local-only 硬约束，直接排除。

---

## 7. 已定决策（含待定项）

| # | 决策 | 状态 |
|---|---|---|
| D1 | GSAP 本地化走 Vue runtime 的同形机制（node_modules → work_dir），不新建 vendor 目录 | 定 |
| D2 | **钉哪个 GSAP 版本：建议 `3.14.2`**，即把 npm 侧从 `^3.15.0` 降到 exact `3.14.2`，让两条路回到静态模板当前在跑的版本 | **待拍** |
| | 理由：9 条 primitive 的曲线是在 3.14.2 下调出来的；而 Vue Tier3 的**真渲染至今没跑过**（`docs/plans/2026-10-13-...tier3...-spec.md:135,161` 未勾），现在统一到 3.14.2 的代价是零，等 Tier3 跑通再统一就要重建基线。反方案（统一到 3.15.0）也成立，代价是 US 4 一定不过、需重录判据 4a 基线 | |
| D3 | GSAP 缺失 = 硬失败（区别于 Vue runtime 现状的 `⚠` + 继续） | 定 |
| D4 | 引擎版本采用「devDependencies 钉版 + 运行时断言」双保险，不用 lockfile 单一手段 | 定 |
| | 补充口径：仓库有 `package-lock.json`，`npm ci` 已能钉传递依赖；但 npx 缓存那条路**完全在 lockfile 管辖之外**，所以必须有运行时断言 | |

---

## 8. 补充说明 / 已知坑

- **P1 `engines` 冲突**：`package.json:34-35` 是 `node >=20.9.0`，而 hyperframes 自身要求 `>=22`。把 hyperframes 加进 devDependencies 后 `npm install` 只会告警不阻断，但**真渲染仍需在 node 22 下跑**。
- **P2 nvm 符号链接不跨 Bash 调用**：`nvm use 22.20.0` 与渲染命令必须在**同一次调用**里，否则第二次调用回落到 20.9.0，闸门会拒。US 7/8 的验证脚本若分开跑会误判成"配置没生效"。
- **P3 缓存目录是全局的**：`702923228c2ce1e6` 这种 hash 目录名由 npx 依依赖树生成，不保证稳定，也不能作为"已锁定"的证据。锁定只认 `node_modules/hyperframes/package.json` 的读值。
- **P4 本机无项目级 `node_modules/.bin/hyperframes`**（已实测 `ls` 为空），US 6/7 落地前 `resolve_hyperframes()` 不可能命中第一档——这是现状，不是回归。
- **P5 文档同步是交付物的一部分**：CDN 串出现在 5 处文件（§1.1 表），只改发射器会让 `SKILL.md:801` 和两份 README 成为下一个人的错误真源。
