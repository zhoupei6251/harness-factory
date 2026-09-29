---
name: douyin-upload
description: 当 agent 需要通过已安装的 `sau` CLI 完成抖音登录、cookie 校验、视频上传或图文发布时使用这个 skill。该 skill 适用于已经安装 `social-auto-upload` 且可调用 `sau` 命令的环境。优先使用这个 skill 进行稳定的命令式抖音工作流，而不是一开始就阅读 uploader 源码。
version: 1.0.0
when_to_use: news 产线进入 publishing 阶段、或用户明确要求把成品视频/图文发布到抖音时（本机账号未登录则先交用户登录）
status: peripheral
tags:
- news
- publish
- douyin
- sau-cli
domain: news
category: news.publish
---

# 抖音上传 Skill

优先把 `sau` 作为主接口。

**本仓库（harness-factory / 本机）先看 `references/local-env.md`**：里面是 `sau.exe` 的绝对路径、cookie 目录、当前「未登录」状态，以及本次安装踩到的两个坑（缺 `playwright` 依赖、npmmirror 拿不到 CFT 145 内核）。上游文档只讲通用前提。

不要假设当前环境一定能读取仓库源码。
不要一开始就去读 `uploader/`。
只有在命令不可用或 CLI 执行失败时，才回退到故障排查说明。

## 功能概览

| 功能 | 命令入口 | 说明 |
| --- | --- | --- |
| 抖音登录 | `sau douyin login --account <name>` | 生成或刷新指定账号的 cookie |
| cookie 校验 | `sau douyin check --account <name>` | 检查指定账号 cookie 是否有效 |
| 视频上传 | `sau douyin upload-video ...` | 上传并发布抖音视频 |
| 图文上传 | `sau douyin upload-note ...` | 上传并发布抖音图文 |

元数据约定：

- 视频使用 `title + desc + tags`
- 图文使用 `title + note + tags`

## 默认工作流

1. 先读 `references/local-env.md` 确认本机的 `sau` 调用路径与登录态。
2. 再确认 `references/runtime-requirements.md` 里的运行前提。
3. 再确认 `references/cli-contract.md` 里的命令契约。
4. 执行匹配的 `sau douyin ...` 命令。
5. 如果命令失败，再看 `references/troubleshooting.md`。

## 安全边界

- 登录（扫码/短信）由用户本人完成；agent 不代替用户执行 `sau douyin login`，除非得到明确指令
- 二维码图片要直接发给用户，不要只回传路径
- `cookies/`、`*cookie*.json`、`verify_code.txt` 必须处于 git ignore 状态；真实 cookie 一律不提交
- 发布是对外动作：`--title/--desc/--tags/--declaration/--schedule` 的取值需来自已核查的稿件或用户明确指令，不可自行编造事实或话题

## 支持动作

- 使用 `sau douyin login --account <name>` 登录抖音
- 使用 `sau douyin check --account <name>` 校验 cookie 是否有效
- 使用 `sau douyin upload-video ...` 上传抖音视频
- 使用 `sau douyin upload-note ...` 上传抖音图文

## 命令选择建议

- 当用户需要新的 cookie，或现有 cookie 已失效时，使用 `login`
- 当用户只需要确认 cookie 状态时，使用 `check`
- 当用户要发布视频时，使用 `upload-video`
- 当用户要发布图文时，使用 `upload-note`

## 执行前检查

- 先确认当前 shell 里是否可以调用 `sau`
- 如果 `sau` 不可用，按 `references/runtime-requirements.md` 里的回退方式处理
- 当用户明确指定无头或有头模式时，显式传 `--headless` 或 `--headed`
- 只有用户明确要求定时发布时，才使用 `--schedule`
- 如果登录流程生成了本地二维码图片，不要只把图片路径告诉用户
- 二维码图片本身就是给用户扫码的，优先直接把本地图片展示/发送给用户

## 模板文件

当你需要稳定的命令模板时，使用 `scripts/examples/` 下的文件：

- `douyin_commands.ps1`
- `douyin_commands.sh`
- `douyin_cli_template.py`

## 参考文档

- 本机安装态：`references/local-env.md`
- 运行前提：`references/runtime-requirements.md`
- CLI 契约：`references/cli-contract.md`
- 故障排查：`references/troubleshooting.md`
