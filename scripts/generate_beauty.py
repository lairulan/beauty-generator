#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美女生成 V7.0 - 双引擎高清生成系统
- Google Imagen 4 Ultra 主力 + 豆包 Seedream 备选
- 从丰富的元素库中随机组合
- 确保每次生成都有新鲜感
- 严格东方美女风格
- 性感系专属：写真集姿势 + 丰满曲线体态 + 专属服装
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


def _get_ssl_context():
    """获取 SSL context：优先使用系统证书，失败则回退到不验证"""
    try:
        ctx = ssl.create_default_context()
        return ctx
    except Exception:
        return ssl._create_unverified_context()

# 脚本目录
SCRIPT_DIR = Path(__file__).parent.absolute()
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
LOGS_DIR = SKILL_DIR / "logs"

# API 配置 - 豆包
API_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
API_MODEL = "doubao-seedream-4-5-251128"
API_KEY = os.environ.get("DOUBAO_API_KEY")

# API 配置 - Google Imagen
GOOGLE_IMAGEN_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-ultra-generate-001:predict"
IMGBB_UPLOAD_ENDPOINT = "https://api.imgbb.com/1/upload"

# 确保目录存在
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str, level: str = "INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [{level}] {message}"
    print(log_msg)

    log_file = LOGS_DIR / f"v7-{datetime.now().strftime('%Y%m%d')}.log"
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
            "Candid photograph taken on a Sony A7IV, natural ambient light, unretouched skin",
            "Documentary-style portrait, shot on Fujifilm X-T5, film simulation, available light only",
            "Street photography portrait, captured mid-moment, shallow depth of field, Leica Q3",
            "Natural light portrait, shot through a window, soft diffused shadows, Canon R5",
            "Lifestyle photograph, relaxed candid moment, gentle bokeh background, Nikon Z8"
        ],
        "asian_identity": [
            "Chinese woman in her early twenties",
            "young East Asian woman, Chinese",
            "twenty-something Chinese woman",
            "young woman with Chinese features",
            "East Asian woman, early twenties"
        ],
        "face_types": {
            "甜美系": [
                "sweet innocent face, round cheeks, bright sparkling eyes, cherry lips, dimples when smiling",
                "baby face, cute round eyes, small button nose, natural pink lips, youthful glow",
                "adorable face, aegyo sal, gradient lips, innocent expression, glowing skin",
                "heart-shaped face, big doe eyes, delicate pointed chin, peach-tinted lips, tiny beauty mark near mouth",
                "oval face with soft jawline, crescent-moon smile eyes, natural flush on apple cheeks, petal-soft lips",
                "petite face with high forehead, bright almond eyes, button nose with slight upturn, cupid-bow lips",
                "soft diamond face, twinkling starry eyes, small straight nose, natural gradient blush, sweet tooth-gap smile"
            ],
            "清纯系": [
                "pure innocent face, clear bright eyes, natural beauty, fresh clean look",
                "fresh-faced beauty, dewy skin, natural brows, innocent gaze",
                "youthful pristine face, clear luminous skin, natural pink lips slightly parted, gentle captivating eyes",
                "delicate porcelain face, wide clear eyes with long natural lashes, barely-there makeup, school-girl innocence",
                "serene oval face, calm deep brown eyes, straight nose, bare lips with natural rose tint, quiet beauty",
                "clean minimalist face, sharp yet soft features, clear single-eyelid eyes, thin natural brows, literary goddess",
                "gentle round face, large sparkling eyes, small nose bridge, natural dewy lips, heart-skip beauty"
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
                "seductive face, heavy-lidded almond eyes, full voluptuous lips, high cheekbones, smoldering intensity",
                "alluring features, sultry deep-set eyes, pouty glossy lips, perfect bone structure, sensual charm",
                "glamorous face, smoky eyes, defined cheekbones, parted moist lips, magnetic attraction",
                "captivating beauty, bedroom eyes, sculpted jawline, seductive expression, dangerously attractive",
                "enchanting face, half-lidded seductive gaze, cherry lips slightly parted, devastating allure",
                "fierce fox-face beauty, upswept cat eyes, sharp nose, bold red lips, lethal hot-cold combination",
                "mature sensual face, knowing eyes with golden shimmer, strong brow bone, full wine-stained lips"
            ],
            "邻家女孩系": [
                "girl-next-door face, natural unfiltered beauty, warm genuine smile, approachable charm",
                "friendly natural face, soft features, bright cheerful eyes, light freckles across nose, everyday beauty",
                "cute wholesome face, natural rosy cheeks, warm brown eyes, authentic smile showing teeth",
                "adorable everyday face, minimal makeup, natural skin glow, playful innocent eyes, coffee-shop beauty",
                "sun-kissed casual face, crinkled laugh lines, slightly windblown hair, outdoor active girl charm",
                "youthful college-girl face, clear skin with tiny moles, wire-frame glasses, studious cute appeal",
                "cheerful tomboy-ish face, short layered hair, bright toothy grin, healthy outdoorsy complexion"
            ],
            "国风系": [
                "classical Chinese beauty face, willow-leaf eyebrows, phoenix eyes, cherry red lips, elegant oval face",
                "ancient Chinese court beauty, delicate features, almond-shaped eyes, jade-like skin, refined noble elegance",
                "traditional Eastern beauty, graceful serene expression, porcelain complexion, timeless oriental allure",
                "poetic Chinese beauty, gentle curved brows, clear luminous eyes, subtle rouge, classical warm charm",
                "Tang Dynasty full-moon face, arched moth brows, small rosebud mouth, plump fair skin, imperial beauty",
                "Song Dynasty scholar-beauty, slender face, distant poetic gaze, elegant long nose, understated grace",
                "Jiangnan watertown beauty, misty dreamy eyes, delicate chin, pale skin like fresh snow, gentle melancholy"
            ],
            "职场系": [
                "confident professional beauty, sharp intelligent eyes, subtle makeup, glossy lips, powerful yet feminine",
                "sophisticated office beauty, defined brows, light smoky eyes, coral lipstick, radiating competence",
                "corporate goddess face, polished flawless skin, knowing smile, captivating gaze, boss-level beauty",
                "elegant business beauty, minimal chic makeup, confident direct gaze, professional glamour",
                "sharp-featured career woman, angular jawline, penetrating dark eyes, matte nude lips, ice-queen aura",
                "youthful professional face, bright eager eyes behind trendy glasses, light blush, ambitious energy",
                "poised manager beauty, symmetrical features, arched brows, mauve lips, quiet authority expression"
            ],
            "生活场景系": [
                "natural relaxed face, bare-faced beauty with dewy skin, sleepy morning eyes, intimate warm expression",
                "cozy homebody beauty, minimal skincare glow, lazy smile, soft drowsy eyes, effortlessly attractive",
                "everyday goddess face, natural no-makeup look, warm gentle expression, comfortable intimate beauty",
                "domestic beauty, fresh washed face, natural skin texture visible, warm sleepy smile",
                "post-shower fresh face, damp hair framing face, clean bare skin, relaxed half-smile, steamy warmth",
                "lazy weekend face, slightly puffy morning eyes, messy bun coming undone, oversized collar exposing shoulder",
                "cooking-at-home beauty, flour-dusted cheek, tied-back hair with loose strands, focused concentrated look"
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
        "body_types_sexy": [
            "voluptuous hourglass figure, full round bust, cinched narrow waist, wide curvaceous hips",
            "gorgeous curvy body, large shapely bust, tiny waist, full rounded hips, long toned legs",
            "sensational figure, ample chest, defined waist curve, generous hips, smooth flawless skin",
            "stunning feminine physique, full perky bust, sculpted waist, round lifted buttocks, shapely thighs",
            "breathtaking curves, nipped waist, voluptuous hips, long slender legs, irresistible body contour"
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
            ],
            "国风": [
                "elegant traditional cheongsam qipao with side slit, intricate silk embroidery, body-hugging fit, warm rich red or emerald green",
                "flowing modern hanfu dress with wide sleeves, delicate floral pattern, ethereal fairy-like elegance, soft pastel colors",
                "modern Chinese-style dress with mandarin collar, form-fitting silk fabric, subtle gold embroidery"
            ],
            "职场": [
                "fitted white blouse with top button undone revealing collarbone, high-waisted pencil skirt, sheer stockings, stiletto heels",
                "tailored blazer over silk camisole, slim-fit trousers, delicate necklace, confident corporate chic",
                "elegant secretary look, crisp shirt with rolled sleeves, tight pencil skirt, reading glasses"
            ],
            "居家": [
                "oversized boyfriend shirt barely covering thighs, messy morning hair, bare legs, cozy intimate warmth",
                "silk pajama set with lace trim, soft satin catching warm light, relaxed sensual comfort",
                "cotton crop top and soft shorts, casual Sunday morning look, natural effortless beauty"
            ],
            "邻家": [
                "simple white tee tucked into denim shorts, casual sneakers, natural effortless style",
                "light sundress with thin straps, small crossbody bag, sandals, girl-you-meet-at-the-park vibe",
                "striped casual shirt, jeans rolled at ankle, minimal accessories, fresh natural college-girl look"
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
            ],
            "写真": [
                "full body side pose, arching back slightly, showcasing curves, hands on waist",
                "sitting with legs crossed, leaning back on hands, body fully visible, confident sensual",
                "standing with one hand on hip, slight twist at waist, accentuating silhouette",
                "leaning against wall with hip pushed out, hands above head, full body S-curve visible"
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
            ],
            "国风": [
                "traditional Chinese garden with pavilion and koi pond, cherry blossoms falling, warm golden afternoon light",
                "ancient Chinese palace courtyard, red pillars and golden tiles, warm lantern glow, elegant imperial setting",
                "misty mountain landscape with bamboo forest, ancient stone bridge, morning mist with warm sun"
            ],
            "居家": [
                "cozy sunlit bedroom, morning golden light through sheer curtains, messy white sheets, warm intimate atmosphere",
                "modern kitchen with warm pendant lights, marble counter, morning coffee steam, homey comfortable feeling",
                "living room with large window, soft afternoon sunlight, cozy sofa with throw blanket, warm domestic scene"
            ],
            "街头": [
                "sunny neighborhood sidewalk, dappled tree shadows, warm afternoon light, everyday street scene",
                "local coffee shop exterior, warm golden hour, outdoor seating, casual relaxed atmosphere",
                "university campus walkway, autumn leaves, warm sunlight, youthful vibrant setting"
            ],
            "职场": [
                "modern office with floor-to-ceiling windows, city skyline view, warm afternoon light, sleek corporate interior",
                "elegant executive office, mahogany desk, warm desk lamp, leather chair, professional sophisticated setting",
                "trendy co-working space, natural light, green plants, warm modern minimalist office design"
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
            "a few stray hairs catching the light, slight asymmetry in smile, one earring slightly tilted",
            "faint laugh lines around eyes, barely visible freckle near nose, natural skin unevenness",
            "fabric wrinkle near elbow, a crease in the shirt collar, wind-blown strand across cheek",
            "subtle motion blur on fingertips, slight squint from sunlight, genuine unposed moment",
            "visible collarbone shadow, natural under-eye texture, tiny beauty mark on jawline"
        ],
        "negative_prompts": {
            "standard": "deformed, bad anatomy, disfigured, ugly, extra fingers, mutated hands, extra limbs, missing limbs, fused fingers, too many fingers, long neck",
            "asian_focused": "Western face, Caucasian features, blonde hair, blue eyes, green eyes, non-Asian features",
            "quality": "3D render, CGI, digital art, illustration, painting, cartoon, anime, plastic skin, airbrushed, over-retouched, wax figure, doll-like, uncanny valley, symmetrical face, too perfect, flawless porcelain, studio backdrop, stock photo, watermark"
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

        # 体态 — 所有风格统一使用傲人三围的 body_types
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
                     custom_elements: list = None,
                     style: str = None) -> str:
        """构建完整的 Prompt"""

        parts = []

        # 1. 基础质量词 + 写真集定向（性感系专用）
        quality = self.pick_one(self.library.get("base_quality", []))
        if style == "性感系":
            parts.append("glamorous sensual beauty photography, alluring feminine charm, photobook style, " + quality)
        else:
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

        # 9. 真实感瑕疵锚点（只选1条，避免堆叠）
        enhancements = self.pick_random(self.library.get("enhancement_keywords", []), 1)
        parts.extend(enhancements)

        # 10. 反AI锚点
        realism_anchors = [
            "shot on location, not a studio composite",
            "no retouching, no airbrushing, natural imperfections",
            "photograph indistinguishable from editorial magazine outtake",
            "real person, real environment, unedited candid capture",
            "authentic moment, untouched colors, organic light falloff"
        ]
        parts.append(self.pick_one(realism_anchors))

        # 11. 自定义元素
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


def upload_to_imgbb(base64_data: str) -> dict:
    """上传 base64 图片数据到 imgbb，返回图片 URL"""
    import urllib.parse
    imgbb_key = os.environ.get("IMGBB_API_KEY")
    if not imgbb_key:
        return {"success": False, "error": "IMGBB_API_KEY 未设置"}

    ssl_context = _get_ssl_context()
    try:
        form_data = urllib.parse.urlencode({"image": base64_data}).encode("utf-8")
        req = urllib.request.Request(
            f"{IMGBB_UPLOAD_ENDPOINT}?key={imgbb_key}",
            data=form_data,
            method="POST"
        )
        with urllib.request.urlopen(req, context=ssl_context, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("success"):
                return {"success": True, "url": result["data"]["url"]}
            return {"success": False, "error": f"imgbb 返回: {result}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_image_google(prompt: str) -> dict:
    """调用 Google Imagen 4 Ultra 生成图片，结果上传到 imgbb 返回 URL"""
    import base64
    google_key = os.environ.get("GOOGLE_API_KEY")
    if not google_key:
        return {"success": False, "error": "GOOGLE_API_KEY 未设置"}

    endpoint = f"{GOOGLE_IMAGEN_ENDPOINT}?key={google_key}"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"sampleCount": 1, "aspectRatio": "3:4"}
    }

    ssl_context = _get_ssl_context()
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, context=ssl_context, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))

        predictions = result.get("predictions", [])
        if not predictions:
            return {"success": False, "error": "Google API 无返回图片"}

        b64_data = predictions[0].get("bytesBase64Encoded", "")
        if not b64_data:
            return {"success": False, "error": "Google API 返回数据为空"}

        log("  📤 上传到 imgbb...")
        upload_result = upload_to_imgbb(b64_data)
        if upload_result["success"]:
            return {"success": True, "url": upload_result["url"]}
        return {"success": False, "error": f"imgbb 上传失败: {upload_result['error']}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_image_doubao(prompt: str, negative_prompt: str) -> dict:
    """调用豆包 Seedream API 生成图片"""
    doubao_key = os.environ.get("DOUBAO_API_KEY")
    if not doubao_key:
        return {"success": False, "error": "DOUBAO_API_KEY 未设置"}

    payload = {
        "model": API_MODEL,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "size": "2K",
        "response_format": "url",
        "watermark": False
    }

    ssl_context = _get_ssl_context()
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            API_ENDPOINT,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {doubao_key}'
            },
            method='POST'
        )
        with urllib.request.urlopen(req, context=ssl_context, timeout=90) as response:
            if response.status == 200:
                response_data = response.read().decode('utf-8')
                data = json.loads(response_data)
                if "data" in data and len(data["data"]) > 0:
                    return {"success": True, "url": data["data"][0].get("url")}
        return {"success": False, "error": "豆包 API 响应异常"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_image(prompt: str, negative_prompt: str) -> dict:
    """生成图片：优先 Google Imagen 4 Ultra，失败后降级到豆包 Seedream"""

    # 优先尝试 Google Imagen 4 Ultra
    google_key = os.environ.get("GOOGLE_API_KEY")
    if google_key:
        log("  🌐 [Google] 尝试 Imagen 4 Ultra...")
        result = generate_image_google(prompt)
        if result["success"]:
            log("  ✅ [Google] 生成成功")
            return result
        log(f"  ⚠️  [Google] 失败: {result.get('error')}，降级到豆包...")

    # 降级到豆包 Seedream
    log("  🎨 [豆包] 使用 Seedream 生成...")
    return generate_image_doubao(prompt, negative_prompt)


def generate_series(count: int = 3,
                    style: str = None,
                    scene_type: str = None,
                    outfit_style: str = None) -> dict:
    """生成系列图片"""

    if not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("DOUBAO_API_KEY"):
        print("错误: 请设置 GOOGLE_API_KEY 或 DOUBAO_API_KEY 环境变量")
        return {"success": False, "count": 0, "total": count, "character": {}, "images": []}

    print("=" * 70)
    print("🎨 美女生成 V7.0 - 双引擎高清生成系统")
    print("=" * 70)

    # 加载元素库
    library = load_prompt_library()
    generator = SmartPromptGenerator(library)

    # 每次生成全新随机人物（不再用日期种子，确保每天都是不同的人）
    character = generator.generate_character(style)

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
        # 性感系风格：固定偏向室内/城市场景，穿搭锁定性感，使用写真姿势和性感体态
        if style == "性感系":
            sexy_scenes = ["室内", "城市"]
            resolved_scene_type = generator.pick_one(sexy_scenes) if not scene_type else scene_type
            scene = generator.generate_scene(resolved_scene_type)
            resolved_outfit_style = outfit_style if outfit_style else "性感"
            pose_type = "写真"
            # 性感体态：使用专属的丰满曲线描述
            sexy_body_list = generator.library.get("body_types_sexy", [])
            if sexy_body_list:
                character["body"] = generator.pick_one(sexy_body_list)
        # 国风系：固定国风场景+国风穿搭
        elif style == "国风系":
            resolved_scene_type = scene_type if scene_type else "国风"
            scene = generator.generate_scene(resolved_scene_type)
            resolved_outfit_style = outfit_style if outfit_style else "国风"
            pose_type = generator.pick_one(["半身", "全身", "动态"])
        # 职场系：固定职场场景+职场穿搭
        elif style == "职场系":
            resolved_scene_type = scene_type if scene_type else "职场"
            scene = generator.generate_scene(resolved_scene_type)
            resolved_outfit_style = outfit_style if outfit_style else "职场"
            pose_type = generator.pick_one(["半身", "特写", "全身"])
        # 生活场景系：固定居家场景+居家穿搭
        elif style == "生活场景系":
            resolved_scene_type = scene_type if scene_type else "居家"
            scene = generator.generate_scene(resolved_scene_type)
            resolved_outfit_style = outfit_style if outfit_style else "居家"
            pose_type = generator.pick_one(["半身", "特写", "写真"])
        # 邻家女孩系：街头/自然场景+邻家穿搭
        elif style == "邻家女孩系":
            girl_next_door_scenes = ["街头", "自然", "城市"]
            resolved_scene_type = scene_type if scene_type else generator.pick_one(girl_next_door_scenes)
            scene = generator.generate_scene(resolved_scene_type)
            resolved_outfit_style = outfit_style if outfit_style else "邻家"
            pose_type = generator.pick_one(["半身", "全身", "动态"])
        else:
            scene = generator.generate_scene(scene_type)
            pose_type = pose_types[i % len(pose_types)]
            if outfit_style:
                resolved_outfit_style = outfit_style
            else:
                scene_outfit_map = {
                    "自然": ["清新", "古典", "运动"],
                    "城市": ["时尚", "优雅", "性感"],
                    "室内": ["优雅", "性感", "清新"],
                    "特殊": ["性感", "古典", "时尚"],
                    "国风": ["国风", "古典"],
                    "居家": ["居家", "清新"],
                    "街头": ["邻家", "清新", "时尚"],
                    "职场": ["职场", "优雅"]
                }
                candidates = scene_outfit_map.get(scene.get("type", ""), [])
                resolved_outfit_style = generator.pick_one(candidates) if candidates else None

        styling = generator.generate_styling(resolved_outfit_style)

        prompt = generator.build_prompt(
            character=character,
            scene=scene,
            styling=styling,
            pose_type=pose_type,
            style=style
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
            negative_prompt
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
    parser = argparse.ArgumentParser(
        description="美女生成 V7.0 - 双引擎高清生成系统"
    )

    parser.add_argument("--count", "-c", type=int, default=3, help="生成数量 (默认: 3)")
    parser.add_argument("--style", "-s", help="人物风格: 甜美系, 清纯系, 性感系, 邻家女孩系, 国风系, 职场系, 生活场景系")
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
    if not args.preview and not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("DOUBAO_API_KEY"):
        print("错误: 请设置 GOOGLE_API_KEY 或 DOUBAO_API_KEY 环境变量")
        print("Google: export GOOGLE_API_KEY='your-api-key'")
        print("豆包:   export DOUBAO_API_KEY='your-api-key'")
        return 1

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
