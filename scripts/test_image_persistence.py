#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号图片持久性测试脚本
验证发布到公众号后的图片是否在24小时后依然有效
"""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# 脚本目录
SCRIPT_DIR = Path(__file__).parent.absolute()
SKILL_DIR = SCRIPT_DIR.parent
LOGS_DIR = SKILL_DIR / "logs"
TEST_RECORD_FILE = LOGS_DIR / "image_persistence_test.json"


def save_test_record(image_urls: list):
    """保存测试记录"""
    record = {
        "timestamp": datetime.now().isoformat(),
        "check_after": (datetime.now() + timedelta(hours=25)).isoformat(),
        "image_urls": image_urls,
        "status": "waiting_for_check",
        "notes": {
            "test_purpose": "验证公众号图片是否在豆包云URL过期后依然有效",
            "original_url_expiry": "豆包云URL有效期24小时",
            "wechat_cdn": "理论上微信会自动将图片保存到CDN",
            "check_time": (datetime.now() + timedelta(hours=25)).strftime("%Y-%m-%d %H:%M")
        }
    }

    with open(TEST_RECORD_FILE, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 测试记录已保存")
    return record


def check_test_record():
    """查看测试记录"""

    if not TEST_RECORD_FILE.exists():
        print("❌ 未找到测试记录")
        print(f"\n请先运行测试:")
        print(f"  python3 {Path(__file__).name}")
        return

    with open(TEST_RECORD_FILE, "r", encoding="utf-8") as f:
        record = json.load(f)

    print("=" * 60)
    print("📋 图片持久性测试记录")
    print("=" * 60)

    test_time = datetime.fromisoformat(record['timestamp'])
    check_time = datetime.fromisoformat(record['check_after'])
    now = datetime.now()

    print(f"\n🕐 测试发布时间: {test_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🕐 建议检查时间: {check_time.strftime('%Y-%m-%d %H:%M:%S')}")

    remaining = check_time - now
    if remaining.total_seconds() > 0:
        days = remaining.days
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        print(f"⏳ 距离检查时间还有: {days}天 {hours}小时 {minutes}分钟")
    else:
        print(f"⏰ 已过检查时间！现在应该验证结果")

    print(f"\n🔗 图片URL:")
    for i, url in enumerate(record['image_urls'], 1):
        print(f"   {i}. {url[:80]}...")

    print(f"\n📝 当前状态: {record['status']}")
    print(f"\n💡 说明:")
    print(f"   {record['notes']['test_purpose']}")
    print(f"   {record['notes']['original_url_expiry']}")
    print(f"   {record['notes']['wechat_cdn']}")

    print(f"\n📱 验证步骤:")
    print(f"   1. 到公众号后台查看草稿箱")
    print(f"   2. 找到标题包含【测试】的文章")
    print(f"   3. 检查图片是否正常显示")
    print(f"   4. 如果图片正常 → 微信已自动处理，无需修改")
    print(f"   5. 如果图片失效 → 需要添加图片上传功能")

    print(f"\n⚠️  检查时间: {record['notes']['check_time']}")


def run_test():
    """运行测试"""

    print("=" * 60)
    print("🧪 公众号图片持久性测试")
    print("=" * 60)

    print("\n📋 测试说明:")
    print("   将发布1张图片到公众号草稿箱")
    print("   标题: 【测试】图片持久性验证")
    print("   请在25小时后检查图片是否依然有效")

    print("\n🎨 开始生成并发布...")

    # 调用发布脚本
    cmd = [
        "python3", str(SKILL_DIR / "scripts" / "publish_wechat.py"),
        "--count", "1"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    print(result.stdout)

    if result.returncode == 0:
        print("\n✅ 发布成功！")

        # 从输出中提取图片URL
        image_urls = []
        for line in result.stdout.split("\n"):
            if "http" in line and ("ark-content" in line or "doubao" in line):
                import re
                urls = re.findall(r'https?://[^\s\)]+', line)
                image_urls.extend(urls)

        if image_urls:
            # 保存测试记录
            record = save_test_record(image_urls)

            print("\n" + "=" * 60)
            print("📌 测试记录已保存")
            print("=" * 60)
            print(f"\n🕐 发布时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🕐 检查时间: {(datetime.now() + timedelta(hours=25)).strftime('%Y-%m-%d %H:%M')}")
            print(f"\n📱 后续步骤:")
            print(f"   1. 25小时后运行检查命令:")
            print(f"      python3 {Path(__file__).name} --check")
            print(f"   2. 到公众号后台查看草稿箱")
            print(f"   3. 找到【测试】文章，检查图片是否正常显示")
            print(f"\n✅ 如果图片正常 → 无需修改")
            print(f"❌ 如果图片失效 → 需要添加图片上传功能")
        else:
            print("\n⚠️  未能从输出中提取图片URL，但发布已成功")
            print(f"   请在公众号后台查看草稿箱")
    else:
        print(f"\n❌ 发布失败")
        print(f"   错误: {result.stderr}")
        return False

    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="公众号图片持久性测试"
    )

    parser.add_argument("--check", action="store_true", help="查看测试记录")

    args = parser.parse_args()

    if args.check:
        check_test_record()
    else:
        run_test()


if __name__ == "__main__":
    main()
