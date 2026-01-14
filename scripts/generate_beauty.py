#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美女生成 V4.0.1 ULTIMATE - 终极版本
- 场景和氛围全面升级
- 精准情绪控制
- 妆容风格系统
- 艺术风格选择
- 高级氛围营造
- 光影大师级控制
- 移除本地存储，仅返回在线URL
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import ssl
from datetime import date, datetime
from pathlib import Path

# 脚本目录
SCRIPT_DIR = Path(__file__).parent.absolute()
SKILL_DIR = SCRIPT_DIR.parent
LOGS_DIR = SKILL_DIR / "logs"

# API 配置
API_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
API_MODEL = "doubao-seedream-4-5-251128"
API_KEY = os.environ.get("DOUBAO_API_KEY")

# 检查 API Key
if not API_KEY:
    print("错误: 未设置 DOUBAO_API_KEY 环境变量")
    print("请运行: export DOUBAO_API_KEY='your-api-key'")
    sys.exit(1)

# 确保目录存在
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str, level: str = "INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [{level}] {message}"
    print(log_msg)

    log_file = LOGS_DIR / f"v4-{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")


# ============================================
# 场景和氛围系统 V4.0
# ============================================

ADVANCED_SCENES = {
    # 自然场景
    "樱花雨": "cherry blossom falling petals, pink flower petals floating in air, romantic spring atmosphere, soft focus background",
    "雨夜": "rainy night city street, wet pavement reflections, neon lights blurring, moody atmosphere, cinematic rain drops",
    "黄昏海滩": "golden hour beach, sunset warm orange sky, ocean waves, golden sand, dreamy warm atmosphere, lens flare",
    "雪山": "snow mountain landscape, white snow, blue sky, crisp cold air, fresh winter atmosphere, high contrast",
    "秋日森林": "autumn forest, falling golden leaves, warm sunlight through trees, nostalgic atmosphere, rich warm tones",

    # 城市场景
    "rooftop夜景": "city rooftop at night, skyline lights, bokeh city lights, urban atmosphere, dark sky with stars",
    "地铁": "subway station, modern interior, fluorescent lighting, urban mood, cinematic depth",
    "咖啡厅": "vintage coffee shop, warm interior lighting, cozy atmosphere, blurred background patrons",
    "豪华酒店": "luxury hotel room, elegant interior, warm ambient light, sophisticated atmosphere",

    # 艺术场景
    "艺术画廊": "art gallery, white walls, spot lighting, minimalist, sophisticated atmosphere",
    "废弃工厂": "abandoned industrial space, dramatic lighting, grunge texture, edgy atmosphere",
    "玻璃花房": "glass conservatory, plants everywhere, natural light, dreamy ethereal atmosphere",
    "复古房间": "vintage retro room, nostalgic decor, warm tones, nostalgic 90s atmosphere",

    # 特殊氛围
    "梦境": "surreal dream landscape, floating elements, soft pastel colors, fantasy atmosphere",
    "赛博朋克": "cyberpunk city, neon lights, futuristic, dark moody atmosphere, high contrast",
    "古风": "ancient Chinese palace, traditional architecture, red lanterns, classical atmosphere",
    "末日废土": "apocalyptic wasteland, dramatic sky, desaturated tones, cinematic atmosphere"
}

# 情绪控制系统
EMOTIONS = {
    "挑逗": "seductive gaze, playful smirk, flirty expression, alluring eyes, teasing body language, intimate atmosphere",
    "忧郁": "melancholic eyes, sad expression, longing gaze, emotional depth, sentimental atmosphere",
    "神秘": "enigmatic expression, mysterious gaze, unreadable emotions, intrigue, captivating presence",
    "开心": "genuine smile, joyful expression, bright eyes, happy energy, uplifting atmosphere",
    "高冷": "cold expression, distant gaze, aloof attitude, unapproachable aura, cool detachment",
    "温柔": "warm soft eyes, gentle smile, kind expression, nurturing aura, tender atmosphere",
    "自信": "confident gaze, self-assured expression, powerful presence, commanding aura",
    "俏皮": "playful expression, mischievous eyes, fun energy, lively personality"
}

# 妆容风格系统
MAKEUP_STYLES = {
    "裸妆": "natural no-makeup makeup, fresh-faced, minimal cosmetics, skin-focused",
    "韩妆": "K-style makeup, gradient lips, straight brows, innocent aegyo-sal, dewy skin",
    "欧美妆": "Western glam makeup, contoured, bold brows, matte lip, dramatic eyeliner",
    "日妆": "J-style makeup, soft blush, natural lips, sweet innocent look",
    "烟熏妆": "smokey eye makeup, dramatic eye definition, bold eyeliner, edgy look",
    "红唇妆": "classic red lip makeup, bold red lipstick, defined eyes, vintage glamour",
    "玻璃妆": "glass skin makeup, glowing skin, glossy lips, highlighter focus, dewy finish",
    "创意妆": "artistic creative makeup, bold colors, graphic liner, avant-garde style"
}

# 艺术风格系统
ART_STYLES = {
    "电影感": "cinematic style, film grain, color grading, movie still aesthetic, dramatic lighting",
    "复古胶片": "vintage film style, film grain, faded colors, retro 90s aesthetic, nostalgic",
    "王家卫": "Wong Kar-wai style, saturated colors, slow-motion feel, romantic melancholy, neon lights",
    "韩剧": "K-drama style, soft romantic lighting, dreamy filter, pastel colors, romantic comedy vibe",
    "时尚杂志": "high fashion magazine style, editorial photography, vogue aesthetic, sophisticated",
    "ins风": "Instagram style, warm tones, soft lighting, lifestyle aesthetic, influencer vibe",
    "暗调": "low key photography, dark moody atmosphere, dramatic shadows, cinematic noir",
    "清新日系": "Japanese fresh style, soft natural light, pastel tones, clean aesthetic, minimalist"
}

# 光影大师级控制
LIGHTING_SETUPS = {
    "黄金时刻": "golden hour lighting, warm orange sun, long shadows, magical atmosphere, lens flare",
    "蓝调时刻": "blue hour lighting, twilight blue sky, city lights turning on, moody atmosphere",
    "窗边自然光": "natural window light, soft diffused, gentle shadows, natural skin tones",
    "影棚柔光": "studio softbox lighting, even illumination, clean shadows, professional look",
    "侧光戏剧": "side lighting, dramatic shadows, chiaroscuro effect, emotional depth",
    "轮廓光": "rim lighting, backlighting, hair light, separation from background, ethereal glow",
    "顶光神圣": "top down lighting, butterfly lighting, glamorous old Hollywood style",
    "霓虹灯光": "neon light sources, colorful glow, cyberpunk atmosphere, vibrant colors"
}


def get_ultimate_profile(weekday: int, theme_name: str) -> dict:
    """终极人物档案"""
    import random

    ultimate_templates = {
        0: {  # 周一 - 多样化
            "faces": [
                "绝世女神，24岁，黄金比例五官，精致瓜子脸，柳叶弯眉，桃花电眼，高挺翘鼻，樱桃红唇，皮肤白皙如雪",
                "倾国倾城，23岁，教科书级颜值，鹅蛋脸，眉眼如画，迷离电眼，秀气小翘鼻，M唇形，皮肤通透发光",
                "祸国殃民级尤物，25岁，精致心形脸，韩式半永久眉，清澈桃花眼，精致鼻梁，微笑唇，皮肤水光肌"
            ],
            "hairs": [
                "黑茶色齐肩发，空气刘海，韩式微卷，发质光泽柔顺",
                "巧克力色长发，大波浪卷，慵懒风",
                "黑咖啡色高马尾，鬓角碎发修饰"
            ],
            "bodies": ["167cm 黄金比例身材", "165cm 模特身材", "168cm 女神身材"]
        },
        1: {  # 周二 - 清新自然
            "faces": [
                "初恋脸，22岁，清纯系，圆脸，平眉，杏眼，清新裸妆",
                "校园初恋，21岁，甜美脸型，清淡眉毛，无辜大眼",
                "初恋系女神，23岁，鹅蛋小脸，自然眉眼，清澈眼神"
            ],
            "hairs": [
                "黑色长发直发披肩，空气刘海",
                "深棕色齐肩发内扣",
                "栗色半扎发散发披肩"
            ],
            "bodies": ["163cm 纤细少女身材", "162cm 娇小玲珑", "164cm 清瘦身材"]
        },
        2: {  # 周三 - 知性优雅
            "faces": [
                "知性御姐，26岁，成熟精致脸，优雅眉眼，智慧眼神",
                "职场女强人，27岁，精致五官，沉稳眼神",
                "优雅女性，25岁，清秀脸型，温婉眉眼"
            ],
            "hairs": [
                "深色低盘发优雅知性",
                "咖啡色波浪卷发披肩",
                "黑色侧分短发干练"
            ],
            "bodies": ["168cm 高挑身材", "166cm 匀称身材", "167cm 纤细优雅"]
        },
        3: {  # 周四 - 冷艳高冷
            "faces": [
                "冷艳女王，25岁，锋利五官，细长眉眼，犀利眼神",
                "高冷御姐，26岁，精致立体五官，冷冽眼神",
                "冰山美人，24岁，精致脸型，细眉凤眼"
            ],
            "hairs": [
                "黑色大波浪披肩气场全开",
                "深棕长直发中分",
                "黑色高马尾干练冷艳"
            ],
            "bodies": ["170cm 高挑S曲线", "168cm 模特身材", "169cm 纤细高挑"]
        },
        4: {  # 周五 - 可爱甜美
            "faces": [
                "甜心少女，20岁，圆脸可爱，圆眼灵动",
                "娃娃脸，19岁，可爱脸型大眼睛",
                "甜美系女神，21岁，甜美脸型笑眼盈盈"
            ],
            "hairs": [
                "棕色波波头甜美可爱",
                "粉色挑染双马尾",
                "栗色齐肩发甜美内扣"
            ],
            "bodies": ["160cm 娇小可爱", "161cm 纤细娇小", "162cm 清瘦可爱"]
        },
        5: {  # 周六 - 时尚潮流
            "faces": [
                "超模脸，24岁，高级脸立体五官",
                "潮流达人，23岁，个性化五官",
                "时尚博主，25岁，精致脸型"
            ],
            "hairs": [
                "银灰色短发潮流",
                "黑色狼尾发型个性",
                "亚麻色层次长发"
            ],
            "bodies": ["175cm 超模身材", "173cm 高挑纤细", "174cm 修长身材"]
        },
        6: {  # 周日 - 温暖治愈
            "faces": [
                "温柔女神，24岁，柔和五官温柔眉眼",
                "恬静美女，25岁，温婉脸型",
                "治愈系美人，23岁，温柔脸型"
            ],
            "hairs": [
                "黑色微卷长发披肩",
                "浅棕色齐肩发自然卷",
                "栗色低马尾温柔"
            ],
            "bodies": ["165cm 纤细温柔", "164cm 清瘦温柔", "166cm 纤细优雅"]
        }
    }

    daily_seed = int(date.today().strftime("%Y%m%d"))
    random.seed(daily_seed)

    template = ultimate_templates.get(weekday, ultimate_templates[0])

    return {
        "face": random.choice(template["faces"]),
        "hair": random.choice(template["hairs"]),
        "body": random.choice(template["bodies"])
    }


def build_ultimate_prompt_v4(profile: dict, pose_info: dict, params: dict) -> str:
    """
    构建终极 prompt V4.0
    包含场景、氛围、情绪、妆容、艺术风格、光影
    """

    face = profile["face"]
    hair = profile["hair"]
    body = profile["body"]

    # 获取用户选择的参数
    scene = params.get("scene", "影棚高级背景，简洁大气")
    emotion = params.get("emotion", "")
    makeup = params.get("makeup", "")
    art_style = params.get("art_style", "")
    lighting = params.get("lighting", "专业影棚光均匀照明")

    # 姿态
    pose = pose_info["pose"]
    camera = pose_info["camera"]

    # 服装（根据情绪调整）
    emotion_key = params.get("emotion_key", "")
    outfits = {
        "挑逗": "黑色蕾丝连衣裙深V设计高开叉诱惑优雅",
        "忧郁": "白色连衣裙简约设计忧伤气质",
        "神秘": "深紫色吊带裙神秘优雅",
        "开心": "彩色碎花连衣裙活泼可爱",
        "高冷": "黑色西装套装干练高冷",
        "温柔": "米色针织套装温柔知性",
        "自信": "红色修身连衣裙自信魅力",
        "俏皮": "牛仔短套装俏皮可爱"
    }

    outfit = outfits.get(emotion_key, "白色真丝衬衫微透领口微敞")

    # 构建完整 prompt
    parts = []

    # 1. 基础质量词
    parts.append("masterpiece best quality ultra detailed 8K UHD")

    # 2. 艺术风格（如果有）
    if art_style:
        parts.append(art_style)

    # 3. 主体描述
    parts.append(f"portrait photography {face} {body} {hair}")

    # 4. 妆容（如果有）
    if makeup:
        parts.append(f"makeup: {makeup}")

    # 5. 服装
    parts.append(f"wearing {outfit}")

    # 6. 情绪（如果有）
    if emotion:
        parts.append(f"emotion: {emotion}")

    # 7. 姿态
    parts.append(pose)

    # 8. 场景
    parts.append(f"scene: {scene}")

    # 9. 光影
    parts.append(f"lighting: {lighting}")

    # 10. 相机参数
    parts.append(camera)

    # 11. 额外增强词
    parts.extend([
        "perfect composition color grading post-processing",
        "skin texture visible pores eyelashes detail hair strands detail",
        "attractive charming feminine beauty elegant sexy",
        "professional photography fashion magazine"
    ])

    prompt = ", ".join(parts)
    prompt = prompt.replace(", ", ", ").strip()

    # 清理多余空格
    while "  " in prompt:
        prompt = prompt.replace("  ", " ")

    return prompt


def generate_image_ultimate(prompt: str, reference_url: str = None, use_img2img: bool = False) -> dict:
    """终极图片生成"""

    payload = {
        "model": API_MODEL,
        "prompt": prompt,
        "size": "2k",
        "response_format": "url",
        "watermark": False
    }

    if use_img2img and reference_url:
        payload["image"] = reference_url
        log(f"📎 图生图模式")

    ssl_context = ssl._create_unverified_context()

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            API_ENDPOINT,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {API_KEY}'
            },
            method='POST'
        )

        with urllib.request.urlopen(req, context=ssl_context, timeout=90) as response:
            if response.status == 200:
                response_data = response.read().decode('utf-8')
                data = json.loads(response_data)

                if "data" in data and len(data["data"]) > 0:
                    return {"success": True, "url": data["data"][0].get("url")}

        return {"success": False, "error": "API 响应异常"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_ultimate_series_v4(count: int = 3, params: dict = None) -> dict:
    """V4.0 终极系列生成"""

    print("=" * 70)
    print("👑 美女生成 V4.0.1 ULTIMATE - 场景氛围升级版")
    print("=" * 70)

    today = date.today()
    weekday = today.weekday()
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    theme_names = {
        0: "多样化", 1: "清新自然", 2: "知性优雅",
        3: "冷艳高冷", 4: "可爱甜美", 5: "时尚潮流", 6: "温暖治愈"
    }

    params = params or {}
    actual_theme = params.get("theme", theme_names.get(weekday, "多样化"))

    print(f"\n📅 日期: {today}")
    print(f"📆 星期: {weekday_names[weekday]}")
    print(f"🎨 主题: {actual_theme}")

    # 显示参数
    print(f"\n🎛️  精准控制参数:")
    print(f"   🎬 场景: {params.get('scene', '影棚')}")
    print(f"   😊 情绪: {params.get('emotion_key', '默认')}")
    print(f"   💄 妆容: {params.get('makeup_key', '默认')}")
    print(f"   🎨 艺术风格: {params.get('art_style_key', '默认')}")
    print(f"   💡 光影: {params.get('lighting_key', '默认')}")

    # 生成档案
    profile = get_ultimate_profile(weekday, actual_theme)
    print(f"\n👤 人物档案:")
    print(f"   {profile['face']}")
    print(f"   {profile['hair']}")

    # 姿态
    poses = [
        {
            "name": "极致特写",
            "pose": "extreme close-up portrait seductive eyes looking at camera natural lips slightly parted hands touching face collarbone visible alluring charm"
        },
        {
            "name": "完美侧颜",
            "pose": "perfect profile 45 degree angle looking back mesmerizing eyes hair blowing across face thoughtful sexy expression beautiful profile neckline"
        },
        {
            "name": "全身魅力",
            "pose": "full body shot elegant pose hands visible natural gesture confident smile sunlight rim light dress flowing dynamic beauty feminine charm complete fingers detailed"
        }
    ]

    cameras = [
        "85mm f/1.2 ultra shallow DOF bokeh dreamy",
        "100mm f/1.4 telephoto creamy bokeh soft focus",
        "50mm f/1.8 standard lens natural perspective"
    ]

    # 生成 prompts
    print(f"\n✍️  生成 {count} 个终极 prompt...")
    prompts = []

    for i in range(min(count, len(poses))):
        pose_info = {"pose": poses[i]["pose"], "camera": cameras[i]}
        prompt = build_ultimate_prompt_v4(profile, pose_info, params)
        prompts.append({
            "index": i + 1,
            "name": poses[i]["name"],
            "prompt": prompt
        })

    print("\n📋 Prompt 预览:")
    for p in prompts:
        print(f"\n   {p['index']}. {p['name']}:")
        print(f"   {p['prompt'][:150]}...")

    # 生成
    print("\n" + "=" * 70)
    print(f"🎨 开始生成 {count} 张图片...")
    print("=" * 70)

    images = []
    reference_url = None
    success_count = 0

    for i, prompt_info in enumerate(prompts):
        idx = prompt_info["index"]
        prompt_text = prompt_info["prompt"]
        name = prompt_info["name"]
        use_img2img = (i > 0) and (reference_url is not None)

        print(f"\n📸 生成图片 {idx} - {name}...")
        if use_img2img:
            print(f"   📎 图生图模式")

        result = generate_image_ultimate(prompt_text, reference_url, use_img2img)

        if result["success"]:
            url = result["url"]
            if i == 0:
                reference_url = url

            images.append({
                "index": idx,
                "name": name,
                "url": url
            })
            success_count += 1
            print(f"   ✅ 完成: {url}")
        else:
            print(f"   ❌ 失败: {result.get('error')}")

        if i < len(prompts) - 1:
            time.sleep(2)

    print("\n" + "=" * 70)
    print(f"✅ 生成完成: {success_count}/{count}")
    print("=" * 70)

    return {
        "success": success_count == count,
        "count": success_count,
        "total": count,
        "profile": profile,
        "images": images,
        "params": params
    }


def main():
    parser = argparse.ArgumentParser(
        description="美女生成 V4.0.1 ULTIMATE - 场景氛围升级"
    )

    parser.add_argument("--count", "-c", type=int, default=3, help="生成数量")
    parser.add_argument("--theme", "-t", help="主题")
    parser.add_argument("--scene", "-s", help=f"场景: {', '.join(list(ADVANCED_SCENES.keys())[:5])}...")
    parser.add_argument("--emotion", "-e", help=f"情绪: {', '.join(list(EMOTIONS.keys())[:5])}...")
    parser.add_argument("--makeup", "-m", help=f"妆容: {', '.join(list(MAKEUP_STYLES.keys())[:5])}...")
    parser.add_argument("--art-style", "-a", help=f"艺术风格: {', '.join(list(ART_STYLES.keys())[:5])}...")
    parser.add_argument("--lighting", "-l", help=f"光影: {', '.join(list(LIGHTING_SETUPS.keys())[:5])}...")
    parser.add_argument("--show-prompts", action="store_true", help="只显示 prompt")
    parser.add_argument("--list-options", action="store_true", help="列出所有选项")

    args = parser.parse_args()

    # 列出选项
    if args.list_options:
        print("\n" + "=" * 70)
        print("🎬 场景选项:")
        print("=" * 70)
        for k, v in ADVANCED_SCENES.items():
            print(f"  • {k}: {v[:60]}...")

        print("\n" + "=" * 70)
        print("😊 情绪选项:")
        print("=" * 70)
        for k, v in EMOTIONS.items():
            print(f"  • {k}: {v[:60]}...")

        print("\n" + "=" * 70)
        print("💄 妆容选项:")
        print("=" * 70)
        for k, v in MAKEUP_STYLES.items():
            print(f"  • {k}: {v[:60]}...")

        print("\n" + "=" * 70)
        print("🎨 艺术风格选项:")
        print("=" * 70)
        for k, v in ART_STYLES.items():
            print(f"  • {k}: {v[:60]}...")

        print("\n" + "=" * 70)
        print("💡 光影选项:")
        print("=" * 70)
        for k, v in LIGHTING_SETUPS.items():
            print(f"  • {k}: {v[:60]}...")

        return 0

    # 构建参数
    params = {
        "theme": args.theme,
        "scene": ADVANCED_SCENES.get(args.scene, ""),
        "emotion": EMOTIONS.get(args.emotion, ""),
        "emotion_key": args.emotion,
        "makeup": MAKEUP_STYLES.get(args.makeup, ""),
        "makeup_key": args.makeup,
        "art_style": ART_STYLES.get(args.art_style, ""),
        "art_style_key": args.art_style,
        "lighting": LIGHTING_SETUPS.get(args.lighting, ""),
        "lighting_key": args.lighting
    }

    if args.show_prompts:
        today = date.today()
        weekday = today.weekday()
        theme_names = {
            0: "多样化", 1: "清新自然", 2: "知性优雅",
            3: "冷艳高冷", 4: "可爱甜美", 5: "时尚潮流", 6: "温暖治愈"
        }
        params["theme"] = params.get("theme", theme_names.get(weekday, "多样化"))
        profile = get_ultimate_profile(weekday, params["theme"])

        poses = [
            {"pose": "extreme close-up", "camera": "85mm f/1.2"},
            {"pose": "perfect profile", "camera": "100mm f/1.4"},
            {"pose": "full body", "camera": "50mm f/1.8"}
        ]

        print("=" * 70)
        print("👑 V4.0.1 Prompt 预览")
        print("=" * 70)
        print(f"\n参数: {params}")

        for i in range(3):
            prompt = build_ultimate_prompt_v4(profile, poses[i], params)
            print(f"\n图片 {i+1}:")
            print(f"{prompt}")

        return 0

    # 生成
    result = generate_ultimate_series_v4(args.count, params)

    if result["success"]:
        print("\n🎉 全部成功！\n")
        for img in result["images"]:
            print(f"  {img['index']}. {img['name']}")
            print(f"     {img['url']}")
        return 0
    else:
        print(f"\n⚠️  部分失败 ({result['count']}/{result['total']})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
