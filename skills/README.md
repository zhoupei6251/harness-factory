# Skills — 全局 Skill 池

> 三域共用（code / novel / news / shared）。通过 `core/orchestration/domain-config.yaml` 按域加载主次 Skill。
> 共 **194 个 Skill**，扁平目录结构 `skills/<slug>/SKILL.md`。

## 目录结构

```
skills/
├── INDEX.md                    # 完整 Skill 索引（自动生成）
├── categories.yaml             # 26 个分类定义
├── _layer.yaml                # Skill 层分级（must-core / optional）
├── <slug>/SKILL.md           # 每个 Skill 独占一个目录
├── <slug>/_meta.json         # 可选元数据
└── README.md                  # 本文件
```

## 分类体系（26 类）

| 分类 | 数量 | 说明 |
|------|------|------|
| **code** | 11 类 | 代码开发全生命周期（test、refactor、security、architecture 等） |
| **novel** | 4 类 | 小说创作与编辑 |
| **news** | 2 类 | 新闻写作与核查 |
| **shared** | 6 类 | 跨域通用技能 |
| **biz** | 2 类 | 商业分析 |
| **crypto** | 1 类 | 加密相关 |
| **science** | 1 类 | 科学研究 |

详见：[skills/categories.yaml](categories.yaml) | [docs/skill-frontmatter-schema.md](../docs/skill-frontmatter-schema.md)

## Skill 层分级

```yaml
_layer.yaml:
  must-core:   # 必须同步的核心技能（约 50 个）
  optional:    # 可选技能（约 140 个）
```

## Skill 元数据规范

每个 Skill 可选包含 `_meta.json`：

```json
{
  "slug": "skill-name",
  "domain": "code|novel|news|shared",
  "category": "category-id",
  "tags": ["tag1", "tag2"],
  "purpose": "简短描述",
  "requires": ["other-skill"],
  "complements": ["related-skill"],
  "conflicts": ["incompatible-skill"],
  "source": "original|ecc|superpowers"
}
```

详见：[docs/skill-frontmatter-schema.md](../docs/skill-frontmatter-schema.md)

## 加载方式

路由到某域后，按 `core/orchestration/domain-config.yaml` 加载：

- **primary_skills**：路由确定后立即加载
- **secondary_skills**：任务需要时按需加载

### 示例配置

```yaml
# core/orchestration/domain-config.yaml
domain: code
primary_skills:
  - architecture-patterns
  - test-driven-development
secondary_skills:
  - code-review
  - refactor-safely
  - simplify
  - technical-writer
  - humanizer-zh
```

## Skill 依赖图

自动生成的可视化依赖关系图：`docs/skill-dependency-graph.md`

---

## 添加新 Skill 流程

1. 在 `skills/` 下创建新目录（如 `my-new-skill/`）
2. 创建 `SKILL.md`（必需），包含 skill 名称、描述、使用说明
3. 可选创建 `_meta.json` 用于元数据管理
4. 运行 `bash scripts/gen-skill-index.sh` 更新索引
5. 在 `core/orchestration/domain-config.yaml` 中注册

## 质量检查

```bash
# 静态检查
bash tests/L1-static/validate-skill-meta.sh

# Skill 质量检查
bash scripts/skill-quality-check.sh

# 生成索引和依赖图
bash scripts/gen-skill-index.sh
bash scripts/gen-skill-graph.sh
```

## 真相源

所有 Skill 文件即为真相源，`sync-skills.sh` 从真相源同步到各 IDE 投影目录。

## License

MIT
