# Pack 决策指南（数量以 `decide_pack.py --list` 现算为准，见 D20）

> 一份**输入关键词/题材 → 推荐 pack** 的速查表 + 工具。配合 `routes/news/scripts/decide_pack.py` 自动判断。

---

## 一、决策维度（4 个）

| 维度 | 含义 | 影响 |
|------|------|------|
| **热点类型** | 13 大类（人物/调查/政策/数据/突发/速报/科普/警示/纪念/观点/体育/国际/反差/晨光） | 决定主 pack 类别 |
| **关键词权重** | 关键词在文本中命中（主词 3 分/辅助 1 分）| 决定同类别内排序 |
| **类型提示** | `--type` 显式指定 | 强加权（+5 分）|
| **长度** | 15/30/45/60/90/120s | 决定镜数（3/3/4/5/7/8）|

---

## 二、Pack 全表

| 主类别 | Primary pack | Secondary pack | 适用热点 |
|--------|--------------|----------------|----------|
| 人物/故事 | `news-coral` | `news-coral-night`, `news-coral-mono` | 单主角 / 反转 / 感人 / 老人 / 家人 / 回忆 |
| 调查/揭露 | `news-ink` | `news-ink-graphite` | 调查 / 卧底 / 暗访 / 追踪 / 内幕 / 黑幕 |
| 政策/法规 | `news-policy` | `news-policy-bold` | 新规 / 政策 / 办法 / 通知 / 施行 / 公文 |
| 数据/排行 | `news-stat` | `news-stat-grid` | 排行 / TOP / 同比 / 指数 / 榜单 |
| 现场/突发 | `news-onsite` | `news-onsite-urgent` | 突发 / 现场 / 直击 / 抢险 / 灾害 / 救援 |
| 速报/合辑 | `news-bulletin` | `news-bulletin-strip` | 速报 / 整点 / 合辑 / 盘点 |
| 科普/图解 | `news-explainer` | `news-explainer-blueprint` | 为什么 / 原理 / 科普 / 图解 / 怎么 |
| 警示/应急 | `news-alert` | `news-alert-warning` | 紧急 / 务必 / 小心 / 预警 / 骗局 / 诈骗 |
| 节日/纪念 | `news-thread` | `news-thread-tribute` | 纪念 / 致敬 / 清明 / 国庆 / 周年 / 追忆 |
| 观点/评论 | `news-takes` | `news-takes-column` | 观点 / 评论 / 专栏 / 我观察 / 思考 |
| 体育/比分 | `news-blast` | `news-blast-score` | 比赛 / 比分 / 进球 / 加时 / 绝杀 / 奥运 |
| 国际/战况 | `news-world` | `news-world-globe` | 国际 / 战况 / 边境 / 外交 / 联合国 |
| 高反差黑白 | `news-polarity` | — | 反差 / 极简 / 强烈 / 黑白 |
| 拂晓/晨光 | `news-dawn` | — | 温暖 / 希望 / 新生 / 清晨 |

**辅 Secondary 包**（当 Primary 不够用）：
- `news-mosaic` / `news-dusk` — 故事/人物有"特殊气质"时
- `news-noir` — 调查/揭露的"更冷峻"分支
- `news-paper` — 政策的"更复古"分支
- `news-podcast` — 观点的"音频"风格

**其他调色板派生**（不进入决策表，但在 batch 决策有需要时可手动指定）：
- `news-coral-mono` / `news-coral-night`
- `news-ink-graphite` / `news-policy-bold` / `news-stat-grid` / `news-onsite-urgent`
- `news-bulletin-strip` / `news-explainer-blueprint` / `news-alert-warning`
- `news-thread-tribute` / `news-takes-column` / `news-blast-score` / `news-world-globe`

---

## 三、自动决策工具

```bash
# 列表所有 pack 分类
python routes/news/scripts/decide_pack.py --list

# 输入热点文本
python routes/news/scripts/decide_pack.py "老人捡垃圾 21 年 账户 42 万"

# 指定类型 + 长度
python routes/news/scripts/decide_pack.py "国务院新规出台" --type policy --length 60
python routes/news/scripts/decide_pack.py "地震现场直击救援" --type breaking --length 30

# 解释某个 pack
python routes/news/scripts/decide_pack.py --explain news-coral-night
```

**输出**：
- `primary`: 推荐 pack
- `alternatives`: 备选 pack
- `reason`: 决策理由（含匹配类别 + 得分 + 镜数）
- `shots`: 长度 → 镜数

---

## 四、决策举例（已测试）

| 输入 | 关键词命中 | 推荐 | 备选 |
|------|-----------|------|------|
| "老人捡垃圾 21 年 账户 42 万" | 老人/感人 → 人物/故事 2 分 | `news-coral` | night, mono, mosaic |
| "国务院新规出台" + --type policy | 国务院/新规/政策 + type 5 分 | `news-policy` | bold, paper |
| "地震现场直击救援" + --type breaking | 地震/直击/救援 + type 5 分 | `news-onsite` | urgent |
| "中国 GDP 增长 5.2% 同比" | 增长/同比 + 5 分 | `news-stat` | grid |
| "国务院: 新规施行 + 印发" | 国务院/新规/施行/印发 + 5 分 | `news-policy` | bold |
| "诈骗新手法 务必小心" + --type alert | 诈骗/小心/务必 + 5 分 | `news-alert` | warning |
| "世界杯决赛 加时绝杀" + --type blast | 世界杯/决赛/加时/绝杀 + 5 分 | `news-blast` | score |

---

## 五、给 agent 的 prompt 模板

```markdown
# 任务: 选最合适 pack

## 步骤
1. 读 `routes/news/pack-decision.md` 第 2 节"Pack 全表"
2. 拿用户提供的热点关键词/主题
3. 在表中找主类别 + primary pack
4. 如有疑虑, 跑 `python routes/news/scripts/decide_pack.py "<关键词>"` 拿推荐
5. 镜数 = `LENGTH_TO_SHOTS[用户指定长度s]`, 默认 5
6. 回填 `MEMORY.md videos[].template: <pack>`

## 例
输入: "老人捡垃圾 21 年账户 42 万"
- 查表: 人物/故事 → news-coral
- 但 t001 已经是 news-coral → 用户明确要求差异化时, 换 news-coral-night (夜店感) 或 news-coral-mono (单色)
```

---

## 六、何时不自动决策

- 用户明确说"用 news-coral-night" → 跳过决策, 直接用
- 主题跨多类别(例: "国务院新规 + 感人故事") → 决策给最高分, **agent 提醒用户** 是否混合两个 pack
- 新增 pack 类别 → 更新 `decide_pack.py` `PACK_BUCKETS` + 同步 SKILL.md

---

## 七、决策不准时怎么办

1. 看 `decide_pack.py --explain <pack>` 确认该 pack 适用场景
2. 跑 `decide_pack.py "<主题>"` 看得分详情, 哪类高分
3. **不要**直接改 pack HTML — 优先调整关键词或重分类
4. 累计 5+ 次不准 → 更新 `PACK_BUCKETS` 的 keywords 权重
