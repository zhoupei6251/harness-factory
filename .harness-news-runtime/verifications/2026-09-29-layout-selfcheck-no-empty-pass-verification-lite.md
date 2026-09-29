# 2026-09-29 · 版式闸门不许**空过**（`layout_selfcheck.py` 传 pack 名从前的 exit 0 → 现在 exit 1）—— 验证记录（lite）

**范围**：D13 一条 + 它的自测负例 + 三份文档同步（ARCHITECTURE §3/§5/§7/§8、MEMORY 校验 bullet、
news-workflow 校验 bullet）。**不含**新的新闻成片，**不含** AIGC 标识行为改动
（上一轮的姿态文件见 `2026-09-29-aigc-posture-file-verification-lite.md`）。

结论：**显式传入的目录里一个版式文件都没有 = 用法错误，当场 exit 1 并点名该目录；
真目录照旧 exit 0；`--quiet` 同样拦得住；渲染内部那道 `gate_layout_selfcheck` 不经 CLI，一行没受影响。**

---

## 1. 被验对象

```
skills/douyin-pro/scripts/layout_selfcheck.py    main(): 空目录记账 → 结尾非零退出（含 --quiet）；
                                                  报错点名目录 + 写出正确参数写法；docstring 返回码补一句
skills/douyin-pro/scripts/path_b_selftest.py     +1 项 t_layout_selfcheck_refuses_a_directory_with_no_layouts
routes/news/ARCHITECTURE.md                      新增 D13 · §3 树 · §7 硬规则 6 · §8 实测转录（一对绿/红真输出）
routes/news/MEMORY.md / skills/news-workflow/SKILL.md   校验 bullet 同步；顺手把抄死的自测项数改成
                                                  "以脚本末行为准"（这条规则本来就在 news-workflow 里写着）
```

旧行为（本次要修的假绿）：

```
$ python skills/douyin-pro/scripts/layout_selfcheck.py news-coral news-policy
news-coral: 没找到版式文件
news-policy: 没找到版式文件
版式自检通过：0 个文件，0 条违规            EXIT=0     ← 一次打错参数的"绿闸门"
```

**为什么这条值得单独上闸**：三道闸里只有 `layout_selfcheck.py` 的参数握在人手里，而红会让人停下、
假绿会被当凭据抄进文档与台账 —— 2026-09-29 订正 D12 文档时正是把它当成"过了"写进记录的
（那份记录 §5.2 已就地订正指向本文件）。

## 2. 改后的四条命令（都是真输出）

```bash
$ python skills/douyin-pro/scripts/layout_selfcheck.py \
    skills/douyin-pro/templates/hyperframes_path_b/news-coral \
    skills/douyin-pro/templates/hyperframes_path_b/news-policy
版式自检通过：12 个文件，0 条违规                                                            EXIT=0

$ python skills/douyin-pro/scripts/layout_selfcheck.py news-coral news-policy        # pack 名当目录
news-coral: 没找到版式文件
news-policy: 没找到版式文件

版式自检不过：显式传入的 2 个目录里没有任何版式文件（news-coral、news-policy）—— 参数要写含
compositions/*.html 的**目录**（如 skills/douyin-pro/templates/hyperframes_path_b/news-coral），
只写 pack 名不算检查，也不算通过。                                                          EXIT=1

$ python skills/douyin-pro/scripts/layout_selfcheck.py --quiet news-coral            # 静默也不放过
news-coral: 没找到版式文件
版式自检不过：显式传入的 1 个目录里没有任何版式文件（news-coral）—— 参数要写含 …            EXIT=1

$ python skills/douyin-pro/scripts/path_b_build.py --input skills/douyin-pro/scripts/fixtures/badge_probe_shots.json \
    --template news-policy --source 版式探针 --check-only \
    --work-dir .harness-news-runtime/tmp/d13/work --output .harness-news-runtime/tmp/d13/checkonly.mp4
[path_b] ✅ 版式自检通过 (0 违规)
[path_b] ✅ 发射与门禁通过 (未渲染)。                                                    EXIT=0
```

最后一条是**回归防线**：渲染期内部那道闸门走 `check_layout()` 逐文件、不经过 `main()`，
所以改 exit 码不该影响产线 —— `--check-only` 过了就是过了。

## 3. 自测项（双向锁，没有负例的校验器不算校验器）

`t_layout_selfcheck_refuses_a_directory_with_no_layouts` 四件事：
真目录 `news-coral` 必须 **0**（且先断言 `discover_layouts` 非空 —— 前提坏了要当场红，不许变成"空目录也绿"）；
`"news-coral"`（相对名）与 `<TEMPLATE_ROOT>/no-such-pack`（不存在的绝对路径）**两种写法各自**在
`[arg]` 与 `["--quiet", arg]` 两种调用下必须 **1**；报错文本必须**点名那个目录**、必须含 `compositions`
（不教正确写法的报错等于让下一个人再猜一遍）。

## 4. 三道闸（本次改完重跑）

```
$ python skills/douyin-pro/scripts/path_b_selftest.py
[selftest] 72 项 · style=news-coral
  ok    t_layout_selfcheck_refuses_a_directory_with_no_layouts
[selftest] 全绿 72/72                                     EXIT=0
$ python skills/douyin-pro/scripts/audit_pack_contrast.py
对比度审计通过：12 个 pack 的 frame.md 色板与文档一致（0 条警告）   EXIT=0
$ python skills/douyin-pro/scripts/layout_selfcheck.py skills/douyin-pro/templates/hyperframes_path_b/news-coral skills/douyin-pro/templates/hyperframes_path_b/news-policy
版式自检通过：12 个文件，0 条违规                                   EXIT=0
```

日志留在 `.harness-news-runtime/tmp/d13/`（gitignore 目录，本记录是它们的证据）。
项数**只写在这一节**：`61→63→66→71→72` 每一次加断言都会让抄在别处的数过期，
所以 §7 与 MEMORY / SKILL 里的引用统一改成"以脚本末行为准"。

## 5. 未做的两件事（明确留在桌面上，不是遗漏）

1. **没给"传了目录又想跳过检查"留合法写法**。`nargs="+"` 决定了不传参数就报错，要跳过就别跑这条命令 ——
   留一个 `--allow-empty` 等于把假绿重新装回闸门里。
2. **没动 `path_b_build.py` 里烧角标那段**（上一轮记录 §8 记的那条自称来自 `pm` 的代理消息仍无出处、
   仍不可核：`SendMessage` 到 `pm` 返回 `No agent named 'pm' is reachable`，`ListAgents` 里没有这个名字）。
   用户 2026-09-29 对两开关的口径由姿态文件满足，删代码不等于关开关；真要去掉 ① 的能力是改判据
   （D8/D11/硬规则 7 一起动），需要本人明确点头。
   > **订正（同日 · D14）**：本条后半已经成真 —— 用户本人点头的是**改判据**（「判据放宽：交付件可以不带 ① …
   > 烧角标的代码留着」），不是删能力。`path_b_build.py` 因此被改过：烧角标那段**一行没删**，
   > 外面加了三档 `full / no-badge / draft` 的分派；D8/D11/硬规则 7 的口径同步放宽为「② + ③ 齐活」。
   > 凭据见 `.harness-news-runtime/verifications/2026-09-29-aigc-no-badge-rail-D14-verification-lite.md`。
   > 本条前半仍然成立：那条无出处的 `pm` 消息始终没有被当成指令执行。
