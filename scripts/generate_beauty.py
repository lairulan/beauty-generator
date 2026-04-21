#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美女生成 V12.0 - Google Imagen 4 Ultra 主力 + 豆包 Seedream 4.5 备选
- Google Imagen 4 Ultra 作为主力引擎
- 豆包 Seedream 4.5 作为 fallback
- 自动重试 + 429 指数退避（最多 3 次）
- 配置驱动风格策略（style_strategies.json）
- 多图床容错上传 + 重试机制
"""

import argparse
import base64
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import ssl
from datetime import date, datetime
from pathlib import Path


VERSION = "12.0.0"


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

# 确保目录存在
LOGS_DIR.mkdir(parents=True, exist_ok=True)


# ─── 配置加载 ───────────────────────────────────────────────

def _load_json_config(filename: str) -> dict:
    """从 config 目录加载 JSON 配置文件"""
    path = CONFIG_DIR / filename
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


CONSTANTS = _load_json_config("constants.json")
STYLE_STRATEGIES = _load_json_config("style_strategies.json")

# 从 CONSTANTS 读取 API 配置（硬编码值作为 fallback）
_engines = CONSTANTS.get("engines", {})
_doubao_cfg = _engines.get("doubao", {})
_google_cfg = _engines.get("google", {})
_google_retry_cfg = _google_cfg.get("retry", {})

API_ENDPOINT = _doubao_cfg.get(
    "endpoint",
    "https://ark.cn-beijing.volces.com/api/v3/images/generations"
)
API_MODEL = _doubao_cfg.get("model", "doubao-seedream-4-5-251128")
DOUBAO_TIMEOUT = _doubao_cfg.get("timeout", 90)
DOUBAO_SIZE = _doubao_cfg.get("size", "2K")

_doubao_retry_cfg = _doubao_cfg.get("retry", {})
DOUBAO_RETRY_MAX_ATTEMPTS = _doubao_retry_cfg.get("max_attempts", 3)
DOUBAO_RETRY_BASE_DELAY = _doubao_retry_cfg.get("base_delay", 10)
DOUBAO_RETRY_MAX_DELAY = _doubao_retry_cfg.get("max_delay", 60)

GOOGLE_IMAGEN_ENDPOINT = _google_cfg.get(
    "endpoint",
    "https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-ultra-generate-001:predict"
)
GOOGLE_MODEL = _google_cfg.get("model", "imagen-4.0-ultra-generate-001")
GOOGLE_TIMEOUT = _google_cfg.get("timeout", 120)
GOOGLE_SAMPLE_COUNT = _google_cfg.get("sample_count", 1)
GOOGLE_ASPECT_RATIO = _google_cfg.get("aspect_ratio", "3:4")
GOOGLE_IMAGE_SIZE = _google_cfg.get("image_size", "2K")
GOOGLE_RETRY_MAX_ATTEMPTS = _google_retry_cfg.get("max_attempts", 2)
GOOGLE_RETRY_BASE_DELAY = _google_retry_cfg.get("base_delay", 15)
GOOGLE_RETRY_MAX_DELAY = _google_retry_cfg.get("max_delay", 120)
GOOGLE_COOLDOWN_SECONDS = _google_cfg.get("cooldown_seconds", 1800)

IMAGE_HOSTS = CONSTANTS.get("image_hosts", [
    {"name": "imgbb", "endpoint": "https://api.imgbb.com/1/upload", "timeout": 60, "env_key": "IMGBB_API_KEY"}
])
RETRY_CFG = CONSTANTS.get("retry", {"max_attempts": 2, "base_delay": 3})
GENERATION_CFG = CONSTANTS.get("generation", {"default_count": 3, "inter_image_delay": 2})
EMOTION_EXPRESSION_MAP = CONSTANTS.get("emotion_expression_map", {
    "挑逗": "挑逗", "性感": "性感", "温柔": "微笑",
    "俏皮": "挑逗", "自信": "自信", "高冷": "冷艳",
    "忧郁": "忧郁", "纯欲": "纯欲"
})
SCENE_OUTFIT_MAP = CONSTANTS.get("scene_outfit_map", {
    "自然": ["清新", "古典", "运动"],
    "城市": ["时尚", "优雅", "性感"],
    "室内": ["优雅", "性感", "清新"],
    "特殊": ["性感", "古典", "时尚"],
    "国风": ["国风", "古典"],
    "居家": ["居家", "清新"],
    "街头": ["邻家", "清新", "时尚"],
    "职场": ["职场", "优雅"]
})

# ─── 日志 ────────────────────────────────────────────────────

def log(message: str, level: str = "INFO"):
    """记录日志到控制台和文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [{level}] {message}"
    print(log_msg)

    log_file = LOGS_DIR / f"v10-{datetime.now().strftime('%Y%m%d')}.log"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    except Exception:
        pass


# ─── Prompt 元素库 ───────────────────────────────────────────

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
    """内置默认元素库（prompt_library.json 缺失时的 fallback）"""
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
            "perfect hourglass figure with stunning feminine proportions, slim defined waist curving into graceful hips, long toned legs",
            "gorgeous curvy body with naturally feminine fullness, tiny cinched waist, beautifully rounded hips, long slender legs",
            "breathtaking S-curve body with elegant feminine lines, nipped waist flowing into shapely hips and thighs, graceful long legs",
            "statuesque model figure with perfect feminine proportions, dramatically narrow waist, wide elegant hips, endless legs",
            "alluring feminine silhouette with soft natural curves, flat toned stomach, perfect hourglass waist-to-hip ratio, long lean legs"
        ],
        "body_types_sexy": [
            "voluptuous hourglass figure with generous feminine curves straining against every garment, cinched narrow waist, wide curvaceous hips",
            "gorgeous curvy body with eye-catching feminine fullness, tiny waist creating dramatic contrast with full hips, long toned legs",
            "sensational figure with curves that clothing can barely contain, defined waist curve, generous hips, smooth flawless skin",
            "stunning feminine physique with captivating fullness up top, sculpted waist, shapely thighs, seductive body line",
            "breathtaking curves with impossible proportions, nipped waist flowing into voluptuous wide hips, long slender legs"
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
            "挑逗": [
                "teasing playful look, one eyebrow slightly raised, mischievous charm",
                "coy sideways glance, lips curving into a knowing smile, flirtatious energy",
                "playful wink with head tilted, irresistible come-hither expression"
            ],
            "纯欲": [
                "innocent yet alluring gaze, doe eyes with lips barely parted, pure temptation",
                "wide-eyed innocence mixed with subtle sensuality, dewy fresh expression",
                "angelic face with a hint of desire, clear bright eyes, naturally flushed cheeks"
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


# ─── SmartPromptGenerator ───────────────────────────────────

class SmartPromptGenerator:
    """智能 Prompt 生成器"""

    def __init__(self, library: dict, seed: int = None):
        self.library = library
        # 默认使用时间戳确保每次运行都不同
        self.seed = seed if seed is not None else int(time.time() * 1000) % 1000000
        self.rng = random.Random(self.seed)
        log(f"随机种子: {self.seed}")

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
        face_key, face_desc = self.pick_from_dict(self.library.get("face_types", {}), style)
        hair = self.pick_one(self.library.get("hair_styles", []))
        skin = self.pick_one(self.library.get("skin_textures", []))
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

    def generate_styling(self, outfit_style: str = None, expression_type: str = None) -> dict:
        """生成穿搭和表情"""
        outfit_key, outfit_desc = self.pick_from_dict(self.library.get("outfits", {}), outfit_style)
        expr_key, expr_desc = self.pick_from_dict(self.library.get("expressions", {}), expression_type)

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
        """构建 Google Imagen 自然语言 Prompt

        采用自然语言句子结构替代 SD 风格的关键词堆叠，
        更好地利用 Imagen 系列模型的语言理解能力。
        结构：主体描述 -> 外貌特征 -> 穿搭动作 -> 场景环境 -> 技术风格
        """

        # --- 收集所有元素 ---
        quality = self.pick_one(self.library.get("base_quality", []))
        asian_id = self.pick_one(self.library.get("asian_identity", []))

        if character is None:
            character = self.generate_character()
        if styling is None:
            styling = self.generate_styling()

        pose = self.generate_pose(pose_type)

        if scene is None:
            scene = self.generate_scene()

        camera = self.pick_one(self.library.get("camera_settings", []))
        art_key, art_style = self.pick_from_dict(self.library.get("art_styles", {}))
        self._last_art_style_key = art_key
        enhancement = self.pick_one(self.library.get("enhancement_keywords", []))

        # --- 组装自然语言段落 ---
        sections = []

        # 1. 主体描述（质量基调 + 人物身份）
        if style == "性感系":
            sections.append(
                f"A glamorous sensual beauty photograph with alluring feminine charm, featuring {asian_id}"
            )
        else:
            sections.append(f"{quality}, featuring {asian_id}")

        # 2. 外貌特征
        traits = []
        if character.get("face"):
            traits.append(character["face"])
        if character.get("hair"):
            traits.append(character["hair"])
        if character.get("skin"):
            traits.append(character["skin"])
        if character.get("body"):
            traits.append(character["body"])
        if traits:
            sections.append("She has " + ". ".join(traits))

        # 3. 穿搭
        if styling.get("outfit"):
            sections.append(f"She is wearing {styling['outfit']}")

        # 4. 表情
        if styling.get("expression"):
            sections.append(styling["expression"])

        # 5. 姿势
        if pose:
            sections.append(pose)

        # 6. 场景 + 光线
        env = []
        if scene.get("scene"):
            env.append(scene["scene"])
        if scene.get("lighting"):
            env.append(scene["lighting"])
        if env:
            sections.append(", ".join(env))

        # 7. 相机参数
        if camera:
            sections.append(f"Shot with {camera}")

        # 8. 艺术风格
        if art_style:
            sections.append(art_style)

        # 9. 真实感增强
        if enhancement:
            sections.append(enhancement)

        # 10. 自定义元素
        if custom_elements:
            sections.extend(custom_elements)

        # --- 用句号连接各段落 ---
        prompt = ". ".join(sections)

        # 清理多余空格和标点
        while "  " in prompt:
            prompt = prompt.replace("  ", " ")
        prompt = prompt.replace("..", ".").replace(". .", ".").strip()
        if not prompt.endswith("."):
            prompt += "."

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
        if neg.get("anti_ai"):
            parts.append(neg["anti_ai"])

        prompt = ", ".join(parts)
        if pose_type == "特写":
            tokens = [t.strip() for t in prompt.split(",")]
            tokens = [t for t in tokens if t not in {"close up", "cropped"}]
            prompt = ", ".join(tokens)

        return prompt


# ─── 图床上传（多图床容错 + 重试） ────────────────────────────

def _upload_imgbb(host: dict, base64_data: str, api_key: str) -> dict:
    """上传到 imgbb"""
    ssl_context = _get_ssl_context()
    try:
        form_data = urllib.parse.urlencode({"image": base64_data}).encode("utf-8")
        req = urllib.request.Request(
            f"{host['endpoint']}?key={api_key}",
            data=form_data,
            method="POST"
        )
        timeout = host.get("timeout", 60)
        with urllib.request.urlopen(req, context=ssl_context, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("success"):
                return {"success": True, "url": result["data"]["url"]}
            return {"success": False, "error": f"imgbb 返回: {result}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _upload_smms(host: dict, base64_data: str, api_key: str) -> dict:
    """上传到 sm.ms"""
    ssl_context = _get_ssl_context()
    try:
        # sm.ms 需要 multipart/form-data 格式
        image_bytes = base64.b64decode(base64_data)
        boundary = f"----WebKitFormBoundary{int(time.time() * 1000)}"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="smfile"; filename="beauty.png"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode("utf-8") + image_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(
            host["endpoint"],
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Authorization": api_key
            },
            method="POST"
        )
        timeout = host.get("timeout", 60)
        with urllib.request.urlopen(req, context=ssl_context, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("success") and result.get("data", {}).get("url"):
                return {"success": True, "url": result["data"]["url"]}
            # sm.ms 图片已存在时返回 images 字段
            if result.get("images"):
                return {"success": True, "url": result["images"]}
            return {"success": False, "error": f"sm.ms 返回: {result.get('message', result)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def upload_image(base64_data: str) -> dict:
    """多图床上传，按优先级尝试，每个图床支持重试"""
    max_attempts = RETRY_CFG.get("max_attempts", 2)
    base_delay = RETRY_CFG.get("base_delay", 3)

    for host in IMAGE_HOSTS:
        env_key = host.get("env_key", "")
        api_key = os.environ.get(env_key)
        if not api_key:
            continue

        host_name = host.get("name", "unknown")
        for attempt in range(max_attempts):
            if host_name == "imgbb":
                result = _upload_imgbb(host, base64_data, api_key)
            elif host_name == "smms":
                result = _upload_smms(host, base64_data, api_key)
            else:
                result = {"success": False, "error": f"不支持的图床: {host_name}"}
                break

            if result["success"]:
                if attempt > 0:
                    log(f"    {host_name} 第 {attempt + 1} 次尝试成功")
                return result

            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                log(f"    {host_name} 失败: {result.get('error', '未知')}，{delay}s 后重试...")
                time.sleep(delay)

        log(f"    {host_name} 全部 {max_attempts} 次尝试失败，尝试下一个图床...")

    return {"success": False, "error": "所有图床上传失败"}


# ─── 图片生成引擎 ────────────────────────────────────────────

def generate_image_minimax(prompt: str) -> dict:
    """调用 MiniMax image-01 生成图片，临时 URL → 下载后上传 imgbb 获取永久链接"""
    minimax_key = os.environ.get("MINIMAX_API_KEY")
    if not minimax_key:
        return {"success": False, "error": "MINIMAX_API_KEY 未设置"}

    payload = {
        "model": "image-01",
        "prompt": prompt,
        "aspect_ratio": "3:4",
        "response_format": "url",
        "n": 1,
        "prompt_optimizer": True
    }

    ssl_context = _get_ssl_context()
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.minimaxi.com/v1/image_generation",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {minimax_key}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, context=ssl_context, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))

        status_code = result.get("base_resp", {}).get("status_code", -1)
        if status_code != 0:
            msg = result.get("base_resp", {}).get("status_msg", "未知错误")
            return {"success": False, "error": f"MiniMax API 错误 {status_code}: {msg}"}

        image_urls = result.get("data", {}).get("image_urls", [])
        if not image_urls:
            return {"success": False, "error": "MiniMax API 无返回图片"}

        # MiniMax URL 24h 有效，必须下载后上传 imgbb 获取永久链接
        temp_url = image_urls[0]
        log("  [MiniMax] 下载临时图片并上传图床...")
        dl_req = urllib.request.Request(temp_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(dl_req, context=ssl_context, timeout=60) as dl_resp:
            image_bytes = dl_resp.read()

        b64_data = base64.b64encode(image_bytes).decode("utf-8")
        upload_result = upload_image(b64_data)
        if upload_result["success"]:
            return {"success": True, "url": upload_result["url"]}
        return {"success": False, "error": f"图床上传失败: {upload_result['error']}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


_GOOGLE_SUSPEND_FILE = LOGS_DIR / "google_suspended.json"


def _suspend_google(message: str, seconds):
    data = {"message": message, "ts": time.time()}
    if seconds:
        data["until"] = time.time() + seconds
    try:
        with open(_GOOGLE_SUSPEND_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _get_google_suspend_message():
    try:
        if not _GOOGLE_SUSPEND_FILE.exists():
            return None
        with open(_GOOGLE_SUSPEND_FILE) as f:
            data = json.load(f)
        until = data.get("until")
        if until and time.time() > until:
            _GOOGLE_SUSPEND_FILE.unlink(missing_ok=True)
            return None
        return data.get("message", "Google API suspended")
    except Exception:
        return None


def generate_image_google(prompt: str) -> dict:
    """调用 Google Imagen 生成图片，结果上传到图床返回 URL"""
    google_key = os.environ.get("GOOGLE_API_KEY")
    if not google_key:
        return {"success": False, "error": "GOOGLE_API_KEY 未设置"}

    suspended = _get_google_suspend_message()
    if suspended:
        return {"success": False, "error": suspended, "error_type": "suspended"}

    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": GOOGLE_SAMPLE_COUNT,
            "aspectRatio": GOOGLE_ASPECT_RATIO,
            "imageSize": GOOGLE_IMAGE_SIZE
        }
    }

    def _parse_retry_after_seconds(headers) -> int:
        retry_after = headers.get("Retry-After") if headers else None
        if not retry_after:
            return 0
        retry_after = retry_after.strip()
        if retry_after.isdigit():
            return max(1, int(retry_after))
        return 0

    def _parse_google_error_body(body: str) -> dict:
        try:
            payload = json.loads(body)
        except Exception:
            return {}

        error = payload.get("error", {})
        reason = ""
        for detail in error.get("details", []):
            if detail.get("@type", "").endswith("ErrorInfo"):
                reason = detail.get("reason", "")
                break

        return {
            "message": error.get("message", ""),
            "status": error.get("status", ""),
            "reason": reason
        }

    def _format_google_http_error(status_code: int, body: str) -> str:
        details = _parse_google_error_body(body)
        message = (details.get("message") or body or "未知错误").strip()
        reason = details.get("reason", "")

        if reason == "API_KEY_INVALID" and "expired" in message.lower():
            return "Google API Key 已过期，请更新 GOOGLE_API_KEY"
        if reason == "API_KEY_INVALID":
            return f"Google API Key 无效，请检查 GOOGLE_API_KEY: {message}"
        if status_code == 429:
            return f"Google API 限流或配额不足 (429): {message}"
        if reason:
            return f"Google API 错误 {status_code} ({reason}): {message}"
        return f"Google API 错误 {status_code}: {message}"

    ssl_context = _get_ssl_context()
    for attempt in range(GOOGLE_RETRY_MAX_ATTEMPTS):
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                GOOGLE_IMAGEN_ENDPOINT,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": google_key
                },
                method="POST"
            )
            with urllib.request.urlopen(req, context=ssl_context, timeout=GOOGLE_TIMEOUT) as response:
                result = json.loads(response.read().decode("utf-8"))

            predictions = result.get("predictions", [])
            if not predictions:
                return {"success": False, "error": "Google API 无返回图片"}

            b64_data = predictions[0].get("bytesBase64Encoded", "")
            if not b64_data:
                return {"success": False, "error": "Google API 返回数据为空"}

            log("  上传到图床...")
            upload_result = upload_image(b64_data)
            if upload_result["success"]:
                return {"success": True, "url": upload_result["url"]}
            return {"success": False, "error": f"图床上传失败: {upload_result['error']}"}

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            error_message = _format_google_http_error(e.code, body)

            if e.code == 429 and attempt < GOOGLE_RETRY_MAX_ATTEMPTS - 1:
                retry_after = _parse_retry_after_seconds(e.headers)
                delay = retry_after or min(
                    GOOGLE_RETRY_MAX_DELAY,
                    GOOGLE_RETRY_BASE_DELAY * (2 ** attempt)
                )
                log(
                    f"  [Google] 触发限流，{delay}s 后重试 ({attempt + 1}/{GOOGLE_RETRY_MAX_ATTEMPTS})",
                    "WARN"
                )
                time.sleep(delay)
                continue

            if e.code == 429:
                _suspend_google(error_message, GOOGLE_COOLDOWN_SECONDS)
                return {"success": False, "error": error_message, "error_type": "rate_limit"}

            if "Key 已过期" in error_message or "Key 无效" in error_message:
                _suspend_google(error_message, None)
                return {"success": False, "error": error_message, "error_type": "key_invalid"}

            if e.code == 400 and ("paid plans" in error_message or "upgrade" in error_message.lower()):
                _suspend_google(error_message, None)
                return {"success": False, "error": error_message, "error_type": "quota_exceeded"}

            return {"success": False, "error": error_message}

        except urllib.error.URLError as e:
            return {"success": False, "error": f"Google 连接失败: {e.reason}"}
        except json.JSONDecodeError:
            return {"success": False, "error": "Google API 响应 JSON 解析失败"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "Google API 重试后仍失败"}


def generate_image_doubao(prompt: str, negative_prompt: str) -> dict:
    """调用豆包 Seedream 4.5 生成图片（主力引擎）

    - 模型：doubao-seedream-4-5-251128
    - 支持 429 指数退避重试，最多 DOUBAO_RETRY_MAX_ATTEMPTS 次
    - 永久性错误（400/401/403）直接返回，不重试
    """
    doubao_key = os.environ.get("DOUBAO_API_KEY")
    if not doubao_key:
        return {"success": False, "error": "DOUBAO_API_KEY 未设置"}

    payload = {
        "model": API_MODEL,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "size": DOUBAO_SIZE,
        "response_format": "url",
        "watermark": False
    }

    ssl_context = _get_ssl_context()

    for attempt in range(DOUBAO_RETRY_MAX_ATTEMPTS):
        try:
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                API_ENDPOINT,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {doubao_key}"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, context=ssl_context, timeout=DOUBAO_TIMEOUT) as response:
                response_data = response.read().decode("utf-8")
                result = json.loads(response_data)
                if "data" in result and len(result["data"]) > 0:
                    url = result["data"][0].get("url")
                    if url:
                        return {"success": True, "url": url}
            return {"success": False, "error": "豆包 API 响应无图片数据"}

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
            if e.code == 429:
                if attempt < DOUBAO_RETRY_MAX_ATTEMPTS - 1:
                    delay = min(DOUBAO_RETRY_MAX_DELAY, DOUBAO_RETRY_BASE_DELAY * (2 ** attempt))
                    log(f"  [豆包] 触发限流 (429)，{delay}s 后重试 ({attempt + 1}/{DOUBAO_RETRY_MAX_ATTEMPTS})", "WARN")
                    time.sleep(delay)
                    continue
                return {
                    "success": False,
                    "error": f"HTTP Error 429: Too Many Requests（已重试 {DOUBAO_RETRY_MAX_ATTEMPTS} 次）",
                    "error_type": "rate_limit"
                }
            if e.code in (400, 401, 403):
                return {
                    "success": False,
                    "error": f"HTTP Error {e.code}: {err_body}",
                    "error_type": "auth_error"
                }
            if attempt < DOUBAO_RETRY_MAX_ATTEMPTS - 1:
                delay = min(DOUBAO_RETRY_MAX_DELAY, DOUBAO_RETRY_BASE_DELAY * (2 ** attempt))
                log(f"  [豆包] HTTP {e.code} 错误，{delay}s 后重试 ({attempt + 1}/{DOUBAO_RETRY_MAX_ATTEMPTS})", "WARN")
                time.sleep(delay)
                continue
            return {"success": False, "error": f"HTTP Error {e.code}: {err_body}"}

        except urllib.error.URLError as e:
            return {"success": False, "error": f"豆包连接失败: {e.reason}"}

        except json.JSONDecodeError:
            return {"success": False, "error": "豆包 API 响应 JSON 解析失败"}

        except Exception as e:
            if attempt < DOUBAO_RETRY_MAX_ATTEMPTS - 1:
                delay = DOUBAO_RETRY_BASE_DELAY
                log(f"  [豆包] 异常: {e}，{delay}s 后重试 ({attempt + 1}/{DOUBAO_RETRY_MAX_ATTEMPTS})", "WARN")
                time.sleep(delay)
                continue
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "豆包 API 重试后仍失败"}


def generate_image(prompt: str, negative_prompt: str) -> dict:
    """生成图片：Google Imagen 主力 → 豆包 Seedream 4.5 备选"""

    google_key = os.environ.get("GOOGLE_API_KEY")
    if google_key:
        log("  [Google] 使用 Imagen 主力引擎...")
        result = generate_image_google(prompt)
        if result["success"]:
            log("  [Google] 生成成功")
            return result
        log(f"  [Google] 失败: {result.get('error')}，尝试豆包备选...", "WARN")

    doubao_key = os.environ.get("DOUBAO_API_KEY")
    if doubao_key:
        log(f"  [豆包] 使用 Seedream 备选引擎（{API_MODEL}）...")
        result = generate_image_doubao(prompt, negative_prompt)
        if result["success"]:
            log("  [豆包] 生成成功")
            return result
        log(f"  [豆包] 失败: {result.get('error')}", "WARN")

    return {"success": False, "error": "所有引擎均不可用或生成失败"}


# ─── 风格策略 ────────────────────────────────────────────────

def _apply_style_strategy(generator, style, scene_type, outfit_style,
                          resolved_expression, character, i):
    """根据风格策略配置生成参数

    返回: (scene, pose_type, resolved_outfit, resolved_expression, character)
    """
    strategy = STYLE_STRATEGIES.get(style) if style else None

    if not strategy:
        # 默认逻辑：循环姿势 + 场景映射穿搭
        scene = generator.generate_scene(scene_type)
        default_poses = ["特写", "半身", "全身", "动态", "写真"]
        pose_type = default_poses[i % len(default_poses)]
        resolved_outfit = _resolve_default_outfit(generator, scene, outfit_style)
        return scene, pose_type, resolved_outfit, resolved_expression, character

    # 场景
    scenes = strategy.get("scenes", [])
    r_scene = scene_type or (generator.pick_one(scenes) if scenes else None)
    scene = generator.generate_scene(r_scene)

    # 姿势
    pose_types = strategy.get("pose_types", ["半身"])
    pose_type = generator.pick_one(pose_types)

    # 穿搭：CLI 参数 > 固定值 > 随机池
    r_outfit = outfit_style or strategy.get("outfit") or (
        generator.pick_one(strategy["outfit_pool"]) if "outfit_pool" in strategy else None
    )

    # 表情：已有值优先 > 固定值 > 随机池
    if not resolved_expression:
        resolved_expression = strategy.get("expression") or (
            generator.pick_one(strategy["expression_pool"]) if "expression_pool" in strategy else None
        )

    # 性感体态
    if strategy.get("use_sexy_body"):
        sexy_list = generator.library.get("body_types_sexy", [])
        if sexy_list:
            character = dict(character)  # 浅拷贝避免污染原始
            character["body"] = generator.pick_one(sexy_list)

    return scene, pose_type, r_outfit, resolved_expression, character


def _resolve_default_outfit(generator, scene, outfit_style):
    """默认风格：根据场景映射穿搭"""
    if outfit_style:
        return outfit_style
    candidates = SCENE_OUTFIT_MAP.get(scene.get("type", ""), [])
    return generator.pick_one(candidates) if candidates else None


# ─── 系列生成 ────────────────────────────────────────────────

def generate_custom(prompt: str, count: int = 1) -> dict:
    """手动模式：使用用户自定义提示词直接生成图片

    跳过随机元素库组合，直接使用用户提供的 prompt 调用双引擎生成。
    """
    if not os.environ.get("DOUBAO_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        log("错误: 请设置 DOUBAO_API_KEY 环境变量", "ERROR")
        return {"success": False, "count": 0, "total": count, "character": {}, "images": []}

    log("=" * 60)
    log(f"美女生成 V{VERSION} - 手动提示词模式")
    log("=" * 60)
    log(f"日期: {date.today()}")
    log(f"自定义 Prompt: {prompt[:200]}...")
    log(f"生成数量: {count}")

    # 通用负面提示词
    negative_prompt = (
        "cartoon, anime, illustration, painting, drawing, sketch, "
        "3d render, cgi, doll, plastic, deformed, ugly, blurry, "
        "low quality, watermark, text, logo, extra fingers, "
        "mutated hands, bad anatomy, bad proportions"
    )

    images = []
    inter_delay = GENERATION_CFG.get("inter_image_delay", 2)

    log("")
    log("=" * 60)
    log(f"开始生成 {count} 张图片（手动模式）...")
    log("=" * 60)

    for i in range(count):
        log(f"")
        log(f"图片 {i+1}/{count} - 手动模式")
        log(f"  Prompt: {prompt[:100]}...")

        result = generate_image(prompt, negative_prompt)

        if result["success"]:
            url = result["url"]
            images.append({
                "index": i + 1,
                "pose_type": "custom",
                "scene_type": "custom",
                "outfit_style": "custom",
                "expression_type": "custom",
                "lighting_type": "custom",
                "art_style": "custom",
                "url": url
            })
            log(f"  完成!")
        else:
            log(f"  失败: {result.get('error')}", "ERROR")

        if i < count - 1:
            time.sleep(inter_delay)

    success_count = len(images)

    log("")
    log("=" * 60)
    log(f"生成完成: {success_count}/{count}")
    log("=" * 60)

    return {
        "success": success_count == count,
        "count": success_count,
        "total": count,
        "character": {},
        "images": images
    }


def generate_series(count: int = 3,
                    style: str = None,
                    scene_type: str = None,
                    outfit_style: str = None,
                    emotion: str = None) -> dict:
    """生成系列图片"""

    if not os.environ.get("DOUBAO_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        log("错误: 请设置 DOUBAO_API_KEY 环境变量", "ERROR")
        return {"success": False, "count": 0, "total": count, "character": {}, "images": []}

    log("=" * 60)
    log(f"美女生成 V{VERSION} - 豆包 Seedream 3.0 主力引擎")
    log("=" * 60)

    # 加载元素库
    library = load_prompt_library()
    generator = SmartPromptGenerator(library)

    # 每次生成全新随机人物（不再用日期种子，确保每天都是不同的人）
    character = generator.generate_character(style)

    log(f"日期: {date.today()}")
    log(f"人物特征:")
    log(f"  风格: {character.get('style', '随机')}")
    log(f"  脸型: {character.get('face', '')[:50]}...")
    log(f"  发型: {character.get('hair', '')[:50]}...")

    # emotion -> expression 类别映射
    resolved_expression = EMOTION_EXPRESSION_MAP.get(emotion) if emotion else None

    images = []
    inter_delay = GENERATION_CFG.get("inter_image_delay", 2)

    log("")
    log("=" * 60)
    log(f"开始生成 {count} 张图片（Seedream 3.0，原生 2K）...")
    log("=" * 60)

    for i in range(count):
        # 通过风格策略配置生成参数
        scene, pose_type, resolved_outfit, resolved_expression, character = \
            _apply_style_strategy(
                generator, style, scene_type, outfit_style,
                resolved_expression, character, i
            )

        styling = generator.generate_styling(resolved_outfit, resolved_expression)

        prompt = generator.build_prompt(
            character=character,
            scene=scene,
            styling=styling,
            pose_type=pose_type,
            style=style
        )

        log(f"")
        log(f"图片 {i+1}/{count} - {pose_type}")
        log(f"  场景: {scene.get('type', '随机')} | 穿搭: {styling.get('outfit_style', '随机')}")
        log(f"  表情: {styling.get('expression_type', '随机')} | 光影: {scene.get('lighting_type', '随机')}")
        log(f"  Prompt: {prompt[:100]}...")

        # 根据姿势调整负面提示词
        negative_prompt = generator.get_negative_prompt(pose_type)

        result = generate_image(prompt, negative_prompt)

        if result["success"]:
            url = result["url"]
            images.append({
                "index": i + 1,
                "pose_type": pose_type,
                "scene_type": scene.get("type"),
                "outfit_style": styling.get("outfit_style"),
                "expression_type": styling.get("expression_type"),
                "lighting_type": scene.get("lighting_type"),
                "art_style": getattr(generator, '_last_art_style_key', ''),
                "url": url
            })
            log(f"  完成!")
        else:
            log(f"  失败: {result.get('error')}", "ERROR")

        if i < count - 1:
            time.sleep(inter_delay)

    success_count = len(images)

    log("")
    log("=" * 60)
    log(f"生成完成: {success_count}/{count}")
    log("=" * 60)

    return {
        "success": success_count == count,
        "count": success_count,
        "total": count,
        "character": character,
        "images": images
    }


# ─── CLI ─────────────────────────────────────────────────────

def list_options(library: dict):
    """列出所有可用选项"""
    print("\n" + "=" * 60)
    print(f"美女生成 V{VERSION} - 可用风格选项")
    print("=" * 60)

    print("\n人物风格 (--style):")
    for key in library.get("face_types", {}).keys():
        print(f"   - {key}")

    print("\n体态类型:")
    for item in library.get("body_types", []):
        print(f"   - {item[:40]}...")

    print("\n场景类型 (--scene):")
    for key in library.get("scenes", {}).keys():
        print(f"   - {key}")

    print("\n穿搭风格 (--outfit):")
    for key in library.get("outfits", {}).keys():
        print(f"   - {key}")

    print("\n表情类型:")
    for key in library.get("expressions", {}).keys():
        print(f"   - {key}")

    print("\n光影类型:")
    for key in library.get("lighting", {}).keys():
        print(f"   - {key}")

    print("\n艺术风格:")
    for key in library.get("art_styles", {}).keys():
        print(f"   - {key}")

    print("\n姿势类型:")
    for key in library.get("poses", {}).keys():
        print(f"   - {key}")

    print("\n情绪 (--emotion):")
    for key in EMOTION_EXPRESSION_MAP.keys():
        print(f"   - {key} -> {EMOTION_EXPRESSION_MAP[key]}")


def main():
    parser = argparse.ArgumentParser(
        description=f"美女生成 V{VERSION} - 双引擎高清生成系统"
    )

    parser.add_argument("--count", "-c", type=int, default=GENERATION_CFG.get("default_count", 3),
                        help=f"生成数量 (默认: {GENERATION_CFG.get('default_count', 3)})")
    parser.add_argument("--prompt", help="手动模式：直接使用自定义提示词生成（跳过随机元素库）")
    parser.add_argument("--style", "-s", help="人物风格: 甜美系, 清纯系, 性感系, 邻家女孩系, 国风系, 职场系, 生活场景系")
    parser.add_argument("--scene", help="场景类型: 自然, 城市, 室内, 特殊")
    parser.add_argument("--outfit", "-o", help="穿搭风格: 优雅, 性感, 清新, 时尚, 古典, 运动")
    parser.add_argument("--emotion", "-e", help="情绪: 挑逗, 性感, 温柔, 俏皮, 自信, 高冷, 忧郁, 纯欲")
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

        print("\n" + "=" * 60)
        print(f"Prompt 预览 (V{VERSION})")
        print("=" * 60)

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

    # 手动模式：使用自定义提示词
    if args.prompt:
        result = generate_custom(
            prompt=args.prompt,
            count=args.count
        )
    else:
        # 自动模式：从元素库随机组合
        result = generate_series(
            count=args.count,
            style=args.style,
            scene_type=args.scene,
            outfit_style=args.outfit,
            emotion=args.emotion
        )

    if result["success"]:
        print(f"\n全部成功！\n")
        for img in result["images"]:
            print(f"  {img['index']}. [{img['pose_type']}] {img['scene_type']} | {img['outfit_style']}")
            print(f"     {img['url']}")
            print(f"     META:{img.get('scene_type','')}|{img.get('outfit_style','')}|{img.get('expression_type','')}|{img.get('lighting_type','')}|{img.get('art_style','')}")
        return 0
    else:
        print(f"\n部分失败 ({result['count']}/{result['total']})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
