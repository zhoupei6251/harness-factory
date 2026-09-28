---
name: web-tools-guide
description: "Web 工具使用指南：搜索、网页抓取、浏览器自动化。触发：查资料、上网、搜索、打开网站。"
version: 1.0.0
when_to_use: 需要使用 web 工具时
status: peripheral
tags:
- web
- search
- research
domain: shared
category: shared.research
---

# /web-tools-guide

Web 工具使用指南，包括搜索、网页抓取和浏览器自动化。

## 工具链

### 1. WebSearch（搜索）
用于查找公开信息、新闻、文档。

```
使用 WebSearch：
- query: {搜索关键词}
- allowed_domains: [] (可选，限定域名)
- blocked_domains: [] (可选，排除域名)
```

### 2. WebFetch（抓取）
用于获取网页内容。

```
使用 WebFetch：
- url: {网页 URL}
- prompt: {基于内容的问题}
```

### 3. Agent Browser（浏览器自动化）
用于需要登录、交互的网页操作。

```
使用 Agent Browser：
- action: navigate/click/type/screenshot
- target: {元素选择器}
- value: {输入值}
```

## 错误处理

| 错误 | 解决方案 |
|------|----------|
| API 未配置 | 引导用户配置 |
| 网站不可访问 | 使用 opencli CLI 作为备选 |
| 内容需要登录 | 使用 Agent Browser |

## 搜索策略

1. **精确搜索**: 使用引号 `"关键词"`
2. **排除词**: `-排除词`
3. **限定网站**: `site:example.com`
4. **文件类型**: `filetype:pdf`

## 注意事项

- 尊重 robots.txt
- 不要过度频繁请求
- 处理重定向和错误状态码
