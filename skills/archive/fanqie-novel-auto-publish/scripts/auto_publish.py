#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键发布工作流 - 整合小说生成和番茄发布

完整流程：
1. 加载故事设定（从 .learnings 目录）
2. 生成/读取章节内容
3. 格式转换（自动适配番茄格式）
4. 批量上传（断点续传 + 重试机制）
5. 生成发布报告
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# 导入封装模块
from novel_generator import NovelPipeline, NovelChapter, get_recent_chapters
from fanqie_publisher import FanQiePublisher, Chapter, extract_chapter_from_file
from fanqie_api import FanQieAPI, RateLimiter, RetryHandler, RetryStrategy, PublishReport


class AutoPublishWorkflow:
    """
    自动发布工作流

    整合 novel-generator 和 fanqie-publisher，
    实现从生成到发布的一键完成。
    """

    def __init__(
        self,
        rate_limit: int = 60,
        max_retries: int = 3,
        default_interval: int = 5
    ):
        """
        初始化工作流

        Args:
            rate_limit: 每分钟请求数限制
            max_retries: 最大重试次数
            default_interval: 默认发布间隔（秒）
        """
        self.novel_gen = NovelPipeline()
        self.publisher = FanQiePublisher()
        self.default_interval = default_interval

        # 初始化 API（带限流和重试）
        rate_limiter = RateLimiter(requests_per_minute=rate_limit)
        retry_handler = RetryHandler(
            max_retries=max_retries,
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay=1.0,
            max_delay=30.0
        )
        self.api = FanQieAPI(rate_limiter=rate_limiter, retry_handler=retry_handler)

    def check_status(self) -> dict:
        """
        检查各模块状态

        Returns:
            {"novel_generator": bool, "fanqie_publisher": bool, "logged_in": bool, "works": list}
        """
        status = {
            "novel_generator": True,  # 本地文件存在即正常
            "fanqie_publisher": self.novel_gen.work_dir.exists(),
            "logged_in": False,
            "works": []
        }

        # 检查登录
        login_result = self.publisher.check_login()
        status["logged_in"] = login_result.get("logged_in", False)

        # 获取作品列表
        if status["logged_in"]:
            works_result = self.publisher.get_works()
            if works_result.get("success"):
                status["works"] = works_result["works"]

        return status

    def check_fanqie_login(self) -> tuple:
        """
        检查番茄登录状态

        Returns:
            (success: bool, message: str)
        """
        try:
            result = self.api.check_login()
            return result["logged_in"], result.get("message", "")
        except Exception as e:
            return False, str(e)

    def get_work(self, title: str) -> Optional[dict]:
        """获取指定作品信息"""
        return self.publisher.find_work(title)

    def publish_chapter(
        self,
        work_title: str,
        chapter_file: str,
        interval: int = 5
    ) -> dict:
        """
        发布单个章节

        Args:
            work_title: 作品标题
            chapter_file: 章节 .md 文件路径
            interval: 发布间隔（秒）

        Returns:
            {"success": bool, "message": str}
        """
        # 提取章节
        chapter = extract_chapter_from_file(chapter_file)
        if not chapter:
            return {
                "success": False,
                "message": f"无法从文件提取章节: {chapter_file}"
            }

        # 发布
        result = self.publisher.publish_chapter(
            work_title=work_title,
            chapter=chapter,
            interval=interval
        )

        return result

    def publish_all_in_output(
        self,
        work_title: str,
        interval: int = 5,
        skip_existing: bool = True
    ) -> Dict[str, Any]:
        """
        发布 output 目录下所有章节

        Args:
            work_title: 作品标题
            interval: 发布间隔（秒）
            skip_existing: 是否跳过已上传章节

        Returns:
            {"success_count": int, "fail_count": int, "results": [...], "report": str}
        """
        output_dir = self.novel_gen.output_dir
        if not output_dir.exists():
            return {
                "success": False,
                "message": f"目录不存在: {output_dir}",
                "results": []
            }

        md_files = list(output_dir.glob("*.md"))
        if not md_files:
            return {
                "success": False,
                "message": "没有找到章节文件",
                "results": []
            }

        results = []
        success_count = 0
        fail_count = 0

        for f in sorted(md_files):
            print(f"  正在发布: {f.name}")
            result = self.publish_chapter(work_title, str(f), interval)
            results.append(result)
            if result.get("success"):
                print(f"    [OK] 成功")
                success_count += 1
            else:
                print(f"    [FAIL] {result.get('message')}")
                fail_count += 1

        return {
            "success_count": success_count,
            "fail_count": fail_count,
            "results": results
        }

    def auto_publish_workflow(
        self,
        book_dir: str,
        work_title: str,
        interval: int = 5,
        skip_existing: bool = True,
        auto: bool = False
    ) -> Dict[str, Any]:
        """
        全自动发布流程

        步骤：
        1. 格式转换
        2. 章节拆分
        3. 登录验证
        4. 批量上传（断点续传）
        5. 状态确认
        6. 生成报告

        Args:
            book_dir: 章节目录路径
            work_title: 作品标题
            interval: 发布间隔（秒）
            skip_existing: 跳过已上传章节
            auto: 是否自动模式（无确认提示）

        Returns:
            {"success": bool, "report": str, "message": str}
        """
        start_time = datetime.now()
        print(f"{'=' * 60}")
        print(f"番茄小说全自动发布")
        print(f"{'=' * 60}")
        print(f"作品: {work_title}")
        print(f"目录: {book_dir}")
        print(f"间隔: {interval}秒")
        print(f"断点续传: {'是' if skip_existing else '否'}")
        print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}\n")

        # 1. 格式转换
        print("[1/5] 格式转换...")
        from format_converter import convert_open_novel_to_fanqie
        try:
            chapters = convert_open_novel_to_fanqie(book_dir)
            print(f"      转换完成: {len(chapters)} 章")
        except FileNotFoundError as e:
            return {
                "success": False,
                "message": f"格式转换失败: {e}",
                "report": ""
            }

        # 2. 章节拆分
        print("[2/5] 章节拆分...")
        from fanqie_api import ChapterData
        chapter_list = [
            ChapterData(
                title=c.title,
                content=c.content,
                chapter_num=c.chapter_num,
                word_count=c.words
            )
            for c in chapters
        ]
        print(f"      拆分完成: {len(chapter_list)} 章")

        # 3. 登录验证
        print("[3/5] 登录验证...")
        ok, msg = self.check_fanqie_login()
        if not ok:
            return {
                "success": False,
                "message": f"登录验证失败: {msg}",
                "report": ""
            }
        print(f"      登录状态: OK")

        # 查找作品
        work = self.get_work(work_title)
        if not work:
            return {
                "success": False,
                "message": f"未找到作品: {work_title}",
                "report": ""
            }
        print(f"      作品ID: {work.get('book_id', 'N/A')}")

        # 4. 批量上传
        print(f"[4/5] 批量上传 ({len(chapter_list)} 章)...")
        try:
            report = self.api.batch_upload(
                book_id=work["book_id"],
                chapters=chapter_list,
                interval=interval,
                skip_existing=skip_existing
            )
        except Exception as e:
            return {
                "success": False,
                "message": f"上传失败: {e}",
                "report": ""
            }

        # 5. 状态确认
        print("[5/5] 状态确认...")
        status = self.api.get_publication_status(work["book_id"])
        print(f"      已上传: {status['uploaded']} / {status['total']}")

        # 保存报告
        end_time = datetime.now()
        report.end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")

        output_dir = Path(book_dir).parent
        report_path = report.save(str(output_dir))

        print(f"\n{'=' * 60}")
        print(f"发布完成!")
        print(f"{'=' * 60}")
        print(f"成功: {report.success_count} 章")
        print(f"失败: {report.fail_count} 章")
        print(f"跳过: {report.skipped_count} 章")
        print(f"耗时: {report.total_duration:.1f} 秒")
        print(f"报告: {report_path}")
        print(f"{'=' * 60}\n")

        return {
            "success": report.fail_count == 0,
            "report": report_path,
            "message": f"成功 {report.success_count} 章，失败 {report.fail_count} 章",
            "report_data": {
                "success_count": report.success_count,
                "fail_count": report.fail_count,
                "skipped_count": report.skipped_count,
                "total_duration": report.total_duration
            }
        }

    def full_workflow(
        self,
        idea: str,
        work_title: str,
        chapter_count: int = 5
    ) -> Dict[str, Any]:
        """
        完整工作流：创作 + 发布

        Args:
            idea: 创作需求
            work_title: 作品标题
            chapter_count: 生成章节数

        Returns:
            {"success": bool, "message": str, "chapters": [...]}
        """
        print(f"开始完整流程: {work_title}")
        print(f"创作需求: {idea}")
        print(f"生成章节数: {chapter_count}")

        # 注意：实际生成依赖外部 AI，这里只是框架
        # 用户需要通过 AI 对话生成内容

        return {
            "success": True,
            "message": "请通过 AI 对话生成章节内容，然后调用 continue_workflow 发布",
            "chapters": []
        }

    def continue_workflow(
        self,
        work_title: str,
        project_dir: str,
        start: int,
        end: int
    ) -> Dict[str, Any]:
        """
        继续发布章节

        Args:
            work_title: 作品标题
            project_dir: 项目目录
            start: 起始章节号
            end: 结束章节号

        Returns:
            {"success": bool, "message": str, "published_count": int}
        """
        # 使用自动发布流程
        result = self.auto_publish_workflow(
            book_dir=f"{project_dir}/正文",
            work_title=work_title,
            interval=self.default_interval,
            skip_existing=True
        )

        return {
            "success": result["success"],
            "message": result["message"],
            "published_count": result.get("report_data", {}).get("success_count", 0)
        }


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="番茄小说一键发布工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python auto_publish.py --check                          # 检查状态
  python auto_publish.py --works                           # 列出作品
  python auto_publish.py -w "作品名" -f "章节.md"          # 发布单章
  python auto_publish.py -w "作品名" -d "章节目录/" --auto  # 全自动发布
  python auto_publish.py -w "作品名" -d "章节目录/" -i 3   # 自定义间隔
        """
    )
    parser.add_argument("--work", "-w", type=str, help="作品标题")
    parser.add_argument("--file", "-f", type=str, help="章节文件路径")
    parser.add_argument("--dir", "-d", type=str, help="章节目录路径")
    parser.add_argument("--check", "-c", action="store_true", help="仅检查状态")
    parser.add_argument("--works", action="store_true", help="列出所有作品")
    parser.add_argument("--interval", "-i", type=int, default=5, help="发布间隔(秒)")
    parser.add_argument("--auto", action="store_true", help="全自动模式")
    parser.add_argument("--skip", action="store_true", default=True, help="跳过已上传")
    parser.add_argument("--no-skip", dest="skip", action="store_false", help="不跳过已上传")
    parser.add_argument("--rate-limit", type=int, default=60, help="每分钟请求数")
    parser.add_argument("--max-retries", type=int, default=3, help="最大重试次数")

    args = parser.parse_args()

    workflow = AutoPublishWorkflow(
        rate_limit=args.rate_limit,
        max_retries=args.max_retries,
        default_interval=args.interval
    )

    # 检查状态
    if args.check:
        print("=" * 60)
        print("状态检查")
        print("=" * 60)
        status = workflow.check_status()
        print(f"小说生成模块: {'[OK]' if status['novel_generator'] else '[FAIL]'}")
        print(f"番茄发布模块: {'[OK]' if status['fanqie_publisher'] else '[FAIL]'}")
        print(f"登录状态: {'[OK]' if status['logged_in'] else '[FAIL]'}")
        if status["works"]:
            print(f"\n作品列表 ({len(status['works'])} 部):")
            for w in status["works"]:
                print(f"  - {w['title']} ({w['chapter_count']}章)")
        return

    # 列出作品
    if args.works:
        status = workflow.check_status()
        if not status["works"]:
            print("未登录或无作品")
            return
        print("=" * 60)
        print("作品列表")
        print("=" * 60)
        for i, w in enumerate(status["works"], 1):
            print(f"{i}. {w['title']}")
            print(f"   章节: {w['chapter_count']} | 状态: {w.get('status', 'unknown')}")
        return

    # 全自动发布
    if args.work and args.dir:
        result = workflow.auto_publish_workflow(
            book_dir=args.dir,
            work_title=args.work,
            interval=args.interval,
            skip_existing=args.skip,
            auto=args.auto
        )
        if result["success"]:
            print(f"\n[OK] 发布成功: {result['message']}")
        else:
            print(f"\n[FAIL] 发布失败: {result['message']}")
            sys.exit(1)
        return

    # 发布单个章节
    if args.work and args.file:
        print(f"正在发布到: {args.work}")
        print(f"文件: {args.file}")
        result = workflow.publish_chapter(args.work, args.file, args.interval)
        if result["success"]:
            print(f"\n[OK] 发布成功: {result.get('message', '')}")
        else:
            print(f"\n[FAIL] 发布失败: {result.get('message', '')}")
            sys.exit(1)
        return

    # 无参数时显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
