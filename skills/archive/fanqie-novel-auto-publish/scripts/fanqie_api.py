#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄小说 API 封装模块

提供完整的番茄小说 API 功能，包括：
- 登录认证
- 书籍管理
- 章节上传
- 批量发布
- 状态查询
- 断点续传
"""

import os
import sys
import json
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略"""
    FIXED = "fixed"           # 固定间隔
    LINEAR = "linear"         # 线性递增
    EXPONENTIAL = "exponential"  # 指数退避


@dataclass
class PublishResult:
    """发布结果"""
    success: bool
    chapter_title: str
    chapter_num: int = 0
    message: str = ""
    error_type: str = ""
    duration: float = 0.0
    retry_count: int = 0


@dataclass
class ChapterData:
    """章节数据"""
    title: str
    content: str
    chapter_num: int = 0
    word_count: int = 0

    def __post_init__(self):
        if self.word_count == 0:
            self.word_count = len(self.content.replace('\n', '').replace(' ', ''))


@dataclass
class BookInfo:
    """书籍信息"""
    book_id: str
    title: str
    author: str
    status: str
    chapter_count: int = 0
    word_count: int = 0
    last_update: str = ""


@dataclass
class PublishReport:
    """发布报告"""
    book_title: str
    start_time: str
    end_time: str = ""
    total_chapters: int = 0
    success_count: int = 0
    fail_count: int = 0
    skipped_count: int = 0
    total_words: int = 0
    total_duration: float = 0.0
    results: List[PublishResult] = field(default_factory=list)
    errors: List[Dict] = field(default_factory=list)

    def add_result(self, result: PublishResult):
        self.results.append(result)
        if result.success:
            self.success_count += 1
        else:
            self.fail_count += 1
            self.errors.append({
                "chapter": result.chapter_title,
                "error": result.message,
                "type": result.error_type
            })
        self.total_duration += result.duration

    def skip_chapter(self, chapter_title: str):
        self.skipped_count += 1

    def to_markdown(self) -> str:
        """生成 Markdown 格式报告"""
        self.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        md = f"""# 番茄小说发布报告

## 书籍：《{self.book_title}》
## 开始时间：{self.start_time}
## 完成时间：{self.end_time}

---

## 上传统计

| 章节 | 状态 | 字数 | 耗时 | 重试 |
|------|------|------|------|------|
"""
        for r in self.results:
            status_icon = "✅ 成功" if r.success else f"❌ 失败 ({r.error_type})"
            md += f"| {r.chapter_title} | {status_icon} | - | {r.duration:.1f}s | {r.retry_count} |\n"

        md += f"""
---

## 跳过章节
"""
        if self.skipped_count == 0:
            md += "无\n"
        else:
            md += f"共 {self.skipped_count} 章（已上传，跳过）\n"

        md += f"""
---

## 错误详情
"""
        if not self.errors:
            md += "无\n"
        else:
            for err in self.errors:
                md += f"- **{err['chapter']}**: {err['error']}\n"

        md += f"""
---

## 汇总

| 指标 | 数值 |
|------|------|
| 总章节 | {self.total_chapters} |
| 成功 | {self.success_count} |
| 失败 | {self.fail_count} |
| 跳过 | {self.skipped_count} |
| 总字数 | {self.total_words} |
| 总耗时 | {self.total_duration:.1f}s |
| 平均速度 | {self.total_duration/self.success_count:.1f}s/章 (仅成功) |

---

*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
        return md

    def save(self, output_dir: str = ".") -> str:
        """保存报告到文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        safe_title = "".join(c for c in self.book_title if c.isalnum() or c in (' ', '-', '_'))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"publish_report_{safe_title}_{timestamp}.md"
        filepath = output_path / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_markdown())

        logger.info(f"报告已保存: {filepath}")
        return str(filepath)


class RateLimiter:
    """API 限流处理器"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_times: List[float] = []
        self.locked_until: float = 0

    def acquire(self) -> float:
        """
        获取请求许可

        Returns:
            需要等待的秒数
        """
        now = time.time()

        # 如果被锁定，等待
        if self.locked_until > now:
            wait_time = self.locked_until - now
            time.sleep(wait_time)
            now = time.sleep

        # 清理超过 1 分钟的记录
        self.request_times = [t for t in self.request_times if now - t < 60]

        # 检查是否达到限制
        if len(self.request_times) >= self.requests_per_minute:
            oldest = self.request_times[0]
            wait_time = 60 - (now - oldest)
            if wait_time > 0:
                logger.warning(f"限流触发，等待 {wait_time:.1f} 秒")
                time.sleep(wait_time)

        self.request_times.append(time.time())
        return 0

    def notify_rate_limit(self, retry_after: int = 60):
        """通知被限流，设置锁定时间"""
        self.locked_until = time.time() + retry_after
        logger.warning(f"API 限流，锁定 {retry_after} 秒")


class RetryHandler:
    """错误重试处理器"""

    def __init__(
        self,
        max_retries: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        base_delay: float = 1.0,
        max_delay: float = 30.0
    ):
        self.max_retries = max_retries
        self.strategy = strategy
        self.base_delay = base_delay
        self.max_delay = max_delay

    def calculate_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * attempt
        else:  # EXPONENTIAL
            delay = self.base_delay * (2 ** (attempt - 1))

        return min(delay, self.max_delay)

    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> tuple:
        """
        带重试执行函数

        Returns:
            (success: bool, result: Any, retry_count: int)
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                return True, result, attempt - 1
            except Exception as e:
                last_error = e
                error_type = type(e).__name__

                # 非重试类错误直接失败
                if error_type in ('AuthenticationError', 'ValidationError'):
                    return False, str(e), attempt - 1

                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        f"尝试 {attempt} 失败: {e}, "
                        f"{self.max_retries - attempt} 次重试，"
                        f"等待 {delay:.1f}s"
                    )
                    time.sleep(delay)

        return False, str(last_error), self.max_retries


class FanQieAPI:
    """
    番茄小说 API 客户端

    提供完整的番茄小说 API 功能封装。
    """

    # API 端点（示例，实际请替换为真实端点）
    BASE_URL = "https://api.fanqiecreative.com"

    def __init__(
        self,
        cookies_path: str = None,
        token: str = None,
        rate_limiter: RateLimiter = None,
        retry_handler: RetryHandler = None
    ):
        """
        初始化 API 客户端

        Args:
            cookies_path: Cookie 文件路径
            token: 认证 Token（优先级高于 cookies）
            rate_limiter: 限流器
            retry_handler: 重试处理器
        """
        if token:
            self.token = token
            self.cookies = None
        elif cookies_path:
            self.cookies = self._load_cookies(cookies_path)
            self.token = self.cookies.get('token') if self.cookies else None
        else:
            self.cookies = None
            self.token = None

        self.rate_limiter = rate_limiter or RateLimiter()
        self.retry_handler = retry_handler or RetryHandler()

    def _load_cookies(self, path: str) -> Optional[dict]:
        """加载 Cookie"""
        cookie_path = Path(path).expanduser()
        if cookie_path.exists():
            try:
                with open(cookie_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载 Cookie 失败: {e}")
        return None

    def _save_cookies(self, path: str, cookies: dict):
        """保存 Cookie"""
        cookie_path = Path(path).expanduser()
        cookie_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cookie_path, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

    def _make_headers(self) -> dict:
        """构建请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict = None,
        requires_auth: bool = True
    ) -> dict:
        """
        发起 API 请求（带限流和重试）

        Args:
            method: HTTP 方法
            endpoint: API 端点
            data: 请求数据
            requires_auth: 是否需要认证

        Returns:
            API 响应
        """
        self.rate_limiter.acquire()

        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = self._make_headers()

        def _do_request():
            import urllib.request
            import urllib.error

            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8') if data else None,
                headers=headers,
                method=method
            )

            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                if e.code == 429:  # Rate limit
                    self.rate_limiter.notify_rate_limit(60)
                    raise Exception("Rate limited")
                raise
            except urllib.error.URLError as e:
                raise Exception(f"Network error: {e}")

        success, result, retry_count = self.retry_handler.execute_with_retry(_do_request)

        if not success:
            raise Exception(f"Request failed after {retry_count} retries: {result}")

        return result

    # ============================================================
    # 认证相关
    # ============================================================

    def login(self, username: str, password: str) -> str:
        """
        登录获取 Token

        Args:
            username: 用户名
            password: 密码

        Returns:
            Token 字符串
        """
        # 密码 MD5 哈希
        password_hash = hashlib.md5(password.encode()).hexdigest()

        data = {
            "username": username,
            "password": password_hash
        }

        response = self._request("POST", "/api/auth/login", data, requires_auth=False)

        if response.get("success"):
            self.token = response["data"]["token"]
            return self.token
        else:
            raise Exception(f"Login failed: {response.get('message')}")

    def check_login(self) -> Dict[str, Any]:
        """
        检查登录状态

        Returns:
            {"logged_in": bool, "user": dict, "message": str}
        """
        if not self.token:
            return {"logged_in": False, "message": "未设置 Token"}

        try:
            response = self._request("GET", "/api/user/profile")
            return {
                "logged_in": True,
                "user": response.get("data", {}),
                "message": "已登录"
            }
        except Exception as e:
            return {"logged_in": False, "message": str(e)}

    # ============================================================
    # 书籍管理
    # ============================================================

    def get_book_info(self, book_id: str) -> BookInfo:
        """
        获取书籍信息

        Args:
            book_id: 书籍 ID

        Returns:
            BookInfo 对象
        """
        response = self._request("GET", f"/api/books/{book_id}")

        if response.get("success"):
            data = response["data"]
            return BookInfo(
                book_id=data["book_id"],
                title=data["title"],
                author=data["author"],
                status=data["status"],
                chapter_count=data.get("chapter_count", 0),
                word_count=data.get("word_count", 0),
                last_update=data.get("last_update", "")
            )
        else:
            raise Exception(f"Failed to get book info: {response.get('message')}")

    def get_works(self) -> List[BookInfo]:
        """
        获取作品列表

        Returns:
            BookInfo 列表
        """
        response = self._request("GET", "/api/works")

        if response.get("success"):
            return [
                BookInfo(
                    book_id=w["book_id"],
                    title=w["title"],
                    author=w["author"],
                    status=w["status"],
                    chapter_count=w.get("chapter_count", 0),
                    word_count=w.get("word_count", 0)
                )
                for w in response.get("data", [])
            ]
        return []

    def find_work(self, title: str) -> Optional[BookInfo]:
        """
        查找作品

        Args:
            title: 作品标题（支持模糊匹配）

        Returns:
            BookInfo 或 None
        """
        works = self.get_works()
        for work in works:
            if title in work.title:
                return work
        return None

    # ============================================================
    # 章节管理
    # ============================================================

    def get_uploaded_chapters(self, book_id: str) -> List[Dict]:
        """
        获取已上传章节列表（用于断点续传）

        Args:
            book_id: 书籍 ID

        Returns:
            [{"chapter_num": int, "title": str, "upload_time": str}, ...]
        """
        response = self._request("GET", f"/api/books/{book_id}/chapters")

        if response.get("success"):
            return response.get("data", [])
        return []

    def upload_chapter(self, book_id: str, chapter_data: ChapterData) -> PublishResult:
        """
        上传单个章节

        Args:
            book_id: 书籍 ID
            chapter_data: 章节数据

        Returns:
            PublishResult
        """
        start_time = time.time()

        data = {
            "title": chapter_data.title,
            "content": chapter_data.content,
            "chapter_num": chapter_data.chapter_num,
            "word_count": chapter_data.word_count
        }

        try:
            response = self._request("POST", f"/api/books/{book_id}/chapters", data)

            if response.get("success"):
                return PublishResult(
                    success=True,
                    chapter_title=chapter_data.title,
                    chapter_num=chapter_data.chapter_num,
                    message="上传成功",
                    duration=time.time() - start_time
                )
            else:
                return PublishResult(
                    success=False,
                    chapter_title=chapter_data.title,
                    chapter_num=chapter_data.chapter_num,
                    message=response.get("message", "未知错误"),
                    error_type="API_ERROR",
                    duration=time.time() - start_time
                )
        except Exception as e:
            return PublishResult(
                success=False,
                chapter_title=chapter_data.title,
                chapter_num=chapter_data.chapter_num,
                message=str(e),
                error_type=type(e).__name__,
                duration=time.time() - start_time
            )

    def batch_upload(
        self,
        book_id: str,
        chapters: List[ChapterData],
        interval: int = 5,
        skip_existing: bool = True
    ) -> PublishReport:
        """
        批量上传章节

        Args:
            book_id: 书籍 ID
            chapters: 章节列表
            interval: 章节间间隔（秒）
            skip_existing: 是否跳过已上传章节

        Returns:
            PublishReport
        """
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        book_info = self.get_book_info(book_id)

        report = PublishReport(
            book_title=book_info.title,
            start_time=start_time,
            total_chapters=len(chapters)
        )

        # 获取已上传章节（用于断点续传）
        uploaded_chapters = set()
        if skip_existing:
            uploaded = self.get_uploaded_chapters(book_id)
            uploaded_chapters = {c["chapter_num"] for c in uploaded}
            report.skipped_count = len(uploaded_chapters)
            logger.info(f"已上传 {len(uploaded_chapters)} 章，将跳过")

        for chapter in chapters:
            # 断点续传检查
            if chapter.chapter_num in uploaded_chapters:
                logger.info(f"跳过已上传章节: {chapter.title}")
                report.skip_chapter(chapter.title)
                continue

            # 上传
            logger.info(f"上传章节: {chapter.title}")
            result = self.upload_chapter(book_id, chapter)
            report.add_result(result)

            # 间隔
            if interval > 0 and result.success:
                time.sleep(interval)

        # 统计字数
        report.total_words = sum(c.word_count for c in chapters)

        return report

    def get_publication_status(self, book_id: str) -> Dict[str, Any]:
        """
        获取发布状态

        Args:
            book_id: 书籍 ID

        Returns:
            {"total": int, "uploaded": int, "pending": int, "failed": int}
        """
        chapters = self.get_uploaded_chapters(book_id)
        book_info = self.get_book_info(book_id)

        return {
            "total": book_info.chapter_count,
            "uploaded": len(chapters),
            "pending": book_info.chapter_count - len(chapters),
            "failed": 0  # 需要从上传记录中统计
        }

    # ============================================================
    # 全自动发布流程
    # ============================================================

    def auto_publish(
        self,
        book_dir: str,
        work_title: str = None,
        options: dict = None
    ) -> PublishReport:
        """
        全自动发布流程

        Args:
            book_dir: 章节目录
            work_title: 作品标题（用于查找书籍）
            options: 配置选项
                - interval: 发布间隔（秒）
                - skip_existing: 跳过已上传
                - auto_create: 不存在时自动创建书籍

        Returns:
            PublishReport
        """
        options = options or {}
        interval = options.get("interval", 5)
        skip_existing = options.get("skip_existing", True)

        # 1. 解析章节目录
        chapters = self._parse_chapters_from_dir(book_dir)
        if not chapters:
            raise ValueError(f"未找到章节文件: {book_dir}")

        # 2. 查找或创建书籍
        if work_title:
            book = self.find_work(work_title)
            if not book:
                raise ValueError(f"未找到作品: {work_title}")
            book_id = book.book_id
        else:
            raise ValueError("必须指定作品标题")

        # 3. 批量上传
        return self.batch_upload(
            book_id=book_id,
            chapters=chapters,
            interval=interval,
            skip_existing=skip_existing
        )

    def _parse_chapters_from_dir(self, book_dir: str) -> List[ChapterData]:
        """从目录解析章节文件"""
        book_path = Path(book_dir)
        if not book_path.exists():
            raise FileNotFoundError(f"目录不存在: {book_dir}")

        chapters = []

        # 支持多种文件格式
        for ext in ['*.txt', '*.md']:
            for file in sorted(book_path.glob(ext)):
                chapter = self._parse_chapter_file(file)
                if chapter:
                    chapters.append(chapter)

        # 按章节号排序
        chapters.sort(key=lambda c: c.chapter_num)
        return chapters

    def _parse_chapter_file(self, filepath: Path) -> Optional[ChapterData]:
        """解析单个章节文件"""
        import re

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        title = None
        body_start = 0

        # 解析标题
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 匹配章节标题模式
            patterns = [
                r'^#\s*(第\s*\d+\s*章.*)',  # # 第1章 标题
                r'^(第\s*\d+\s*章.*)',       # 第1章 标题
                r'^(\d+[.、].*)',             # 1. 标题
            ]

            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    title = match.group(1).strip()
                    body_start = i + 1
                    break

            if title:
                break

        if not title:
            title = filepath.stem

        # 提取正文
        body_lines = []
        for line in lines[body_start:]:
            # 跳过元数据行
            if line.startswith('---') or line.startswith('**') or line.startswith('*'):
                continue
            # 跳过章末钩子
            if line.startswith('>'):
                break
            body_lines.append(line)

        content = '\n'.join(body_lines).strip()

        # 提取章节号
        chapter_num_match = re.search(r'第\s*(\d+)\s*章', title)
        chapter_num = int(chapter_num_match.group(1)) if chapter_num_match else 0

        return ChapterData(
            title=title,
            content=content,
            chapter_num=chapter_num,
            word_count=len(content.replace('\n', '').replace(' ', ''))
        )


# ============================================================
# 兼容旧接口
# ============================================================

class FanQiePublisher:
    """
    番茄小说发布器（兼容旧接口）

    封装 FanQieAPI，提供向后兼容的接口。
    """

    def __init__(self, scripts_dir: str = None):
        """
        初始化发布器

        Args:
            scripts_dir: fanqie-publisher 脚本目录
        """
        if scripts_dir:
            self.scripts_dir = Path(scripts_dir)
        else:
            self.scripts_dir = Path.home() / ".openclaw/skills/fanqie-publisher/scripts"

        # 尝试加载配置
        self.cookies_path = self.scripts_dir / "fanqie_cookies.json"

        # 初始化 API
        self.api = FanQieAPI(cookies_path=str(self.cookies_path))

        # 确保依赖的模块可用
        self._setup_path()

    def _setup_path(self):
        """将 publisher 脚本目录添加到 import 路径"""
        if str(self.scripts_dir) not in sys.path:
            sys.path.insert(0, str(self.scripts_dir))

    def check_login(self) -> Dict:
        """检查登录状态"""
        result = self.api.check_login()
        return {"logged_in": result["logged_in"], "message": result.get("message", "")}

    def get_works(self) -> Dict:
        """获取作品列表"""
        try:
            works = self.api.get_works()
            return {
                "success": True,
                "works": [
                    {
                        "title": w.title,
                        "book_id": w.book_id,
                        "chapter_count": w.chapter_count,
                        "status": w.status
                    }
                    for w in works
                ]
            }
        except Exception as e:
            return {"success": False, "works": [], "message": str(e)}

    def find_work(self, title: str) -> Optional[Dict]:
        """查找作品"""
        work = self.api.find_work(title)
        if work:
            return {
                "title": work.title,
                "book_id": work.book_id,
                "chapter_count": work.chapter_count,
                "status": work.status
            }
        return None

    def publish_chapter(
        self,
        work_title: str,
        chapter: Any,
        interval: int = 5
    ) -> Dict:
        """发布单个章节"""
        try:
            # 查找书籍
            work = self.api.find_work(work_title)
            if not work:
                return {"success": False, "message": f"未找到作品: {work_title}"}

            # 构建章节数据
            chapter_data = ChapterData(
                title=chapter.title,
                content=chapter.content,
                chapter_num=getattr(chapter, 'chapter_num', 0) or 0
            )

            # 上传
            result = self.api.upload_chapter(work.book_id, chapter_data)

            if result.success:
                return {
                    "success": True,
                    "message": f"成功发布: {chapter.title}",
                    "chapter_title": chapter.title
                }
            else:
                return {
                    "success": False,
                    "message": result.message,
                    "chapter_title": chapter.title
                }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def publish_batch(
        self,
        work_title: str,
        chapters: List[Dict],
        interval: int = 5
    ) -> List[Dict]:
        """批量发布章节"""
        try:
            # 查找书籍
            work = self.api.find_work(work_title)
            if not work:
                return [{"success": False, "message": f"未找到作品: {work_title}"}]

            # 转换为 ChapterData
            chapter_list = [
                ChapterData(
                    title=c.get("title", ""),
                    content=c.get("content", ""),
                    chapter_num=c.get("chapter_num", 0) or 0
                )
                for c in chapters
            ]

            # 批量上传
            report = self.api.batch_upload(
                book_id=work.book_id,
                chapters=chapter_list,
                interval=interval
            )

            return [
                {
                    "success": r.success,
                    "message": r.message,
                    "chapter_title": r.chapter_title,
                    "duration": r.duration
                }
                for r in report.results
            ]
        except Exception as e:
            return [{"success": False, "message": str(e)}]


# ============================================================
# 工具函数
# ============================================================

class Chapter:
    """章节对象（兼容旧接口）"""

    def __init__(self, title: str, content: str):
        self.title = title
        self.content = content

    def __repr__(self):
        return f"Chapter(title='{self.title}', content_len={len(self.content)})"


def create_chapter(title: str, content: str) -> Chapter:
    """工厂函数：创建 Chapter 对象"""
    return Chapter(title, content)


def extract_chapter_from_file(filepath: str) -> Optional[Chapter]:
    """从 .md 文件提取章节信息"""
    path = Path(filepath)
    if not path.exists():
        return None

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    title = None
    body_start = 0

    # 找标题
    for i, line in enumerate(lines):
        if line.startswith('# 第'):
            title = line.lstrip('# ').strip()
            body_start = i + 1
            break

    if not title:
        return None

    # 找分隔符
    sep_idx = None
    for i in range(body_start, len(lines)):
        if lines[i].strip() == '---':
            sep_idx = i
            break

    content_start = sep_idx + 1 if sep_idx else body_start

    # 提取正文（到章末钩子前）
    body_lines = []
    for line in lines[content_start:]:
        if line.startswith('>'):
            break
        body_lines.append(line)

    pure_content = '\n'.join(body_lines).strip()

    return Chapter(title=title, content=pure_content)


# ============================================================
# 主入口
# ============================================================

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="番茄小说 API 工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 登录
    login_parser = subparsers.add_parser("login", help="登录")
    login_parser.add_argument("-u", "--username", required=True, help="用户名")
    login_parser.add_argument("-p", "--password", required=True, help="密码")
    login_parser.add_argument("--save", help="保存 Cookie 到文件")

    # 检查登录
    subparsers.add_parser("check", help="检查登录状态")

    # 作品列表
    subparsers.add_parser("works", help="列出作品")

    # 上传章节
    upload_parser = subparsers.add_parser("upload", help="上传章节")
    upload_parser.add_argument("-w", "--work", required=True, help="作品标题")
    upload_parser.add_argument("-f", "--file", required=True, help="章节文件")
    upload_parser.add_argument("-i", "--interval", type=int, default=5, help="间隔秒数")

    # 批量上传
    batch_parser = subparsers.add_parser("batch", help="批量上传")
    batch_parser.add_argument("-w", "--work", required=True, help="作品标题")
    batch_parser.add_argument("-d", "--dir", required=True, help="章节目录")
    batch_parser.add_argument("-i", "--interval", type=int, default=5, help="间隔秒数")
    batch_parser.add_argument("--no-skip", action="store_true", help="不跳过已上传")

    # 发布状态
    status_parser = subparsers.add_parser("status", help="查看发布状态")
    status_parser.add_argument("-w", "--work", required=True, help="作品标题")

    args = parser.parse_args()

    api = FanQieAPI()

    if args.command == "login":
        token = api.login(args.username, args.password)
        print(f"登录成功，Token: {token[:20]}...")
        if args.save:
            api._save_cookies(args.save, {"token": token})
            print(f"已保存到: {args.save}")

    elif args.command == "check":
        result = api.check_login()
        print(f"登录状态: {'已登录' if result['logged_in'] else '未登录'}")
        print(f"信息: {result.get('message', '')}")

    elif args.command == "works":
        works = api.get_works()
        if not works:
            print("无作品")
        else:
            for w in works:
                print(f"- {w.title} ({w.chapter_count}章)")

    elif args.command == "upload":
        chapter = extract_chapter_from_file(args.file)
        if not chapter:
            print(f"无法解析文件: {args.file}")
            sys.exit(1)

        publisher = FanQiePublisher()
        result = publisher.publish_chapter(args.work, chapter, args.interval)
        if result["success"]:
            print(f"成功: {result['message']}")
        else:
            print(f"失败: {result['message']}")
            sys.exit(1)

    elif args.command == "batch":
        publisher = FanQiePublisher()
        report = publisher.api.auto_publish(
            book_dir=args.dir,
            work_title=args.work,
            options={
                "interval": args.interval,
                "skip_existing": not args.no_skip
            }
        )
        print(report.to_markdown())

    elif args.command == "status":
        work = api.find_work(args.work)
        if not work:
            print(f"未找到作品: {args.work}")
            sys.exit(1)

        status = api.get_publication_status(work.book_id)
        print(f"作品: {work.title}")
        print(f"总章节: {status['total']}")
        print(f"已上传: {status['uploaded']}")
        print(f"待发布: {status['pending']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
