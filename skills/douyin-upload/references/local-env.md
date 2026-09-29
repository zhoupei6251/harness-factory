# 本地环境（harness-factory / 本机 Windows 实际安装态）

> 上游 `references/runtime-requirements.md` 写的是通用前提；本文件记录**这台机器上已经装好的东西与踩过的坑**，接 `sau` 命令时以本文件为准。

## 安装位置与调用方式

| 项 | 值 |
|----|----|
| 工具仓库 | `D:/work/xinyue/tools/social-auto-upload`（上游 `dreammis/social-auto-upload`，commit `0012d2c`，2026-09-03，MIT；**不在** harness-factory 工作树内） |
| `sau` 可执行 | `D:/work/xinyue/tools/social-auto-upload/.venv/Scripts/sau.exe`（**未加入 PATH**，agent 必须用绝对路径调用） |
| venv python | `D:/work/xinyue/tools/social-auto-upload/.venv/Scripts/python.exe`（Python 3.12.11） |
| cookie 文件 | `<仓库>/cookies/douyin_<account>.json`（由 `--account <account>` 决定文件名） |
| 运行配置 | `<仓库>/conf.py`（已由 `conf.example.py` 复制生成；`sau_cli.py` 启动即 `from conf import BASE_DIR`，缺失则 `ModuleNotFoundError: conf`） |

调用样例（git-bash）：

```bash
D:/work/xinyue/tools/social-auto-upload/.venv/Scripts/sau.exe douyin --help
```

## 凭证与 git 边界（登录前必须成立）

- 上游 `.gitignore` 已覆盖 `cookies`(:175)、`conf.py`(:172)、`.venv`(:124) → `git status` 不会列出 cookie
- **上游漏了 `verify_code.txt`**（抖音短信 2FA 的落地文件，仓库根，用后被删）→ 已写入本机 `<仓库>/.git/info/exclude`（不改上游跟踪文件）
- harness-factory 侧 `.gitignore` 追加 `cookies/`、`*cookie*.json`、`verify_code.txt`，两条仓库都做过「造一个假 cookie → `git status` 不出现」的验证
- 遵守项目安全条款：**禁止把真实 cookie / 密码 / API Key 提交进任何仓库**

## 当前状态（2026-09-28）

- **未登录**，`cookies/` 为空 —— 按用户指令「先不登录，等我把账号搞好先」，安装与接线不含任何登录动作
- 账号就绪后的第一步是用户自己扫码/短信：`sau douyin login --account <name>`（二维码图片要**直接发给用户**，不要只报路径）
- 校验登录态：`sau douyin check --account <name>` → `valid` / `invalid`

## 本次安装的两个真实障碍

1. **缺 `playwright` 依赖**：`pyproject.toml` 只声明 `patchright`，但 `sau_cli.py` 会 eager import 各平台模块，其中 `uploader/baijiahao|alipay|hupu|tk`、`myUtils/login.py` 是 `from playwright.async_api import ...` → 只装 patchright 时 `sau --help` 直接崩。
   修复：`uv pip install playwright`（本机装上 `playwright==1.63.0`）。抖音自身走 patchright，这条只是为了让 CLI 起得来。
2. **上游推荐的镜像拿不到内核**：文档给的 `PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright` 对 patchright 1.58.2 需要的 **Chrome for Testing 145.0.7632.6（chromium v1208）** 返回 404（该镜像没有 `builds/cft/` 目录）。官方 CDN 在本机长时间无输出。
   可用配方（已验证）：从 `cdn.npmmirror.com/binaries/chrome-for-testing/...` 直接取 zip，手工摆进 playwright 缓存目录：

```bash
MD=~/AppData/Local/ms-playwright
mkdir -p $MD/chromium-1208 $MD/chromium_headless_shell-1208
curl -sS --fail -o /tmp/cft/chrome-win64.zip "https://cdn.npmmirror.com/binaries/chrome-for-testing/145.0.7632.6/win64/chrome-win64.zip"
curl -sS --fail -o /tmp/cft/shell.zip "https://cdn.npmmirror.com/binaries/chrome-for-testing/145.0.7632.6/win64/chrome-headless-shell-win64.zip"
unzip -q -o /tmp/cft/chrome-win64.zip -d $MD/chromium-1208
unzip -q -o /tmp/cft/shell.zip -d $MD/chromium_headless_shell-1208
touch $MD/chromium-1208/INSTALLATION_COMPLETE $MD/chromium_headless_shell-1208/INSTALLATION_COMPLETE
```

   验证：`patchright install chromium` 静默通过（视为已装），并用与 `douyin_uploader` 完全相同的启动参数跑通 launch→goto→close（`chromium version = 145.0.7632.6`）。冒烟脚本：`harness-factory/.harness-news-runtime/checks/patchright_launch_smoke.py`。

## news 产线接线注意

- 上传走的是发布页 + `channel="chromium"` 无头浏览器，参数固定为 `--no-sandbox --disable-blink-features=AutomationControlled`；首次真实发布建议 `--headed` 观察一遍
- `--schedule` 只在用户明确要求定时发布时给，格式 `%Y-%m-%d %H:%M`
- `--declaration` 已于 2026-09-29 对齐上游源码（`sau_cli.py:821`、`douyin_uploader/main.py:481`）：
  必须传**弹窗选项原文**，AI 生成内容填 `内容由AI生成`。**上游选不上只 warning、不阻断发布**，
  因此以日志 `自主声明已选择「…」` 为唯一成功凭据；失败改 `--headed` 人工补勾。详见 `cli-contract.md` § 自主声明
- 图文正文用 `--notef <文件>` 比长字符串转义稳（Windows shell 对中文/引号/`&` 不友好）
- 一次 `upload-video` 只发一个文件；成片路径必须是绝对路径
