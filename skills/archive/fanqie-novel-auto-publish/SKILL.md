---
name: fanqie-novel-auto-publish
description: 番茄小说创作发布一条龙技能，整合 AI 创作与番茄发布，支持全自动批量上传、断点续传、错误重试、发布报告生成
version: 1.1.0
when_to_use: 调用 fanqie-novel-auto-publish 时，用于将小说章节自动发布到番茄小说平台
status: peripheral
metadata:
  domain: novel
  priority: P1
  tags:
  - 番茄
  - 自动发布
  - 批量上传
  - 断点续传
domain: novel
category: novel.publish
tags:
- 番茄
- 自动发布
---
# fanqie-novel-auto-publish
# 番茄小说创作发布一条龙技能

整合 AI 小说创作与番茄小说平台发布，支持全自动批量上传、断点续传、错误重试、发布报告生成。

## 核心模块

| 模块 | 文件 | 说明 |
|------|------|------|
| `fanqie_api` | `fanqie_api.py` | 番茄小说 API 封装（登录/上传/批量/重试/限流） |
| `fanqie_publisher` | `fanqie_publisher.py` | 发布器兼容层（调用 fanqie-publisher） |
| `format_converter` | `format_converter.py` | 格式转换（open-novel → 番茄格式） |
| `novel_generator` | `novel_generator.py` | 小说生成流水线 |
| `auto_publish` | `auto_publish.py` | 全自动发布工作流编排 |

## 完整流程

```
想法 → 设定 → 大纲 → 生成多章 → 评审修订 → 格式转换 → 全自动发布 → 发布报告
```

## 使用方式

### 1. 命令行发布（推荐）

```bash
cd skills/fanqie-novel-auto-publish/scripts

# 检查状态
python auto_publish.py --check

# 列出作品
python auto_publish.py --works

# 发布单章
python auto_publish.py -w "我的小说" -f "第1章.md"

# 全自动批量发布
python auto_publish.py -w "我的小说" -d "章节目录/" --auto

# 自定义参数
python auto_publish.py -w "我的小说" -d "章节目录/" -i 3 --skip
```

### 2. Python API

```python
import sys
sys.path.insert(0, "skills/fanqie-novel-auto-publish/scripts")

from auto_publish import AutoPublishWorkflow

# 初始化工作流
workflow = AutoPublishWorkflow(
    rate_limit=60,      # 每分钟请求数
    max_retries=3,       # 最大重试次数
    default_interval=5   # 发布间隔（秒）
)

# 检查状态
status = workflow.check_status()
print(f"登录状态: {status['logged_in']}")
print(f"作品: {status['works']}")

# 发布单章
result = workflow.publish_chapter(
    work_title="我的小说",
    chapter_file="第1章.md",
    interval=5
)

# 全自动发布
result = workflow.auto_publish_workflow(
    book_dir="章节目录/",
    work_title="我的小说",
    interval=5,
    skip_existing=True,  # 断点续传
    auto=True
)
print(result["report"])
```

### 3. 高级 API（fanqie_api.py）

```python
from fanqie_api import FanQieAPI, ChapterData, PublishReport

api = FanQieAPI(
    cookies_path="~/.openclaw/skills/fanqie-publisher/scripts/fanqie_cookies.json"
)

# 登录
token = api.login("username", "password")

# 获取作品
works = api.get_works()
book = api.find_work("我的小说")

# 上传章节
chapter = ChapterData(
    title="第1章 穿越",
    content="正文内容...",
    chapter_num=1,
    word_count=3000
)
result = api.upload_chapter(book.book_id, chapter)

# 批量上传
report = api.batch_upload(
    book_id=book.book_id,
    chapters=[chapter1, chapter2, ...],
    interval=5,
    skip_existing=True
)
print(report.to_markdown())
```

## 功能特性

### 1. 错误重试机制

- **网络错误**：自动重试 3 次，指数退避（1s → 2s → 4s）
- **API 限流**：自动检测 429 响应，暂停后继续
- **失败记录**：记录失败章节和原因，便于排查

### 2. 断点续传

- 自动检测已上传章节
- 跳过已上传章节，避免重复
- 支持 `--no-skip` 强制重新上传

### 3. 发布报告

发布完成后自动生成 Markdown 报告：

```markdown
# 番茄小说发布报告

## 书籍：《我的小说》
## 时间：2026-07-02

## 上传统计
| 章节 | 状态 | 字数 | 耗时 | 重试 |
|------|------|------|------|------|
| 第1章 | ✅ 成功 | - | 1.2s | 0 |
| 第2章 | ❌ 失败 (API_ERROR) | - | 3.1s | 3 |

## 汇总
| 指标 | 数值 |
|------|------|
| 总章节 | 28 |
| 成功 | 27 |
| 失败 | 1 |
| 总耗时 | 35.2s |
```

### 4. 限流控制

- 默认每分钟 60 请求
- 可配置 `--rate-limit`
- 自动等待间隙

## 配置

### 环境变量

```bash
# Cookie 文件路径（默认）
export FANQIE_COOKIES_PATH="~/.openclaw/skills/fanqie-publisher/scripts/fanqie_cookies.json"
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-w, --work` | 作品标题 | - |
| `-f, --file` | 章节文件路径 | - |
| `-d, --dir` | 章节目录路径 | - |
| `-i, --interval` | 发布间隔（秒） | 5 |
| `--auto` | 全自动模式 | False |
| `--skip` | 跳过已上传 | True |
| `--rate-limit` | 每分钟请求数 | 60 |
| `--max-retries` | 最大重试次数 | 3 |

## 依赖

- `open-novel-writing` 技能（生成小说内容）
- `fanqie-publisher` 技能（发布到番茄小说）
- Python 3.8+

## 工作目录

- 小说输出：`~/.openclaw/skills/novel-generator/output/`
- 记忆文件：`~/.openclaw/skills/novel-generator/.learnings/`
- Cookie 文件：`~/.openclaw/skills/fanqie-publisher/scripts/fanqie_cookies.json`
- 发布报告：`章节目录/publish_report_*.md`

## 故障排除

### 登录失败
```bash
# 重新登录
python -c "from fanqie_api import FanQieAPI; api = FanQieAPI(); api.login('user', 'pass')"
```

### 上传失败
```bash
# 检查状态
python auto_publish.py --check

# 查看作品列表
python auto_publish.py --works
```

### 限流触发
```
WARNING: API 限流，锁定 60 秒
```
等待后自动继续，无需手动操作。

---

企业开发·定制技能请联系Wx：CChenJ_
