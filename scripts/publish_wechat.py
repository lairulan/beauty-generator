#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号发布脚本 V10.0
将生成的美女图片发布到公众号草稿箱（小绿书形式）
"""

import argparse
import json
import os
import subprocess
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, date
from pathlib import Path

# 脚本目录
SCRIPT_DIR = Path(__file__).parent.absolute()
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
GENERATE_SCRIPT = SKILL_DIR / "scripts" / "generate.py"
BEAUTY_GENERATE_SCRIPT = SKILL_DIR / "scripts" / "generate_beauty.py"
ARTISTIC_GENERATE_SCRIPT = SKILL_DIR / "scripts" / "generate_artistic.py"

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
    payload = json.dumps(data or {}, ensure_ascii=False).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            },
            method="POST"
        )
        # TODO: 临时跳过 SSL 验证（wx.limyai.com 证书过期），恢复后删除 ssl_ctx
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=60, context=ssl_ctx) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"success": False, "error": f"HTTP {e.code}: {body[:200]}"}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"连接失败: {e.reason}"}
    except json.JSONDecodeError:
        return {"success": False, "error": "响应 JSON 解析失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_caption_from_meta(meta: dict) -> str:
    """基于图片元数据动态生成配文（与图片内容贴合）

    meta 结构: {scene_type, outfit_style, expression_type, lighting_type, art_style}
    """
    import random

    scene = meta.get("scene_type", "")
    outfit = meta.get("outfit_style", "")
    expression = meta.get("expression_type", "")
    lighting = meta.get("lighting_type", "")
    art = meta.get("art_style", "")

    # --- 场景描写片段 ---
    scene_phrases = {
        "自然": ["山野间的风", "绿意盎然的画面", "大自然最好的滤镜", "清风与花香交织"],
        "海滩": ["海风轻抚的瞬间", "浪花写下的情书", "海与天的交界处", "被海风吹乱的温柔"],
        "花田": ["花海里的少女心事", "花瓣落满肩头", "被花包围的浪漫", "春天专属的色彩"],
        "城市": ["城市光影中的故事", "街角的一抹亮色", "都市里的片刻宁静", "水泥森林中的柔软"],
        "街头": ["街拍质感满分", "街角转弯遇见美好", "城市漫步的随性", "人潮中最亮眼的存在"],
        "室内": ["窗边光影的温柔", "阳光洒进来的午后", "室内的安静时光", "光线最好的角落"],
        "咖啡厅": ["咖啡香里的慵懒", "一杯拿铁的时光", "午后咖啡馆的邂逅", "慢下来，享受此刻"],
        "古建筑": ["青砖黛瓦间的古典美", "时光在这里停驻", "古韵与美人相得益彰", "历史与美的对话"],
        "特殊": ["独特氛围感拉满", "不一样的视角", "光影交错中的故事", "氛围感这一块拿捏住了"],
    }

    # --- 表情描写片段 ---
    expr_phrases = {
        "甜美微笑": ["甜度爆表", "笑容是最好的滤镜", "嘴角上扬的弧度刚好", "笑起来眼睛弯弯的"],
        "优雅端庄": ["优雅是骨子里的气质", "举手投足间的从容", "美得不动声色", "端庄中透着温度"],
        "俏皮灵动": ["古灵精怪招人爱", "灵动的眼神会说话", "元气少女上线", "可爱值已超标"],
        "冷艳高贵": ["气场全开", "高冷中透着迷人", "疏离感刚刚好", "清冷如月的美"],
        "性感妩媚": ["眼角眉梢全是故事", "风情万种不过如此", "这种美，带着温度", "靠近是本能"],
        "文艺知性": ["书卷气自成风景", "知性是最高级的性感", "文艺范十足", "眉目间的故事感"],
        "清纯自然": ["清水出芙蓉", "不施粉黛的美好", "干净得像一阵风", "最纯粹的样子"],
    }

    # --- 光影描写片段 ---
    light_phrases = {
        "自然光": ["自然光就是最好的打光师", "光线温柔得刚好", "阳光帮你做造型"],
        "黄金时刻": ["黄金时刻的魔法", "夕阳把一切都镀了金", "日落是最浪漫的滤镜"],
        "柔和室内光": ["窗边的柔光最温柔", "光影交织的安静", "被光线偏爱的角落"],
    }

    # --- 穿搭描写片段 ---
    outfit_phrases = {
        "优雅": ["优雅是永不过时的时尚", "精致到每一个细节"],
        "性感": ["恰到好处的性感", "美得让人心跳加速"],
        "清新": ["清新感扑面而来", "像春风一样舒服"],
        "时尚": ["时尚嗅觉满分", "走在潮流前端"],
        "古典": ["古典韵味十足", "穿越时光的美"],
        "运动": ["活力值拉满", "运动女孩最迷人"],
    }

    # 从各维度随机选一个片段组合
    parts = []

    if scene and scene in scene_phrases:
        parts.append(random.choice(scene_phrases[scene]))
    elif scene:
        parts.append(f"{scene}里的故事")

    if expression and expression in expr_phrases:
        parts.append(random.choice(expr_phrases[expression]))

    if not parts:
        if lighting and lighting in light_phrases:
            parts.append(random.choice(light_phrases[lighting]))

    if not parts:
        if outfit and outfit in outfit_phrases:
            parts.append(random.choice(outfit_phrases[outfit]))

    # 保底：至少有一句
    if not parts:
        fallback = ["今日份心动瞬间", "美好值得被定格", "每一帧都是风景",
                     "镜头里的温柔", "光影之间的故事", "被美好击中的瞬间"]
        parts.append(random.choice(fallback))

    # 组合：1-2 句，用逗号或句号连接
    if len(parts) >= 2:
        return f"{parts[0]}，{parts[1]}。"
    else:
        return f"{parts[0]}。"


def generate_tags_from_meta(meta: dict) -> str:
    """基于图片元数据动态生成话题标签"""
    tags = ["#每日美女", "#写真"]

    scene = meta.get("scene_type", "")
    expression = meta.get("expression_type", "")
    art = meta.get("art_style", "")

    # 场景标签
    scene_tags = {
        "自然": "#户外写真", "海滩": "#海边", "花田": "#花海",
        "城市": "#街拍", "街头": "#街拍", "室内": "#室内写真",
        "咖啡厅": "#咖啡时光", "古建筑": "#国风", "特殊": "#创意摄影",
    }
    if scene in scene_tags:
        tags.append(scene_tags[scene])

    # 表情/风格标签
    expr_tags = {
        "甜美微笑": "#甜美", "优雅端庄": "#优雅", "俏皮灵动": "#元气少女",
        "冷艳高贵": "#高冷范", "性感妩媚": "#性感", "文艺知性": "#文艺范",
        "清纯自然": "#清纯",
    }
    if expression in expr_tags:
        tags.append(expr_tags[expression])

    # 艺术风格标签
    art_tags = {
        "电影感": "#电影感", "胶片": "#胶片质感", "日系": "#日系",
        "ins风": "#ins风",
    }
    if art in art_tags:
        tags.append(art_tags[art])

    # 固定尾部标签
    tags.append("#人像摄影")
    tags.append("#今日心动")

    return " ".join(tags[:6])  # 最多 6 个标签


def generate_smart_caption(scene: str = "", emotion: str = "", makeup: str = "", art_style: str = "") -> str:
    """兼容旧接口：无元数据时使用"""
    return generate_caption_from_meta({
        "scene_type": scene,
        "expression_type": emotion,
        "art_style": art_style,
    })


def generate_one_line_caption(style: str = "") -> str:
    """生成一句话介绍（兼容旧接口）"""
    return generate_smart_caption()


def publish_to_wechat(
    appid: str,
    title: str,
    content: str,
    images: list,
    article_type: str = "newspic",
    **kwargs
):
    """发布到公众号草稿箱"""

    # 小绿书格式：图文混排
    if article_type == "newspic":
        # 构建小绿书内容 - 移除 alt text 避免"图片"文字出现
        content_lines = []
        first_meta = {}
        for i, (img_url, caption) in enumerate(images):
            content_lines.append(f"![]({img_url})")
            if caption:
                content_lines.append(f"\n{caption}\n")

        # 动态标签（基于元数据或默认）
        tags = kwargs.get("tags", "#每日美女 #写真 #人像摄影 #今日心动")
        content_lines.append(f"\n{tags}")

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


def _extract_images_with_meta(output: str) -> list:
    """从脚本输出中提取图片 URL 和 META 元数据

    返回: [(url, meta_dict), ...]
    META 行格式: META:场景|穿搭|表情|光影|艺术风格
    """
    import re
    results = []
    lines = output.split("\n")

    for i, line in enumerate(lines):
        if "http" not in line:
            continue
        # 匹配所有已知图片 URL 来源
        if any(domain in line for domain in [
            "ark-content", "doubao", "volces.com",
            "imgbb", "i.ibb.co", "ibb.co",
            "imgur.com",
            "sm.ms", "loli.net",
        ]):
            urls = re.findall(r'https?://[^\s\)\]"\']+', line)
            for url in urls:
                # 向后查找对应的 META 行
                meta = {}
                for j in range(i + 1, min(i + 3, len(lines))):
                    if lines[j].strip().startswith("META:"):
                        parts = lines[j].strip()[5:].split("|")
                        if len(parts) >= 5:
                            meta = {
                                "scene_type": parts[0],
                                "outfit_style": parts[1],
                                "expression_type": parts[2],
                                "lighting_type": parts[3],
                                "art_style": parts[4],
                            }
                        break
                results.append((url, meta))
    return results


def _extract_image_urls(output: str) -> list:
    """兼容旧接口：只返回 URL 列表"""
    return [url for url, _ in _extract_images_with_meta(output)]


def generate_daily_images(count: int = 3, style: str = "", emotion: str = "") -> list:
    """
    生成多张一致性人物图片
    使用双引擎 (Google Imagen 4 Ultra + Doubao Seedream 4.5)

    返回: [(url, meta_dict), ...]  meta 含 scene_type/outfit_style/expression_type/lighting_type/art_style
    """
    import re

    images_with_meta = []

    print(f"\n🎨 [双引擎] 正在生成 {count} 张图片 (Google Imagen → 豆包 fallback)...")

    cmd = [
        "python3", str(BEAUTY_GENERATE_SCRIPT),
        "--count", str(count)
    ]
    if style:
        cmd.extend(["--style", style])
    if emotion:
        cmd.extend(["--emotion", emotion])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env=os.environ
        )

        # 打印生成脚本的关键日志（引擎选择、提示词摘要等）
        if result.stdout:
            for line in result.stdout.split("\n"):
                if any(kw in line for kw in ["[Google]", "[豆包]", "👤", "风格:", "脸型:", "Prompt:", "随机种子", "✅", "❌", "⚠️", "降级", "http", "全部成功", "META:"]):
                    print(f"  {line.strip()}")

        images_with_meta = _extract_images_with_meta(result.stdout)

        if result.returncode == 0 and len(images_with_meta) > 0:
            print(f"  ✅ 成功生成 {len(images_with_meta)} 张图片")
            return images_with_meta

        print(f"  ❌ 生成失败（返回码: {result.returncode}, 图片数: {len(images_with_meta)}）")
        if result.stderr:
            print(f"  错误: {result.stderr[:500]}")
        if result.stdout and not images_with_meta:
            print(f"  完整输出: {result.stdout[-500:]}")

    except subprocess.TimeoutExpired:
        print("  ❌ 生成超时 (300s)")
    except Exception as e:
        print(f"  ❌ 生成异常: {e}")

    return images_with_meta


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

    # 生成图片（返回 [(url, meta), ...]）
    images_with_meta = generate_daily_images(args.count, args.style, args.emotion or "")

    if len(images_with_meta) == 0:
        print("❌ 没有成功生成任何图片")
        return 1

    print(f"\n✅ 成功生成 {len(images_with_meta)} 张图片")

    # 测试模式
    if args.test:
        print("\n🧪 测试模式：不发布到公众号")
        print("\n生成的图片链接:")
        for i, (url, meta) in enumerate(images_with_meta, 1):
            caption = generate_caption_from_meta(meta) if meta else "今日份心动瞬间。"
            tags = generate_tags_from_meta(meta) if meta else "#每日美女 #写真 #人像摄影 #今日心动"
            print(f"  {i}. {url}")
            print(f"     配文: {caption}")
            print(f"     标签: {tags}")
        return 0

    # 发布到公众号
    appid = args.appid or DEFAULT_APPID

    print(f"\n📤 正在发布到公众号...")

    # 构建图片和说明配对 - 基于元数据动态生成配文
    image_pairs = []
    first_meta = {}
    for i, (img_url, meta) in enumerate(images_with_meta):
        if i == 0:
            first_meta = meta or {}
        caption = generate_caption_from_meta(meta) if meta else generate_smart_caption()
        image_pairs.append((img_url, caption))

    # 基于第一张图的元数据生成动态标签
    dynamic_tags = generate_tags_from_meta(first_meta) if first_meta else "#每日美女 #写真 #人像摄影 #今日心动"
    print(f"🏷️ 标签: {dynamic_tags}")

    result = publish_to_wechat(
        appid=appid,
        title=args.title,
        content="",
        images=image_pairs,
        article_type=args.type,
        tags=dynamic_tags
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
