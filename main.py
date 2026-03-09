# -*- coding: utf-8 -*-
"""
主程序入口 - B站 (同步版本)
支持命令行参数:
  python main.py --task video    # 仅爬取视频详情（每小时定时任务）
  python main.py --task comment  # 仅爬取评论弹幕（每天定时任务）
  python main.py --task all      # 全部爬取（默认）
"""
import sys
import argparse
from bilibili_crawler.bili_crawler import BilibiliCrawler
import config


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Bilibili Crawler - B站数据爬虫")
    parser.add_argument(
        "--task",
        type=str,
        default="all",
        choices=["video", "comment", "all"],
        help="任务类型: video(仅视频详情,每小时), comment(仅评论弹幕,每天), all(全部,默认)"
    )
    args = parser.parse_args()

    print(f"开始运行B站爬虫，任务类型: {args.task} ...")

    # 创建爬虫实例
    crawler = BilibiliCrawler()

    # 启动爬虫，传入任务模式
    try:
        crawler.start(config, task=args.task)
        print("B站爬虫执行完成!")
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
