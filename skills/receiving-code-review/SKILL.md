---
name: receiving-code-review
description: 根据独立审查者的反馈修改代码。
version: 1.0.0
when_to_use: 调用 receiving-code-review 时
status: peripheral
tags:
- shared
domain: code
category: code.review
---
# Receiving Code Review

根据独立审查者的反馈修改代码。

## 触发条件

当 Coder 提交的代码被审查者（Reviewer）标记为 `REQUEST_CHANGES` 时使用此 Skill。

## 工作流程

1. 读取审查意见（`requesting-code-review` Skill 生成的审查报告）
2. 逐条处理审查问题，按严重性排序：
   - `critical` — 必须修复
   - `major` — 应该修复
   - `minor` — 建议修复
3. 修改代码后重新运行测试
4. 返回修复摘要

## 修改规则

- 只修改审查意见中提到的文件和位置
- 不引入新的功能或重构
- 如果不同意审查意见，需在返回中说明理由
- 修复后需确保原有测试仍然通过

## 返回格式

```yaml
review_id: <审查ID>
status: fixed | partially_fixed | disputed
fixes:
  - file: <文件路径>
    issue: <原问题>
    fix: <修复说明>
disputed:
  - file: <文件路径>
    issue: <原问题>
    reason: <不同意的理由>
tests_passed: true/false
```
