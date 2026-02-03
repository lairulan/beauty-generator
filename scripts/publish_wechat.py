#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号发布脚本
将生成的美女图片发布到公众号草稿箱（小绿书形式）
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

# 脚本目录
SCRIPT_DIR = Path(__file__).parent.absolute()
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
GENERATE_SCRIPT = SKILL_DIR / "scripts" / "generate.py"
BEAUTY_GENERATE_SCRIPT = SKILL_DIR / "scripts" / "generate_beauty.py"

# API 配置
API_BASE = "https://wx.limyai.com/api/openapi"
WECHAT_API_KEY = os.environ.get("WECHAT_API_KEY")

# 公众号配置
DEFAULT_APPID = "wx287cdb9d78a498aa"  # 三更熟


def get_api_key():
    """获取 API Key"""
    if not WECHAT_API_KEY:
        return None
    return WECHAT_API_KEY


def make_request(endpoint, data=None):
    """发送 API 请求"""
    api_key = get_api_key()
    if not api_key:
        return {"success": False, "error": "环境变量 WECHAT_API_KEY 未设置"}

    url = f"{API_BASE}/{endpoint}"

    cmd = [
        "curl", "-s", "-X", "POST", url,
        "-H", f"X-API-Key: {api_key}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(data or {}, ensure_ascii=False)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "请求超时"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"响应解析失败: {result.stdout}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_smart_caption(scene: str = "", emotion: str = "", makeup: str = "", art_style: str = "") -> str:
    """
    智能生成配文 - 根据图片参数动态生成
    不再受星期几限制，完全随机且与图片内容匹配
    """

    # 大型配文库 - 按情绪和场景分类
    captions = {
        "挑逗": [
            "一眼心动，再沦陷。",
            "迷人无需多言，看就够了。",
            "眼神会说话，你听到了吗？",
            "危险又迷人的距离。",
            "这一刻的吸引力，致命。",
            "风情万种，不过如此。",
            "不用刻意，就很勾人。"
        ],
        "忧郁": [
            "孤独是华丽的。",
            "温柔里藏着忧伤。",
            "安静中，故事在流淌。",
            "眼中有海，心中有故事。",
            "淡然，是最好的伪装。",
            "有些话，不用说。",
            "沉默，也是一种表达。"
        ],
        "神秘": [
            "看不透，才最迷人。",
            "眼神里，藏着故事。",
            "若即若离，最是抓人。",
            "谜一样的存在。",
            "保持距离，更有魅力。",
            "猜不透的谜题。",
            "越神秘，越想靠近。"
        ],
        "开心": [
            "笑容是最好的滤镜。",
            "今天的快乐超标了。",
            "阳光下的笑容，治愈一切。",
            "笑着，就很美。",
            "心情写在脸上。",
            "元气满满的一天。",
            "今天也很开心呀。"
        ],
        "高冷": [
            "不讨好，自有光芒。",
            "高冷，也是一种温度。",
            "疏离感刚刚好。",
            "无需刻意，就很酷。",
            "气场全开。",
            "距离产生美。",
            "生人勿近的气场。"
        ],
        "温柔": [
            "温柔了岁月，惊艳了时光。",
            "岁月静好，温柔相伴。",
            "温暖，是最好的滤镜。",
            "柔软中，自有力量。",
            "温柔了整个世界。",
            "安静的美好。",
            "如沐春风的温柔。"
        ],
        "自信": [
            "无需定义，只做自己。",
            "从容，是最大的魅力。",
            "自信，是最好的妆容。",
            "光芒万丈，无需多言。",
            "做自己的风景。",
            "不被定义的自由。",
            "本色出演，就足够好。"
        ],
        "俏皮": [
            "今天也很可爱呢。",
            "甜度满分，超标了。",
            "元气少女上线。",
            "可爱，是挡不住的。",
            "今天的可爱值爆表。",
            "俏皮一下，很开心。",
            "活泼是天性。"
        ],
        # 通用配文（无特定情绪）
        "通用": [
            "今日份心动瞬间。",
            "美好，值得被记录。",
            "每一帧都是心动。",
            "定格此刻的美好。",
            "遇见，就是最好的开始。",
            "时光不语，却给了答案。",
            "安静地发光。",
            "美好从不缺席。",
            "今日份美好已送达。",
            "被光选中的一天。"
        ],
        # 场景配文
        "雨夜": [
            "雨夜，最适合想念。",
            "霓虹灯下的孤单。",
            "雨中，故事在发生。",
            "潮湿的情绪，被雨淋湿。",
            "雨夜，别有一番风味。",
            "湿漉漉的温柔。"
        ],
        "樱花雨": [
            "花瓣雨，落满心头。",
            "樱花树下的约定。",
            "粉色，是春天的告白。",
            "落花时节，又逢君。",
            "樱花雨，浪漫了时光。",
            "每一片都是心事。"
        ],
        "黄昏海滩": [
            "黄昏时，在海边想你。",
            "日落时分，温柔了世界。",
            "海边的黄昏，黄金时刻。",
            "阳光与海，最好的组合。",
            "黄昏，海风，心事。",
            "此刻，刚刚好。"
        ],
        "赛博朋克": [
            "霓虹灯下的未来感。",
            "赛博朋克的浪漫。",
            "未来的样子，想象不到。",
            "科技与美，完美融合。",
            "霓虹闪烁的夜晚。",
            "未来已来。"
        ],
        "咖啡厅": [
            "咖啡时光，慢下来。",
            "咖啡香里，故事发酵。",
            "一杯咖啡，一下午。",
            "咖啡厅，偷得浮生半日闲。",
            "温暖，从一杯咖啡开始。",
            "慢生活，刚刚好。"
        ]
    }

    import random

    # 根据传入的参数选择配文
    if emotion and emotion in captions:
        # 优先使用情绪配文
        return random.choice(captions[emotion])
    elif scene == "雨夜":
        return random.choice(captions["雨夜"])
    elif scene == "樱花雨":
        return random.choice(captions["樱花雨"])
    elif scene == "黄昏海滩":
        return random.choice(captions["黄昏海滩"])
    elif scene == "赛博朋克":
        return random.choice(captions["赛博朋克"])
    elif scene == "咖啡厅":
        return random.choice(captions["咖啡厅"])
    else:
        # 使用通用配文
        return random.choice(captions["通用"])


def generate_one_line_caption(style: str = "") -> str:
    """生成一句话介绍（兼容旧接口）"""
    return generate_smart_caption()


def publish_to_wechat(
    appid: str,
    title: str,
    content: str,
    images: list,
    article_type: str = "newspic"
):
    """发布到公众号草稿箱"""

    # 小绿书格式：图文混排
    if article_type == "newspic":
        # 构建小绿书内容 - 移除 alt text 避免"图片"文字出现
        content_lines = []
        for i, (img_url, caption) in enumerate(images):
            # 使用空的 alt text，避免显示"图片"文字
            content_lines.append(f"![]({img_url})")
            if caption:
                content_lines.append(f"\n{caption}\n")

        content_md = "\n".join(content_lines)
    else:
        content_md = content

    data = {
        "wechatAppid": appid,
        "title": title,
        "content": content_md,
        "contentFormat": "markdown",
        "articleType": article_type
    }


    # 小绿书模式需要明确提供图片URL列表
    if article_type == "newspic" and images:
        image_urls = [img_url for img_url, _ in images]
        data["mainImages"] = image_urls
    result = make_request("wechat-publish", data)
    return result


def generate_daily_images(count: int = 3, style: str = "") -> list:
    """
    生成多张一致性人物图片
    使用 generate_beauty.py 确保人物一致性和高质量
    """
    print(f"\n🎨 正在生成 {count} 张一致性人物图片...")
    print("🎭 人物特征将保持一致，仅改变姿态和角度")

    # 调用美女生成脚本 V4.0
    cmd = [
        "python3", str(BEAUTY_GENERATE_SCRIPT),
        "--count", str(count)
    ]

    if style:
        cmd.extend(["--style", style])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,  # 5分钟超时（3张图）
        env=os.environ
    )

    images = []

    # 解析输出，提取图片 URL
    # generate_beauty.py 输出格式:
    #   1. 极致特写
    #      https://ark-content-generation-v2-cn-beijing.tos-cn-beijing.volces.com/...
    import re
    lines = result.stdout.split("\n")
    for line in lines:
        # 查找包含 http 的行
        if "http" in line and ("ark-content" in line or "doubao" in line):
            urls = re.findall(r'https?://[^\s\)]+', line)
            images.extend(urls)

    # 显示生成结果
    if result.returncode == 0:
        print(f"  ✅ 成功生成 {len(images)} 张图片")
    else:
        print(f"  ⚠️  生成过程有异常，返回码: {result.returncode}")
        if result.stderr:
            print(f"  错误: {result.stderr}")

    return images


def main():
    parser = argparse.ArgumentParser(
        description="每日美女图 - 发布到公众号"
    )

    parser.add_argument("--count", "-c", type=int, default=1, help="生成图片数量（默认1张）")
    parser.add_argument("--style", "-s", help="风格描述")
    parser.add_argument("--scene", help="场景：雨夜、樱花雨、赛博朋克、咖啡厅等")
    parser.add_argument("--emotion", help="情绪：挑逗、忧郁、神秘、开心、高冷、温柔、自信、俏皮")
    parser.add_argument("--makeup", help="妆容：韩妆、欧美妆、烟熏妆、玻璃妆等")
    parser.add_argument("--art-style", help="艺术风格：王家卫、韩剧、电影感、ins风等")
    parser.add_argument("--appid", help="公众号 AppID（默认：三更熟）")
    parser.add_argument("--title", "-t", help="文章标题（自动生成默认）")
    parser.add_argument("--caption", help="一句话介绍（自动生成默认）")
    parser.add_argument("--test", action="store_true", help="测试模式：只生成不发布")
    parser.add_argument("--type", choices=["news", "newspic"], default="newspic", help="文章类型")

    args = parser.parse_args()

    # 检查 API Key
    if not get_api_key():
        print("❌ 环境变量 WECHAT_API_KEY 未设置")
        return 1

    # 获取今日主题
    today = date.today()
    weekday_str = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][today.weekday()]

    # 生成标题
    if not args.title:
        args.title = f"📸 每日美女 | {weekday_str}"

    # 智能生成一句话介绍（根据场景、情绪等参数）
    if not args.caption:
        args.caption = generate_smart_caption(
            scene=args.scene or "",
            emotion=args.emotion or "",
            makeup=args.makeup or "",
            art_style=args.art_style or ""
        )

    print("=" * 50)
    print(f"📅 日期: {today}")
    print(f"📋 标题: {args.title}")
    print(f"💬 介绍: {args.caption}")
    if args.scene:
        print(f"🎬 场景: {args.scene}")
    if args.emotion:
        print(f"😊 情绪: {args.emotion}")
    print("=" * 50)

    # 生成图片
    images = generate_daily_images(args.count, args.style)

    if len(images) == 0:
        print("❌ 没有成功生成任何图片")
        return 1

    print(f"\n✅ 成功生成 {len(images)} 张图片")

    # 测试模式
    if args.test:
        print("\n🧪 测试模式：不发布到公众号")
        print("\n生成的图片链接:")
        for i, url in enumerate(images, 1):
            print(f"  {i}. {url}")
        return 0

    # 发布到公众号
    appid = args.appid or DEFAULT_APPID

    print(f"\n📤 正在发布到公众号...")

    # 构建图片和说明配对
    image_pairs = [(img, args.caption if i == 0 else "") for i, img in enumerate(images)]

    result = publish_to_wechat(
        appid=appid,
        title=args.title,
        content="",
        images=image_pairs,
        article_type=args.type
    )

    # 打印详细的API响应用于调试
    print(f"\n🔍 API响应: {json.dumps(result, ensure_ascii=False)}")

    # 修复：只有明确成功才算成功
    if result.get("success") is True or result.get("code") == "SUCCESS":
        print("✅ 发布成功！")
        print(f"📱 请到公众号后台查看草稿箱")
        return 0
    else:
        error_msg = result.get("error", "未知错误")
        error_code = result.get("code", "")
        print(f"❌ 发布失败: {error_msg}")
        if error_code:
            print(f"   错误代码: {error_code}")
        print(f"   完整响应: {result}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
