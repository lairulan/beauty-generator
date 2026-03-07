#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美女生成 V6.0 - 纯文生图 4K 高清系统
- 从丰富的元素库中随机组合
- 确保每次生成都有新鲜感
- 严格东方美女风格
- 基于 Civitai/Stable Diffusion 社区最佳实践
- 使用 4K 分辨率纯文生图，不再使用图生图（避免质量降低）
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.request
import ssl
from datetime import date, datetime
from pathlib import Path

# 脚本目录
SCRIPT_DIR = Path(__file__).parent.absolute()
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
LOGS_DIR = SKILL_DIR / "logs"

# API 配置
API_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
API_MODEL = "doubao-seedream-4-5-251128"
API_KEY = os.environ.get("DOUBAO_API_KEY")

# 确保目录存在
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str, level: str = "INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [{level}] {message}"
    print(log_msg)

    log_file = LOGS_DIR / f"v6-{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")


def load_prompt_library() -> dict:
    """加载 Prompt 元素库"""
    library_path = CONFIG_DIR / "prompt_library.json"
    if library_path.exists():
        with open(library_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        log("警告: 未找到 prompt_library.json，使用内置默认值", "WARN")
        return get_default_library()


def get_default_library() -> dict:
    """内置默认元素库（从 generate_artistic.py 高质量元素库补充）"""
    return {
        "base_quality": [
            "RAW photo, masterpiece, best quality, ultra detailed, 8K UHD, DSLR",
            "masterpiece, best quality, ultra realistic, 8k resolution, photorealistic",
            "professional photography, masterpiece, ultra high resolution 8K, RAW photo, super sharp",
            "cinematic photo, masterpiece, best quality, hyper-detailed, 8K HDR, ultra crisp",
            "award-winning photography, masterpiece, ultra detailed, film grain, Fujifilm XT3"
        ],
        "asian_identity": [
            "East Asian Chinese young woman, Asian facial features, Asian beauty",
            "beautiful Chinese woman, delicate Asian features, oriental beauty",
            "gorgeous East Asian girl, Chinese facial structure, natural Asian beauty",
            "stunning Asian woman in her early twenties, Chinese heritage, elegant oriental features",
            "young Chinese beauty, refined Asian facial features, porcelain skin"
        ],
        "face_types": {
            "甜美系": [
                "sweet innocent face, round cheeks, bright sparkling eyes, cherry lips, dimples when smiling",
                "baby face, cute round eyes, small nose, natural pink lips, youthful glow",
                "adorable face, aegyo sal, gradient lips, innocent expression, glowing skin"
            ],
            "清纯系": [
                "pure innocent face, clear bright eyes, natural beauty, fresh clean look",
                "girl-next-door face, natural features, minimal makeup look, clear skin",
                "fresh-faced beauty, dewy skin, natural brows, innocent gaze"
            ],
            "御姐系": [
                "mature elegant face, sharp jawline, sophisticated features, intense gaze",
                "queen-like features, high cheekbones, defined brows, powerful presence",
                "fierce beautiful face, strong bone structure, captivating eyes, confident expression"
            ],
            "知性系": [
                "intellectual beauty, refined features, wise gentle eyes, elegant expression",
                "sophisticated face, graceful features, thoughtful gaze, cultured appearance",
                "classic beauty, timeless features, intelligent eyes, poised expression"
            ],
            "冷艳系": [
                "cold beauty, sharp features, icy gaze, mysterious allure, pale skin",
                "aloof gorgeous face, sculpted features, distant expression, ethereal beauty",
                "frost queen features, piercing eyes, perfect bone structure, cool elegance"
            ],
            "性感系": [
                "seductive face, full lips, bedroom eyes, sultry expression, flawless skin",
                "alluring features, smoldering gaze, pouty lips, sensual charm",
                "glamorous face, defined cheekbones, smokey eyes, irresistible beauty"
            ]
        },
        "hair_styles": [
            "long silky black hair flowing in wind, glossy healthy shine",
            "shoulder-length dark brown hair with subtle waves, natural movement",
            "elegant updo with loose face-framing tendrils, sophisticated style",
            "sleek straight black hair, mirror-like shine, razor-cut ends",
            "soft romantic curls, chestnut brown, bouncy volume",
            "messy beach waves, sun-kissed highlights, effortless style",
            "high ponytail, sleek and polished, face-lifting effect",
            "bob cut with blunt bangs, modern chic, face-framing",
            "long layered hair with curtain bangs, soft feminine look",
            "half-up half-down style, romantic braids, ethereal beauty"
        ],
        "skin_textures": [
            "flawless porcelain skin, visible pores, natural skin texture, healthy glow",
            "dewy glass skin, luminous complexion, subtle skin details, radiant",
            "creamy smooth skin, natural texture, soft focus, photorealistic",
            "honey-toned skin, warm undertones, healthy natural glow, detailed texture",
            "milky white skin, translucent quality, delicate texture, ethereal glow"
        ],
        "body_types": [
            "slim elegant figure, graceful proportions, model-like silhouette",
            "petite delicate frame, feminine curves, youthful figure",
            "tall slender body, long legs, elegant posture, statuesque",
            "fit toned body, healthy athletic build, graceful strength",
            "soft feminine curves, hourglass silhouette, elegant proportions"
        ],
        "outfits": {
            "优雅": [
                "elegant silk evening gown, flowing fabric, subtle shimmer",
                "sophisticated cocktail dress, classic cut, refined elegance",
                "designer blazer with matching skirt, professional chic",
                "cashmere sweater with pearl accessories, understated luxury"
            ],
            "性感": [
                "form-fitting red dress with subtle slit, alluring elegance",
                "black lace top with silk camisole underneath, sophisticated sexy",
                "off-shoulder sweater dress, showing collarbone, cozy sensual",
                "satin slip dress, delicate straps, elegant curves"
            ],
            "清新": [
                "white cotton sundress with floral embroidery, fresh innocent",
                "light blue oversized shirt, effortless casual, girl-next-door",
                "pastel cardigan with white tee, soft feminine layers",
                "linen midi skirt with simple blouse, natural aesthetic"
            ],
            "时尚": [
                "designer trench coat, street style chic, fashion-forward",
                "leather jacket with vintage band tee, edgy cool",
                "high-waisted jeans with crop top, trendy casual",
                "oversized blazer as dress, power dressing, modern"
            ],
            "古典": [
                "traditional cheongsam qipao, intricate embroidery, cultural elegance",
                "modern hanfu-inspired dress, flowing sleeves, ethereal",
                "vintage-style tea dress, retro feminine, timeless charm"
            ],
            "运动": [
                "yoga outfit, athletic wear, healthy lifestyle aesthetic",
                "tennis skirt with polo top, sporty chic, preppy style",
                "casual athleisure, matching set, comfortable elegance"
            ]
        },
        "poses": {
            "特写": [
                "extreme close-up portrait, looking directly at camera, captivating gaze",
                "face close-up, chin slightly tilted, mysterious expression",
                "intimate portrait, eyes half-closed, dreamy sensual look",
                "profile close-up, perfect side angle, elegant neck line visible"
            ],
            "半身": [
                "upper body shot, hands near face, graceful gesture",
                "waist-up portrait, one hand touching hair, natural pose",
                "elegant seated pose, hands in lap, refined posture",
                "leaning forward slightly, engaging expression, dynamic composition"
            ],
            "全身": [
                "full body standing pose, weight on one leg, natural S-curve",
                "walking pose, hair and clothes in motion, dynamic energy",
                "seated cross-legged, relaxed elegant posture, approachable",
                "leaning against wall, casual confident stance, editorial style"
            ],
            "动态": [
                "hair flipping in motion, dynamic movement, frozen moment",
                "twirling in dress, fabric flowing, joyful energy",
                "reaching up gracefully, elongated silhouette, dancer-like",
                "looking back over shoulder, mysterious allure, dynamic angle"
            ]
        },
        "expressions": {
            "微笑": [
                "gentle natural smile, eyes crinkled with joy, warm genuine",
                "subtle mysterious smile, Mona Lisa expression, intriguing",
                "bright cheerful smile, showing teeth, infectious happiness"
            ],
            "性感": [
                "sultry gaze, lips slightly parted, smoldering intensity",
                "bedroom eyes, seductive half-smile, alluring charm",
                "confident sexy smirk, direct eye contact, magnetic presence"
            ],
            "冷艳": [
                "icy cold stare, emotionless beauty, intimidating elegance",
                "aloof distant expression, untouchable aura, mysterious",
                "piercing intense gaze, strong silent type, powerful presence"
            ],
            "忧郁": [
                "melancholic gaze, wistful expression, poetic sadness",
                "thoughtful distant look, introspective mood, emotional depth"
            ],
            "自信": [
                "confident direct gaze, empowered expression, boss energy",
                "self-assured smile, knowing look, powerful feminine",
                "fierce determined expression, unstoppable energy, inspiring"
            ]
        },
        "scenes": {
            "自然": [
                "cherry blossom garden, pink petals falling, spring romance",
                "golden wheat field at sunset, warm summer glow, pastoral beauty",
                "misty bamboo forest, zen atmosphere, oriental mystique",
                "seaside at golden hour, waves gently lapping, peaceful serenity",
                "autumn maple forest, red and gold leaves, nostalgic warmth",
                "lavender field in Provence, purple haze, dreamy romantic"
            ],
            "城市": [
                "Tokyo neon-lit street at night, urban glamour, cyberpunk vibe",
                "Parisian cafe terrace, vintage charm, romantic atmosphere",
                "New York rooftop at sunset, skyline backdrop, metropolitan chic",
                "Shanghai Bund at blue hour, city lights, modern luxury",
                "rainy city street, reflections on wet pavement, cinematic mood",
                "luxury hotel lobby, marble and gold, sophisticated elegance"
            ],
            "室内": [
                "sunlit bedroom, morning light through sheer curtains, intimate warmth",
                "cozy coffee shop corner, warm ambient lighting, lifestyle aesthetic",
                "minimalist studio, clean white background, professional setting",
                "vintage library, leather books, intellectual atmosphere",
                "luxury bathroom, marble surfaces, spa-like serenity",
                "art gallery, white walls, sophisticated cultural setting"
            ],
            "特殊": [
                "underwater photography, flowing fabric, dreamlike surreal",
                "mirror reflection scene, double image, artistic composition",
                "behind sheer fabric, mysterious silhouette, sensual artistic",
                "in falling rain, water droplets, emotional dramatic",
                "surrounded by flowers, botanical beauty, nature goddess"
            ]
        },
        "lighting": {
            "自然光": [
                "golden hour sunlight, warm orange glow, magical atmosphere, lens flare",
                "soft diffused daylight, even illumination, natural skin tones",
                "blue hour twilight, cool tones, city lights beginning to glow",
                "dappled sunlight through leaves, natural patterns, organic beauty"
            ],
            "影棚": [
                "professional studio softbox, clean even lighting, fashion magazine quality",
                "Rembrandt lighting, dramatic shadow on cheek, classic portrait",
                "butterfly lighting, glamorous old Hollywood, flattering shadows",
                "rim lighting with hair light, subject separation, ethereal glow"
            ],
            "氛围": [
                "neon lights, colorful glow, cyberpunk atmosphere, vibrant",
                "candlelight warm glow, intimate romantic, soft flickering",
                "fairy lights bokeh, magical sparkle, dreamy atmosphere",
                "dramatic chiaroscuro, strong contrast, emotional depth"
            ]
        },
        "camera_settings": [
            "85mm f/1.2 lens, ultra shallow depth of field, creamy bokeh",
            "50mm f/1.4 lens, natural perspective, classic portrait",
            "135mm f/2 lens, compressed background, beautiful subject isolation",
            "35mm f/1.8 lens, environmental portrait, context and subject",
            "100mm f/2.8 macro lens, extreme detail, skin texture visible"
        ],
        "art_styles": {
            "电影感": [
                "cinematic color grading, film grain, movie still aesthetic, dramatic",
                "Wong Kar-wai style, saturated colors, melancholic romance, neon",
                "Korean drama aesthetic, soft romantic filter, dreamy pastel"
            ],
            "时尚": [
                "Vogue magazine editorial, high fashion, sophisticated elegance",
                "Harper's Bazaar style, avant-garde fashion, artistic",
                "Instagram influencer aesthetic, warm tones, lifestyle aspirational"
            ],
            "艺术": [
                "fine art portrait, painterly quality, museum-worthy",
                "Renaissance painting inspired, classical beauty, timeless"
            ],
            "复古": [
                "90s film photography, nostalgic grain, vintage color cast",
                "Polaroid instant photo aesthetic, retro charm, authentic",
                "old Hollywood glamour, black and white option, timeless elegance"
            ]
        },
        "enhancement_keywords": [
            "award-winning photo, professional photography, magazine cover quality, ultra high resolution",
            "skin texture visible, pores detail, eyelash detail, hair strands detail, ultra crisp",
            "perfect composition, rule of thirds, visual balance, color harmony",
            "post-processing, color grading, professional retouching, polished, hyper detailed",
            "sharp focus on eyes, catchlight, detailed iris, expressive, perfectly focused"
        ],
        "negative_prompts": {
            "standard": "(deformed, bad anatomy, disfigured:1.3), ugly, duplicate, morbid, mutilated, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, blurry, dehydrated, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers, long neck",
            "asian_focused": "Western face, Caucasian features, European features, blonde hair, blue eyes, green eyes, high nose bridge, deep-set eyes, non-Asian features",
            "quality": "low quality, worst quality, jpeg artifacts, pixelated, blurry, out of focus, poorly lit, overexposed, underexposed, amateur photography"
        }
    }


class SmartPromptGenerator:
    """智能 Prompt 生成器"""

    def __init__(self, library: dict, seed: int = None):
        self.library = library
        # 默认使用时间戳确保每次运行都不同
        self.seed = seed if seed is not None else int(time.time() * 1000) % 1000000
        self.rng = random.Random(self.seed)
        log(f"🎲 随机种子: {self.seed}")

    def pick_random(self, items: list, count: int = 1) -> list:
        """从列表中随机选择"""
        if not items:
            return []
        count = min(count, len(items))
        return self.rng.sample(items, count)

    def pick_one(self, items: list) -> str:
        """随机选择一个"""
        if not items:
            return ""
        return self.rng.choice(items)

    def pick_from_dict(self, d: dict, key: str = None) -> tuple:
        """从字典中随机选择，返回 (key, value)"""
        if not d:
            return ("", "")
        if key and key in d:
            values = d[key]
        else:
            key = self.rng.choice(list(d.keys()))
            values = d[key]

        if isinstance(values, list):
            value = self.pick_one(values)
        else:
            value = values
        return (key, value)

    def generate_character(self, style: str = None) -> dict:
        """生成人物特征"""
        # 脸型风格
        face_key, face_desc = self.pick_from_dict(self.library.get("face_types", {}), style)

        # 发型
        hair = self.pick_one(self.library.get("hair_styles", []))

        # 肤质
        skin = self.pick_one(self.library.get("skin_textures", []))

        # 体态
        body = self.pick_one(self.library.get("body_types", []))

        return {
            "style": face_key,
            "face": face_desc,
            "hair": hair,
            "skin": skin,
            "body": body
        }

    def generate_scene(self, scene_type: str = None) -> dict:
        """生成场景"""
        scene_key, scene_desc = self.pick_from_dict(self.library.get("scenes", {}), scene_type)
        light_key, light_desc = self.pick_from_dict(self.library.get("lighting", {}))

        return {
            "type": scene_key,
            "scene": scene_desc,
            "lighting_type": light_key,
            "lighting": light_desc
        }

    def generate_styling(self, outfit_style: str = None) -> dict:
        """生成穿搭和表情"""
        outfit_key, outfit_desc = self.pick_from_dict(self.library.get("outfits", {}), outfit_style)
        expr_key, expr_desc = self.pick_from_dict(self.library.get("expressions", {}))

        return {
            "outfit_style": outfit_key,
            "outfit": outfit_desc,
            "expression_type": expr_key,
            "expression": expr_desc
        }

    def generate_pose(self, pose_type: str = None) -> str:
        """生成姿势"""
        _, pose = self.pick_from_dict(self.library.get("poses", {}), pose_type)
        return pose

    def build_prompt(self,
                     character: dict = None,
                     scene: dict = None,
                     styling: dict = None,
                     pose_type: str = None,
                     custom_elements: list = None) -> str:
        """构建完整的 Prompt"""

        parts = []

        # 1. 基础质量词
        quality = self.pick_one(self.library.get("base_quality", []))
        parts.append(quality)

        # 2. 强制东方美女身份
        asian_id = self.pick_one(self.library.get("asian_identity", []))
        parts.append(asian_id)

        # 3. 人物特征
        if character is None:
            character = self.generate_character()

        if character.get("face"):
            parts.append(character["face"])
        if character.get("skin"):
            parts.append(character["skin"])
        if character.get("hair"):
            parts.append(character["hair"])
        if character.get("body"):
            parts.append(character["body"])

        # 4. 穿搭和表情
        if styling is None:
            styling = self.generate_styling()

        if styling.get("outfit"):
            parts.append(f"wearing {styling['outfit']}")
        if styling.get("expression"):
            parts.append(styling["expression"])

        # 5. 姿势
        pose = self.generate_pose(pose_type)
        if pose:
            parts.append(pose)

        # 6. 场景
        if scene is None:
            scene = self.generate_scene()

        if scene.get("scene"):
            parts.append(scene["scene"])
        if scene.get("lighting"):
            parts.append(scene["lighting"])

        # 7. 相机设置
        camera = self.pick_one(self.library.get("camera_settings", []))
        if camera:
            parts.append(camera)

        # 8. 艺术风格
        _, art_style = self.pick_from_dict(self.library.get("art_styles", {}))
        if art_style:
            parts.append(art_style)

        # 9. 增强关键词
        enhancements = self.pick_random(self.library.get("enhancement_keywords", []), 2)
        parts.extend(enhancements)

        # 10. 自定义元素
        if custom_elements:
            parts.extend(custom_elements)

        # 组合并清理
        prompt = ", ".join(parts)
        while "  " in prompt:
            prompt = prompt.replace("  ", " ")
        prompt = prompt.replace(", ,", ",").strip()

        return prompt

    def get_negative_prompt(self, pose_type: str = None) -> str:
        """获取负面提示词"""
        neg = self.library.get("negative_prompts", {})
        parts = []

        if neg.get("standard"):
            parts.append(neg["standard"])
        if neg.get("asian_focused"):
            parts.append(neg["asian_focused"])
        if neg.get("quality"):
            parts.append(neg["quality"])

        prompt = ", ".join(parts)
        if pose_type == "特写":
            # 特写构图允许 close up / cropped
            tokens = [t.strip() for t in prompt.split(",")]
            tokens = [t for t in tokens if t not in {"close up", "cropped"}]
            prompt = ", ".join(tokens)

        return prompt


def generate_image(prompt: str, negative_prompt: str, reference_url: str = None) -> dict:
    """调用 API 生成图片（纯文生图，不使用图生图）"""

    payload = {
        "model": API_MODEL,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "size": "2K",  # 使用 2K 分辨率（Seedream API 标准格式，大写K）
        "response_format": "url",
        "watermark": False
    }

    # 移除图生图逻辑，每次都使用文生图
    # if reference_url:
    #     payload["image"] = reference_url
    #     log("📎 使用图生图模式")

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


def generate_series(count: int = 3,
                    style: str = None,
                    scene_type: str = None,
                    outfit_style: str = None) -> dict:
    """生成系列图片"""

    global API_KEY
    API_KEY = os.environ.get("DOUBAO_API_KEY")
    if not API_KEY:
        print("错误: 未设置 DOUBAO_API_KEY 环境变量")
        print("请运行: export DOUBAO_API_KEY='your-api-key'")
        return {"success": False, "count": 0, "total": count, "character": {}, "images": []}

    print("=" * 70)
    print("🎨 美女生成 V6.0 - 纯文生图 4K 高清系统")
    print("=" * 70)

    # 加载元素库
    library = load_prompt_library()
    generator = SmartPromptGenerator(library)

    # 生成统一的人物特征（保持一致性，按日期稳定）
    daily_seed = int(date.today().strftime("%Y%m%d"))
    stable_generator = SmartPromptGenerator(library, seed=daily_seed)
    character = stable_generator.generate_character(style)

    print(f"\n📅 日期: {date.today()}")
    print(f"\n👤 人物特征:")
    print(f"   风格: {character.get('style', '随机')}")
    print(f"   脸型: {character.get('face', '')[:50]}...")
    print(f"   发型: {character.get('hair', '')[:50]}...")

    # 不同姿势类型
    pose_types = ["特写", "半身", "全身", "动态"]

    images = []
    negative_prompt = generator.get_negative_prompt()
    print(f"\n🚫 Negative Prompt: {negative_prompt[:80]}...")

    print("\n" + "=" * 70)
    print(f"🎨 开始生成 {count} 张图片（纯文生图，4K 高清）...")
    print("=" * 70)

    for i in range(count):
        # 每张图使用不同的场景、穿搭、姿势
        # 性感系风格：固定偏向室内/城市场景，穿搭锁定性感
        if style == "性感系":
            sexy_scenes = ["室内", "城市"]
            resolved_scene_type = generator.pick_one(sexy_scenes) if not scene_type else scene_type
            scene = generator.generate_scene(resolved_scene_type)
            resolved_outfit_style = outfit_style if outfit_style else "性感"
        else:
            scene = generator.generate_scene(scene_type)
            if outfit_style:
                resolved_outfit_style = outfit_style
            else:
                scene_outfit_map = {
                    "自然": ["清新", "古典", "运动"],
                    "城市": ["时尚", "优雅", "性感"],
                    "室内": ["优雅", "性感", "清新"],
                    "特殊": ["性感", "古典", "时尚"]
                }
                candidates = scene_outfit_map.get(scene.get("type", ""), [])
                resolved_outfit_style = generator.pick_one(candidates) if candidates else None

        styling = generator.generate_styling(resolved_outfit_style)
        pose_type = pose_types[i % len(pose_types)]

        prompt = generator.build_prompt(
            character=character,
            scene=scene,
            styling=styling,
            pose_type=pose_type
        )

        print(f"\n📸 图片 {i+1}/{count} - {pose_type}")
        print(f"   场景: {scene.get('type', '随机')} | 穿搭: {styling.get('outfit_style', '随机')}")
        print(f"   表情: {styling.get('expression_type', '随机')} | 光影: {scene.get('lighting_type', '随机')}")
        print(f"   Prompt: {prompt[:100]}...")

        # 根据姿势调整负面提示词
        negative_prompt = generator.get_negative_prompt(pose_type)

        # 移除图生图逻辑，每次都用文生图生成独立的高清图片
        result = generate_image(
            prompt,
            negative_prompt,
            reference_url=None  # 不使用参考图，纯文生图
        )

        if result["success"]:
            url = result["url"]

            images.append({
                "index": i + 1,
                "pose_type": pose_type,
                "scene_type": scene.get("type"),
                "outfit_style": styling.get("outfit_style"),
                "url": url
            })
            print(f"   ✅ 完成!")
        else:
            print(f"   ❌ 失败: {result.get('error')}")

        if i < count - 1:
            time.sleep(2)

    success_count = len(images)

    print("\n" + "=" * 70)
    print(f"✅ 生成完成: {success_count}/{count}")
    print("=" * 70)

    return {
        "success": success_count == count,
        "count": success_count,
        "total": count,
        "character": character,
        "images": images
    }


def list_options(library: dict):
    """列出所有可用选项"""
    print("\n" + "=" * 70)
    print("🎨 可用风格选项")
    print("=" * 70)

    print("\n👤 人物风格 (--style):")
    for key in library.get("face_types", {}).keys():
        print(f"   • {key}")

    print("\n🧍 体态类型:")
    for item in library.get("body_types", []):
        print(f"   • {item[:40]}...")

    print("\n🏞️  场景类型 (--scene):")
    for key in library.get("scenes", {}).keys():
        print(f"   • {key}")

    print("\n👗 穿搭风格 (--outfit):")
    for key in library.get("outfits", {}).keys():
        print(f"   • {key}")

    print("\n😊 表情类型:")
    for key in library.get("expressions", {}).keys():
        print(f"   • {key}")

    print("\n💡 光影类型:")
    for key in library.get("lighting", {}).keys():
        print(f"   • {key}")

    print("\n🎞️  艺术风格:")
    for key in library.get("art_styles", {}).keys():
        print(f"   • {key}")

    print("\n📷 姿势类型:")
    for key in library.get("poses", {}).keys():
        print(f"   • {key}")


def main():
    global API_KEY

    parser = argparse.ArgumentParser(
        description="美女生成 V6.0 - 纯文生图 4K 高清系统"
    )

    parser.add_argument("--count", "-c", type=int, default=3, help="生成数量 (默认: 3)")
    parser.add_argument("--style", "-s", help="人物风格: 甜美系, 清纯系, 御姐系, 知性系, 冷艳系, 性感系")
    parser.add_argument("--scene", help="场景类型: 自然, 城市, 室内, 特殊")
    parser.add_argument("--outfit", "-o", help="穿搭风格: 优雅, 性感, 清新, 时尚, 古典, 运动")
    parser.add_argument("--list-options", "-l", action="store_true", help="列出所有可用选项")
    parser.add_argument("--preview", "-p", action="store_true", help="只预览 Prompt，不生成图片")

    args = parser.parse_args()

    # 加载元素库
    library = load_prompt_library()

    if args.list_options:
        list_options(library)
        return 0

    # 检查 API Key（预览和列表模式不需要）
    API_KEY = os.environ.get("DOUBAO_API_KEY")
    if not API_KEY and not args.preview:
        print("错误: 未设置 DOUBAO_API_KEY 环境变量")
        print("请运行: export DOUBAO_API_KEY='your-api-key'")
        return 1

    if args.list_options:
        list_options(library)
        return 0

    if args.preview:
        generator = SmartPromptGenerator(library)
        character = generator.generate_character(args.style)
        scene = generator.generate_scene(args.scene)
        styling = generator.generate_styling(args.outfit)

        print("\n" + "=" * 70)
        print("📋 Prompt 预览")
        print("=" * 70)

        for pose_type in ["特写", "半身", "全身"]:
            prompt = generator.build_prompt(
                character=character,
                scene=scene,
                styling=styling,
                pose_type=pose_type
            )
            print(f"\n【{pose_type}】")
            print(prompt)
            print(f"\n【Negative Prompt - {pose_type}】")
            print(generator.get_negative_prompt(pose_type))

        return 0

    # 生成图片
    result = generate_series(
        count=args.count,
        style=args.style,
        scene_type=args.scene,
        outfit_style=args.outfit
    )

    if result["success"]:
        print("\n🎉 全部成功！\n")
        for img in result["images"]:
            print(f"  {img['index']}. [{img['pose_type']}] {img['scene_type']} | {img['outfit_style']}")
            print(f"     {img['url']}")
        return 0
    else:
        print(f"\n⚠️  部分失败 ({result['count']}/{result['total']})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
