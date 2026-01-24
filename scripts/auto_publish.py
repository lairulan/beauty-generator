#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日美女自动发布脚本
每天 20:00 自动生成并发布到公众号草稿箱
"""

import json
import os
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

# 脚本目录
SCRIPT_DIR = Path(__file__).parent.absolute()
SKILL_DIR = SCRIPT_DIR.parent
PUBLISH_SCRIPT = SKILL_DIR / "scripts" / "publish_wechat.py"
LOG_FILE = SKILL_DIR / "logs" / "auto_publish.log"

# 确保日志目录存在
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def log(message: str, level: str = "INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [{level}] {message}"
    print(log_msg)

    # 写入日志文件
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")


def check_api_keys():
    """检查 API 密钥是否配置"""
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    imgbb_key = os.environ.get("IMGBB_API_KEY")
    doubao_key = os.environ.get("DOUBAO_API_KEY")
    wechat_key = os.environ.get("WECHAT_API_KEY")

    if not wechat_key:
        log("❌ WECHAT_API_KEY 未设置", "ERROR")
        return False

    has_openrouter = bool(openrouter_key) and bool(imgbb_key)
    has_doubao = bool(doubao_key)

    if not has_openrouter and not has_doubao:
        log("❌ 未设置可用的图片生成密钥（需要 OPENROUTER_API_KEY+IMGBB_API_KEY 或 DOUBAO_API_KEY）", "ERROR")
        return False

    if not has_openrouter:
        log("⚠️  未设置 OPENROUTER_API_KEY 或 IMGBB_API_KEY，将使用豆包生成")
    elif not has_doubao:
        log("⚠️  未设置 DOUBAO_API_KEY，OpenRouter 失败时无法回退")

    log("✅ API 密钥检查通过")
    return True


def get_today_info():
    """获取今日信息"""
    today = date.today()
    weekday = today.weekday()
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    # 每周主题
    themes = {
        0: {"name": "多样化", "keywords": ["美女", "写真", "人像"]},
        1: {"name": "清新自然", "keywords": ["清纯", "自然", "阳光"]},
        2: {"name": "知性优雅", "keywords": ["知性", "优雅", "书卷气"]},
        3: {"name": "冷艳高冷", "keywords": ["高冷", "冷艳", "御姐"]},
        4: {"name": "可爱甜美", "keywords": ["可爱", "甜美", "萌系"]},
        5: {"name": "时尚潮流", "keywords": ["时尚", "潮流", "街头"]},
        6: {"name": "温暖治愈", "keywords": ["温暖", "治愈", "温柔"]},
    }

    theme = themes.get(weekday, themes[0])

    return {
        "date": today.strftime("%Y-%m-%d"),
        "weekday": weekday_names[weekday],
        "theme": theme["name"],
        "keywords": theme["keywords"]
    }


def auto_publish():
    """执行自动发布"""
    log("=" * 60)
    log("🚀 每日美女自动发布任务开始")
    log("=" * 60)

    # 检查 API 密钥
    if not check_api_keys():
        return False

    # 获取今日信息
    today_info = get_today_info()
    log(f"📅 日期: {today_info['date']}")
    log(f"📆 星期: {today_info['weekday']}")
    log(f"🎨 主题: {today_info['theme']}")
    log(f"🔑 关键词: {', '.join(today_info['keywords'])}")

    # 调用发布脚本
    log(f"🎯 开始生成 3 张图片并发布到公众号...")

    try:
        cmd = [
            "python3", str(PUBLISH_SCRIPT),
            "--count", "3",
            "--type", "newspic"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5分钟超时
            env=os.environ
        )

        # 记录输出
        log("\n--- 发布脚本输出 ---")
        for line in result.stdout.split("\n"):
            if line.strip():
                log(line)
        if result.stderr:
            log("错误输出:", "ERROR")
            for line in result.stderr.split("\n"):
                if line.strip():
                    log(line, "ERROR")
        log("--- 输出结束 ---\n")

        if result.returncode == 0:
            log("✅ 自动发布成功！")
            log(f"📱 请到「三更熟」公众号后台查看草稿箱")
            return True
        else:
            log(f"❌ 自动发布失败，返回码: {result.returncode}", "ERROR")
            return False

    except subprocess.TimeoutExpired:
        log("❌ 执行超时（5分钟）", "ERROR")
        return False
    except Exception as e:
        log(f"❌ 执行异常: {e}", "ERROR")
        return False
    finally:
        log("=" * 60)
        log("🏁 每日美女自动发布任务结束")
        log("=" * 60)
        log("")  # 空行分隔


def main():
    """主函数"""
    success = auto_publish()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
