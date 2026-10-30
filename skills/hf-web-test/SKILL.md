---
name: hf-web-test
description: "使用 Anthropic Webapp Testing 方法检查本地 Web 应用、截图、控制台与关键交互，优先复用已有 Playwright 工具或测试。"
---

# Web 应用验证

优先调用已连接的浏览器工具或项目已有 Playwright 测试；有 Python Playwright 环境且需要脚本时读取 upstream/SKILL.md。示例在 upstream/examples/，它们是模板，URL、选择器和输出目录必须替换为本项目实际值。

检查页面状态后再操作，等待可观察元素或响应；长连接页面不强制 networkidle，不机械复制固定 sleep。截图与日志写入当前项目约定的临时目录，不复制 Linux 示例的 /mnt 或 /tmp 到 Windows。

upstream/scripts/with_server.py 保留为上游原文参考，不作为默认进程启动器：它通过 shell 启动命令，存在孙进程清理和输出管道限制。优先已有开发服务器或项目自己的进程管理方式。仅为本次任务启动并清理自己拥有的服务；不终止其他会话，不自动安装 Python 包或浏览器，不导入真实登录态。

报告使用的工具、视口、关键路径和结果；只读源码不算浏览器验证。
