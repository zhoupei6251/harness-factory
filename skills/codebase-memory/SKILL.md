---
name: codebase-memory
description: "代码结构、符号、调用和改动影响取证；使用已连接的 codebase-memory-mcp 工具，失败时读取源码并报告实际原因。"
---

# Codebase Memory

先发现本会话工具并调用 list_projects，选择 root_path 与当前项目匹配的精确 name；未索引才调用 index_repository。MCP 连接和客户端注册见仓库 references/tooling.md，安装此技能不代表服务已连接。

- 符号定位：search_graph，使用返回的 qualified_name。
- 源码：get_code_snippet；调用者/被调者：trace_path，按问题选择 inbound/outbound/both。
- 文本和配置：search_code 或精确源码读取；多跳关系按需 query_graph。
- 引用路径调用 check_index_coverage；过期或缺覆盖时读当前源码补证。分页结果只支持已读取范围内的结论。
- 复用本会话仍有效的项目标识和证据；不为局部任务全库索引或审计。

工具不可用时报告：[codebase-memory-mcp 不可用，已降级] 原因：实际错误；替代手段：源码读取与调用追踪。不要假称做过图谱查询，不终止其他会话的进程。

来源：https://github.com/DeusData/codebase-memory-mcp 。这是 Harness 的工具协议适配，不包含服务二进制。
