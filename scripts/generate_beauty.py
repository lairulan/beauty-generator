#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美女生成 V12.31 - Google Imagen 4 Ultra 双 Key 主力 + 豆包 Seedream 4.5 备选
- Google Imagen 4 Ultra 作为主力引擎，支持主备 Key 轮换
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


VERSION = "12.31.0"


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

    log_file = LOGS_DIR / f"v12-{datetime.now().strftime('%Y%m%d')}.log"
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
            "Clean lifestyle beauty portrait, flattering available light, porcelain-fair East Asian skin with rosy undertone, fresh relaxed presence",
            "Fresh relaxed lifestyle portrait, full-frame camera, soft neutral daylight tones, clean youthful facial detail",
            "Fresh lifestyle photograph, natural light, clear healthy complexion, soft depth of field",
            "Warm candid beauty portrait, subtle filmic color, flattering catchlights, real moment feeling",
            "Clean everyday beauty portrait that still feels human, lightly retouched, fresh skin, youthful facial softness"
        ],
        "asian_identity": [
            "adult Chinese woman in her early twenties, 22 to 23 years old, contemporary East Asian first-love facial aesthetic, porcelain-fair skin with white-and-rosy cheek warmth, translucent pale-pink lip-balm lips",
            "adult East Asian Chinese woman around 22 or 23 with a graceful oval-melon face, dark almond eyes, natural black hair, a smooth slim cheek-to-jaw line, and a narrow youthful lower face",
            "mainland Chinese / East Asian woman in her early twenties with gentle facial planes, neat natural brows, soft first-love face styling, and fresh rested energy",
            "Chinese woman around 23 with lively East Asian facial features, slim oval-melon facial outline, dark eyes looking gently toward camera, translucent pale-pink glossy lips with transparent lip-balm finish, porcelain-fair skin, smooth narrow cheek-to-jaw transition, and relaxed adult charm",
            "adult East Asian Chinese woman with fresh 22-23 age impression, natural black or very dark brown hair, fair ivory complexion, and soft youthful feminine appeal"
        ],
        "face_types": {
            "甜美系": [
                "sweet innocent face, round cheeks, bright sparkling eyes, soft peach-pink lips, dimples when smiling",
                "soft heart-shaped face, cute round eyes, small button nose, natural pink lips, warm adult sweetness",
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
                "delicate porcelain face, wide clear eyes with long natural lashes, barely-there makeup, clean adult innocence",
                "fresh oval face, bright brown eyes, straight nose, bare lips with natural rose tint, quiet youthful beauty",
                "clean minimalist face, sharp yet soft features, clear single-eyelid eyes, thin natural brows, literary goddess",
                "gentle round face, large sparkling eyes, small nose bridge, natural dewy lips, heart-skip beauty"
            ],
            "御姐系": [
                "refined young-adult elegant face, soft jawline, fresh features, bright confident gaze",
                "elegant young-adult features, soft cheek volume, defined brows, warm confident presence",
                "beautiful young-adult face, balanced soft bone structure, captivating eyes, relaxed expression"
            ],
            "知性系": [
                "intellectual beauty, refined features, wise gentle eyes, elegant expression",
                "sophisticated face, graceful features, thoughtful gaze, cultured appearance",
                "classic beauty, timeless features, intelligent eyes, poised expression"
            ],
            "冷艳系": [
                "cool beauty, soft features, clear gaze, mysterious allure, natural skin",
                "quiet gorgeous face, softly sculpted features, calm expression, ethereal beauty",
                "cool elegant young-adult features, bright eyes, soft cheek volume, polished calm"
            ],
            "性感系": [
                "fresh sensual Chinese face, bright almond eyes, soft cheek fullness, natural peach-pink lips, youthful adult allure",
                "alluring East Asian face, clear warm eyes, relaxed eyelids, softly rounded cheeks, natural lip-balm sheen, refined feminine charm",
                "radiant young-adult face, clean eye makeup, smooth lower-face contours, gently parted natural lips, magnetic but fresh",
                "captivating beauty with bright direct gaze, soft jawline, natural blush, relaxed brows, tasteful youthful attraction",
                "enchanting face with clear eyes and soft smile, soft peach-pink natural lips slightly parted, fresh realistic skin, elegant allure",
                "playful East Asian cat-eye beauty, lifted clear dark eyes, soft nose bridge, natural peach lips, confident warm-cool balance",
                "refined sensual face, lively eyes with subtle catchlights, balanced soft brow bone, full natural low-saturation lips, fresh young-adult allure"
            ],
            "邻家女孩系": [
                "woman-next-door face, natural unfiltered beauty, warm genuine smile, approachable adult charm, clean light makeup",
                "friendly natural face, soft features, bright cheerful eyes, clean cheeks, everyday beauty",
                "cute wholesome face, natural rosy cheeks, warm brown eyes, authentic smile showing teeth",
                "adorable everyday face, minimal makeup, natural skin glow, playful innocent eyes, coffee-shop beauty",
                "fresh outdoor casual face, bright smiling eyes, slightly windblown hair, clean warm complexion, active young-adult charm",
                "bookish adult face, clear clean skin, wire-frame glasses, intelligent gentle appeal",
                "cheerful tomboy-ish face, short layered hair, bright toothy grin, healthy outdoorsy complexion"
            ],
            "国风系": [
                "classical Chinese beauty face, willow-leaf eyebrows, clear phoenix eyes, natural peach lips, elegant oval face",
                "ancient Chinese court beauty, delicate features, almond-shaped eyes, jade-like skin, refined noble elegance",
                "traditional Eastern beauty, graceful bright expression, natural complexion, timeless oriental allure",
                "poetic Chinese beauty, gentle curved brows, clear luminous eyes, subtle rouge, classical warm charm",
                "Tang Dynasty full-moon face, arched moth brows, small rosebud mouth, plump fair skin, imperial beauty",
                "Song Dynasty scholar-beauty, slender face with soft cheek volume, clear poetic gaze, elegant long nose, understated grace",
                "Jiangnan watertown beauty, misty bright eyes, delicate chin, fresh fair skin, gentle poetic charm"
            ],
            "职场系": [
                "modern Chinese office beauty with a soft oval face, dark almond eyes, natural straight brows, gentle nose bridge, barely tinted peach-beige lips",
                "refined East Asian Chinese face, clear dark eyes, understated brows, soft cheek contour, natural lip-balm sheen with pale nude-pink color",
                "elegant urban Chinese professional, warm almond eyes, subtle aegyo-sal, balanced soft jawline, fresh natural makeup, soft peach nude lips",
                "classic Eastern beauty with a slim oval face, dark brown eyes, soft brows, natural complexion, bare peach-beige lip color",
                "young Chinese career woman with clean natural features, soft facial contour, clear eyes, neat natural black hair, barely-there makeup",
                "Hong Kong style modern office beauty, natural black hair, luminous but realistic skin, pale nude-pink lips, restrained eye makeup",
                "polished Chinese professional face with approachable warmth, natural brows, dark almond eyes, soft smile, natural low-saturation peach-beige lips"
            ],
            "生活场景系": [
                "photogenic everyday young-adult East Asian Chinese first-love face, graceful oval-melon facial outline, porcelain-fair skin with translucent rosy undertone, bright rested dark eyes looking gently toward camera, smooth slim cheek-to-jaw line, transparent pale-pink lip-balm lips, tiny closed-lip smile",
                "cozy homebody East Asian clean-beauty face with clean skincare glow, gentle closed-mouth smile, dark almond eyes, youthful lower-face softness, delicate East Asian facial balance",
                "clean East Asian makeup with balanced delicate features, relaxed closed-lip small smile, translucent pale-pink jelly-balm lips, slightly tousled natural black hair, fresh everyday beauty",
                "fresh clear complexion with smooth lower-face contours, tiny relaxed half-smile, morning coffee warmth, clean soft oval East Asian facial balance",
                "photogenic casual weekend Chinese first-love face with bright clear dark eyes, narrow cheek-to-jaw taper, delicate nose bridge, clean oval-melon contours, approachable charm",
                "warm cooking-at-home East Asian lifestyle beauty, clean cheeks, natural black hair tied back with loose strands, tiny fresh closed-lip smile, photogenic East Asian facial balance",
                "photogenic young adult Chinese lifestyle face with faint baby-pink cheek warmth, clean brows, slim oval-melon face, dark almond eyes looking back toward camera, smooth narrow lower face, transparent lip-balm lips, lively attractive 22-23 age impression"
            ]
        },
        "hair_styles": [
            "long silky black hair flowing in wind, glossy healthy shine",
            "shoulder-length dark brown hair with subtle waves, natural movement",
            "elegant updo with loose face-framing tendrils, sophisticated style",
            "sleek straight black hair, mirror-like shine, razor-cut ends",
            "soft romantic dark-brown curls, bouncy natural volume",
            "loose natural black waves, effortless style",
            "high ponytail, sleek and polished, face-lifting effect",
            "bob cut with blunt bangs, modern chic, face-framing",
            "long layered hair with curtain bangs, soft feminine look",
            "half-up half-down style, romantic braids, ethereal beauty"
        ],
        "skin_textures": [
            "porcelain-fair East Asian skin, natural soft glow, translucent rosy undertone",
            "dewy clean fair ivory skin, luminous complexion, white-and-rosy cheek warmth",
            "creamy smooth fair skin, soft focus, photorealistic and clean",
            "cool-neutral fair East Asian skin, healthy natural glow, clear rosy cheeks",
            "milky fresh skin, translucent quality, soft detail, ethereal glow"
        ],
        "body_types": [
            "balanced adult feminine proportions, naturally full but realistic upper-body contour, defined waist, soft hips, and healthy legs",
            "soft natural curves, clear full bust-to-waist line, realistic waist-to-hip ratio, and believable silhouette",
            "healthy everyday build with visible feminine curves, natural rounded upper-body contour, relaxed posture, and realistic proportions",
            "graceful frame with soft shoulders, natural full upper-body volume, defined waist, and balanced hips, photographed without exaggeration",
            "graceful feminine silhouette with clear full bust-to-waist proportion, soft hips, and grounded balance"
        ],
        "adult_lifestyle_face_moods": [
            "fresh young-adult Chinese beauty profile: slim oval-melon face, harmonious photogenic facial proportions, smooth narrow cheek-to-jaw taper, soft small chin, clean willow brows, bright almond eyes with subtle double eyelids and sparkling catchlights, small straight high nose, compact nostrils, porcelain-fair skin with rosy cheek warmth, medium-small petal smile lips with translucent pale clear-pink jelly balm, and lively sweet warmth",
            "sweet mainland Chinese camera-beauty profile: narrow oval lower face, attractive balanced eyes-nose-mouth spacing, soft cheek plane, lifted almond eyes with lower-lid glow, neat natural brows, delicate high nose bridge, small nose base, fair ivory East Asian skin, softly full petal lips in transparent pale-pink water gloss, and relaxed bright eye contact",
            "fresh East Asian first-love adult profile: graceful melon-seed lower face, smooth jaw transition, bright clear pupils, slightly lifted almond eye corners, tidy soft brows, slender straight nose highlight, compact nostrils, white-and-rosy fair complexion, small petal mouth with glossy translucent light pink water tint, and an easy warm smile"
        ],
        "lifestyle_reference_hair_styles": [
            "long natural black hair with a deep soft side part, airy volume at the crown, loose waves flowing behind one shoulder, and a few face-framing strands slimming the cheek line",
            "long glossy black hair swept to one side, natural root lift, soft loose waves, one side tucked lightly behind the ear, revealing an elegant jawline and earring",
            "soft side-parted long black hair with relaxed waves, gentle flyaway strands near the temples, hair framing only one side of the face to avoid a wide face impression"
        ],
        "body_types_lifestyle_full": [
            "a clearly adult tasteful sensual art-portrait silhouette with fuller rounded upper-body fullness, defined waist suggestion, relaxed shoulders, and believable proportions shaped by a modest supportive fitted knit top",
            "a bright fresh young-adult body silhouette with a noticeably fuller but realistic upper-body-to-waist curve, soft waist definition, balanced hips, and fully dressed lifestyle portrait styling",
            "a natural adult feminine build with visible well-supported upper-body fullness, gentle collarbone line, relaxed posture, and structured ribbed fabric creating a fuller rounded art-photo silhouette"
        ],
        "body_types_sexy": [
            "confident curvy figure with natural feminine volume, fuller but realistic bust, defined waist, and rounded hips",
            "softly sculpted body with natural curves, graceful bust-to-waist line, long legs, and believable proportions",
            "refined young-adult feminine figure with natural full upper-body shape, relaxed posture, and clothing that follows the body without exaggeration",
            "shapely body with realistic waistline, full hips, soft natural bust, and natural leg proportions",
            "balanced hourglass figure with natural full bust, believable hips, and relaxed body language",
            "curvy silhouette with balanced proportions, subtle definition, natural full upper-body contour, and understated sensuality"
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
                "white cotton sundress with floral embroidery, modest neckline, soft waist seam, fresh everyday charm",
                "light blue linen shirt softly tucked into high-waisted relaxed denim, clear waist line, effortless casual",
                "pastel wrap top with gentle front gathering and a white linen midi skirt, soft feminine layers",
                "cream knit tank under a light cardigan with a high-waisted floral skirt, literary natural aesthetic"
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
                "supportive ivory ribbed knit top with a modest scoop neckline tucked into relaxed high-waisted lounge pants, clear waist definition, fuller rounded upper-body fullness visible through structured fabric, and soft art-portrait window light",
                "light cream short cardigan worn open over a supportive ribbed tank with wide-leg lounge trousers, fully dressed tasteful sensual portrait styling, soft collarbone line, and fuller rounded upper-body-to-waist contour through the fabric",
                "lightweight open white overshirt over a soft rose-pink structured ribbed fitted tank and straight-leg jeans, rolled sleeves, bright fresh home portrait styling, fuller balanced feminine silhouette, and torso clearly visible from the front"
            ],
            "邻家": [
                "simple white tee tucked into denim shorts, casual sneakers, natural effortless style",
                "light sundress with thin straps, small crossbody bag, sandals, warm park-side adult charm",
                "striped casual shirt, jeans rolled at ankle, minimal accessories, fresh natural off-duty look"
            ]
        },
        "poses": {
            "特写": [
                "close-up portrait, looking directly at camera, lively smiling eyes",
                "face close-up, chin slightly tilted, tiny natural smile",
                "quiet close portrait, bright engaged eyes, natural lips, soft hair detail",
                "three-quarter close-up, elegant side angle, natural neck line visible"
            ],
            "半身": [
                "waist-up portrait with relaxed shoulders and one hand touching hair, natural pose",
                "upper-body portrait leaning slightly toward camera, open posture, lively eye contact",
                "elegant seated half-body pose, hands in lap, relaxed posture with gentle closed-lip smile",
                "front-facing three-quarter waist-up portrait, one arm resting near the waist, tiny closed-lip smile"
            ],
            "全身": [
                "full body standing pose, weight resting naturally on one leg, grounded proportions",
                "walking pose, hair and clothes moving gently, believable confident stride",
                "seated on chair or bench, both feet grounded, relaxed elegant posture",
                "leaning lightly against wall, casual confident stance, realistic posture"
            ],
            "动态": [
                "hair moving lightly as she turns, believable candid motion",
                "twirling in dress, fabric flowing softly, joyful energy",
                "reaching up in a relaxed stretch, elongated posture, dancer-like ease",
                "turning slightly toward camera with a bright curious smile"
            ],
            "写真": [
                "standing portrait with a gentle shoulder turn, hands relaxed, editorial but believable stance",
                "seated portrait on a chair or bench, one leg folded comfortably, hands resting naturally",
                "standing with one hand near the waist, slight natural twist, graceful silhouette",
                "leaning near a window or wall with natural weight shift, full body visible"
            ]
        },
        "expressions": {
            "微笑": [
                "light closed-lip smile with lively clear eyes looking gently toward camera, relaxed mouth corners, smooth slim cheek-to-jaw line, approachable early-twenties charm",
                "subtle closed-mouth smile with bright engaged eyes, smooth lower-face contours, fresh 22-23 mood",
                "gentle tiny smile with lips softly closed, eyes alive with candid warmth, natural attractiveness"
            ],
            "清新微笑": [
                "soft youthful closed-lip small smile with bright clear eyes looking back toward camera, relaxed brows, smooth narrow lower-face line, fresh 22-23 adult softness",
                "gentle relaxed closed-mouth smile with lively dark eyes returning to camera, smooth slim cheek-to-jaw line, clean young-adult charm",
                "fresh tiny half-smile with rested eyes, smooth lower-face contours, translucent pale-pink jelly-balm lips, clean fresh makeup",
                "light closed-lip candid smile with open friendly eyes, relaxed mouth corners, soft cheek fullness, clean East Asian young-adult look",
                "quiet sweet closed-mouth smile with clear catchlights, relaxed jaw, smooth cheek area, fresh early-twenties warmth"
            ],
            "性感": [
                "warm confident gaze with bright open eyes, natural peach lips slightly parted, tasteful youthful adult charm",
                "soft direct eye contact with relaxed eyelids, a light smile, fresh cheeks, refined feminine allure",
                "confident relaxed smile with level chin, bright eyes, soft lower-face contours, natural adult appeal"
            ],
            "挑逗": [
                "playful wink with one eye, bright grin, soft cheeks, lively early-twenties charm",
                "coy sideways glance, lips curving into a light smile, youthful confident warmth",
                "playful wink with head tilted, relaxed brows, natural peach lips, lighthearted charm"
            ],
            "纯欲": [
                "wide soft doe eyes with lips barely parted, soft-faced adult allure, fresh cheek fullness",
                "wide bright eyes with subtle adult charm, dewy fresh expression, natural low-saturation lips",
                "gentle youthful face, clear bright eyes, naturally flushed cheeks, clearly adult presence"
            ],
            "冷艳": [
                "cool clear gaze with soft brows, lifted eyes, soft cheeks, polished styling, still youthful",
                "quiet distant expression with bright catchlights, natural lips, graceful young-adult elegance",
                "sharp but relaxed eye contact, clean facial planes, soft lower-face contours"
            ],
            "忧郁": [
                "soft wistful gaze, fresh eyes, relaxed lips, poetic quietness",
                "thoughtful distant look, relaxed brows, youthful softness, gentle emotional depth"
            ],
            "自信": [
                "confident direct gaze, level chin, bright open eyes, slight natural smile",
                "self-assured soft smile, bright steady eyes, youthful confident presence",
                "focused determined expression, relaxed brows, clear bright eyes, approachable strength"
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
                "sunlit apartment corner, morning light through sheer curtains, warm everyday calm",
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
                "sunlit apartment living room, morning golden light through sheer curtains, tidy sofa and plants, warm everyday atmosphere",
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
                "elegant modern office, warm desk lamp, soft leather chair, professional but youthful setting",
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
            "100mm f/2.8 portrait lens, crisp eyes, soft flattering skin detail"
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
            "a few stray hairs catching the light, smooth slim cheek-to-jaw line, one earring slightly tilted",
            "bright smiling eyes, clean cheek highlights, natural skin softness",
            "fabric wrinkle near elbow, a crease in the shirt collar, wind-blown strand across cheek",
            "subtle motion blur on fingertips, slight squint from sunlight, genuine unposed moment",
            "visible collarbone shadow, clean facial highlights, soft cheek glow"
        ],
        "negative_prompts": {
            "standard": "deformed, bad anatomy, disfigured, ugly, extra fingers, mutated hands, extra limbs, missing limbs, fused fingers, too many fingers, long neck",
            "asian_focused": "Western face, Caucasian features, European features, Southeast Asian face, South Asian face, Indian facial features, Latin face, mixed-race Eurasian face, blonde hair, blue eyes, green eyes, non-Asian features, Westernized mixed-race face, non-Chinese facial structure, olive skin, dusky skin, caramel skin, brown skin, golden tan skin, bronzed tan skin, yellow-brown skin, dark warm skin, heavy Western glam makeup",
            "quality": "3D render, CGI, digital art, illustration, painting, cartoon, anime, plastic skin, airbrushed, over-retouched, wax figure, doll-like, uncanny valley, symmetrical face, too perfect, flawless porcelain, studio backdrop, stock photo, watermark",
            "anti_ai": "impossible body proportions, unnaturally tiny waist, distorted chest anatomy, flattened chest, unnaturally flat chest, flat chest, small chest, missing bust contour, underdeveloped figure, boxy torso, shapeless oversized clothing, bulky shapeless sleeves, hands covering chest, arms blocking torso, side profile hiding torso, countertop hiding body, androgynous torso, collapsed upper-body silhouette, exaggerated fake curves, average face, plain face, unattractive facial features, awkward facial proportions, wide face, broad face, wide round face, short round face, puffy cheeks, chubby cheeks, square jaw, broad jawline, wide lower face, heavy jaw, wide chin, short hair, bob haircut, chin-length hair, flat full-frontal passport angle, flat face angle, no head turn, looking away, strong side gaze, face turned too far away, large nostrils, flared nostrils, wide nostril wings, bulbous nose, wide nose base, wide mouth, broad mouth, over-wide lips, teen, underage, childlike face, school uniform, childish styling, middle-aged, older woman, woman in her 30s, over 30 years old, aged face, mature face, mature executive, older manager, aged professional, gaunt cheeks, hollow cheeks, deep wrinkles, heavy nasolabial folds, pronounced smile lines, tired under-eye bags, tired face, sagging skin, acne, pimples, facial blemishes, skin breakouts, red bumps, acne scars, rash, dark spots, dirty skin, many moles, mole clusters, stiff expression, rigid expression, blank stare, awkward smile, forced smile, dead eyes, stern expression, severe expression, world-weary expression, tired half-lidded eyes, mature seductive smirk, manager-like composure, cold intimidating stare, hard cheekbones, sharp mature jawline, harsh contour makeup, heavy eyeliner, over-arched brows, red lips, red lip tint, colored lipstick, visible lipstick color, high-saturation lip color, dark lip stain, deep lip color, muddy lip color, dull brown lip tint, matte lipstick, lip liner, deep rose lips, mature rose lipstick, dark red lipstick, burgundy lips, purple lipstick, mauve lips, wine-colored lips, red-brown lipstick, brown lipstick, brick-red lips, dark rose lipstick, heavy lipstick, thick lip makeup, overdrawn lips, saturated red lips, vivid red lips, orange-red lips, coral lipstick, dull gray beige color grading, muddy taupe clothing, desaturated lifeless colors"
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

    def generate_scene(self, scene_type: str = None, lighting_type: str = None) -> dict:
        """生成场景"""
        scene_key, scene_desc = self.pick_from_dict(self.library.get("scenes", {}), scene_type)
        light_key, light_desc = self.pick_from_dict(self.library.get("lighting", {}), lighting_type)

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

    def _should_include_body(self, pose_type: str = None, style: str = None) -> bool:
        """近景时弱化身材描写，避免提示词落到夸张身材模板。"""
        return pose_type in {"全身", "写真", "动态"} or style in {"性感系", "生活场景系", "职场系", "国风系"}

    def _build_east_asian_aesthetic_clause(self, style: str = None) -> str:
        """给 Google 正向提示稳定注入东亚审美脸部锚点。"""
        if style == "生活场景系":
            return (
                "Face first: her face must read as a clearly adult contemporary mainland Chinese beauty face, "
                "using the selected adult face profile as a unique individual identity and a varied near-frontal or graceful three-quarter head angle. Keep the face varied but classically Chinese: "
                "a soft high forehead, elongated oval-melon facial outline, smooth narrow cheek-to-jaw taper, softly rounded small chin, and soft arched willow brows; "
                "warm almond eyes with subtle double-eyelid creases, tiny catchlights, delicate lower-lid softness, gently lifted outer corners, and gentle eye contact back toward the camera; "
                "a refined straight high East Asian nose bridge with a clean highlight line, narrow nose base, compact nostrils, and a delicate nose tip; porcelain-fair to fair ivory East Asian skin with translucent rosy undertone, not tan, olive, golden, dusky, or brown; natural black side-parted hair; barely-there makeup; "
                "and petal-shaped medium-small smile lips with a soft cupid's bow, moderate narrow mouth width, translucent pale clear-pink jelly balm, glossy clear-balm finish, and no red lipstick, dark lip stain, or colored lipstick"
            )

        return (
            "Her face should read unmistakably as contemporary East Asian Chinese first-love clean-beauty styling: "
            "soft oval facial outline, porcelain-fair East Asian complexion with white-and-rosy cheek warmth, dark almond-shaped eyes, neat natural straight brows, "
            "a natural gentle nose bridge, smooth slim cheek-to-jaw transition, youthful lower-face contours, natural black or very dark brown hair, "
            "clean fresh makeup, transparent lip-balm finish, and translucent pale-pink glossy lips"
        )

    def _build_feminine_presence_clause(self, style: str = None, pose_type: str = None) -> str:
        """稳定强调年轻成熟女性感，同时避免夸张失真的身体比例。"""
        if style == "性感系":
            return (
                "Her refined young-adult feminine presence is central: graceful neck and collarbones, "
            "a naturally full but realistic upper-body contour, a defined waist, soft rounded hips, and confident feminine posture, "
                "all kept realistic and photographic"
            )

        if style == "生活场景系":
            return (
                "Make the image read as a fresh relaxed 22-23 year old adult Chinese lifestyle portrait. The attraction should come from "
                "the selected fresh adult youthful Chinese beauty profile, bright almond eyes with subtle double eyelids, a small straight high nose bridge with compact nostrils, translucent pale-pink glossy flower-petal lips, porcelain-fair rosy skin, a smooth narrow lower face, "
                "side-parted long black hair softly framing one side of the cheek, bright fresh sensual lifestyle styling, soft sculpting light, a supportive structured fitted casual knit top, fuller rounded upper-body fullness, clear upper-body-to-waist curve, a gentle waist cue, and a three-quarter waist-up camera angle; "
                "keep the outfit fully dressed, modest, artistic, everyday, and restrained"
            )

        if style == "职场系":
            return (
                "Make the image read unmistakably as a modern Chinese / East Asian woman: soft oval facial structure, "
                "dark almond eyes, natural black or very dark brown hair without highlights, clean understated makeup, "
                "and barely tinted peach-beige lips with transparent lip-balm softness and low saturation. The office-fashion appeal should come from confident eye contact, "
                "tailored lines, collarbone and waist cues, a natural full upper-body contour through refined garment structure, "
                "and warm cinematic office depth, with understated makeup and no theatrical glam styling"
            )

        if pose_type in {"特写", "半身"}:
            return (
                "Keep a clearly adult feminine upper-body silhouette visible through the neckline, "
                "collarbones, natural full upper-body contour, shoulder line, and waist suggestion"
            )

        return (
            "Keep her refined adult femininity visible through a clear full bust-to-waist proportion, "
            "soft hips, graceful legs, and believable full-body balance"
        )

    def _build_realism_clauses(self, style: str = None, pose_type: str = None) -> list[str]:
        """补充真实摄影约束，降低 AI 味和过度美化。"""
        if style == "生活场景系":
            return [
                "Keep the image grounded in real-world lifestyle photography with natural daylight, restrained retouching, believable skin texture, and relaxed candid posture",
                "Keep the face clearly adult but visibly 22 to 23 years old: a smooth slim cheek-to-jaw line, bright rested eyes looking gently toward camera, slim smooth lower-face contours, relaxed brows, and a soft early-twenties adult expression",
                "Use the selected face profile as a unique individual identity; preserve fresh adult youthful sweetness and harmonious photogenic facial proportions while keeping a graceful oval-melon face, smooth narrow cheek-to-jaw taper, softly rounded small chin, varied natural brow shape, bright almond eye openness, small straight high nose bridge, and petal-shaped medium-small mouth",
                "Use classic Chinese beauty-word structure in a modern natural face: graceful oval-melon face, narrow lower jaw without harsh sharpness, willow-leaf arched brows, warm lifted almond eyes with subtle double eyelids, refined high East Asian nose bridge with a clean highlight line, compact nostrils, petal-shaped smile lips, and porcelain-fair skin with white-and-rosy cheek warmth",
                "Make the expression gentle and fresh: lively clear eyes, relaxed facial muscles, tiny sweet closed-mouth smile, softly lifted mouth corners, and approachable warmth",
                "Keep the complexion porcelain-fair to fair ivory and clean, with translucent rosy undertone, bright soft cheek color, clear skin texture, fresh clean makeup, and a transparent natural finish; avoid tan, olive, golden, dusky, or brown facial color",
                "Keep the lips attractive and youthful-adult: medium-small petal shape, moderate narrow mouth width, softly full natural lower lip, defined but soft cupid's bow, glossy transparent lip-balm sheen, translucent pale-pink color close to natural lip tone, and no red lipstick, dark lip stain, or colored lipstick",
                "Keep her body clearly adult and feminine through bright tasteful sensual lifestyle-photo styling and fully dressed casual clothing: fuller rounded upper-body fullness, defined waist suggestion, soft shoulders, realistic proportions, supportive structured ribbed knit fabric, soft side light shaping the silhouette, and a three-quarter half-body frame with torso and waist visible",
                "Use contemporary mainland Chinese clean-beauty cues: side-parted natural black hair, slender softly arched brows, warm almond eyes, graceful oval-melon face, smooth narrow lower jaw, refined straight high nose line, compact nostrils, pale-pink petal smile lips, porcelain-fair rosy skin, and a relaxed first-meeting smile"
            ]

        clauses = [
            "Keep the image grounded in real-world photography with clean healthy skin, balanced facial structure, and restrained retouching",
            "Preserve relaxed posture, natural hand placement, smooth healthy cheeks, clean facial highlights, and candid portrait detail",
            "Keep the subject clearly adult but visibly 22 to 23 years old: youthful cheek fullness, bright eyes, smooth lower-face contours, fresh rested energy, and a soft early-twenties facial impression",
            "Keep her facial expression attractive and unmistakably early-twenties: lively clear eyes looking gently toward camera, relaxed brows, smooth slim cheek-to-jaw line, barely tinted transparent lip-balm lips, a closed-lip small fresh smile, and open friendly energy",
            "Favor youthful facial softness, neat natural brows, flattering catchlights, faint rosy-pink cheek warmth, porcelain-fair East Asian skin, barely-there makeup, and almost bare pale nude-pink lips",
            "Keep the body clearly adult and feminine with a natural full upper-body contour, defined waist suggestion, realistic proportions, and a softly fitted silhouette"
        ]

        if pose_type in {"特写", "半身", "职场半身"}:
            clauses.append("Prioritize a fresh early-twenties face with clean healthy skin, lively eyes returning to camera, a smooth slim cheek-to-jaw line, smooth lower-face contours, and a gentle closed-mouth small smile while keeping a soft feminine neckline, collarbones, and natural full upper-body curve visible")
        else:
            clauses.append("Keep refined feminine curves visible but realistic, with natural full bust-to-waist and hip proportions rather than cartoon exaggeration")

        if style == "性感系":
            clauses.append("Use tasteful sensual fashion styling, form-flattering fabric, confident eye contact, fully clothed elegance, and youthful adult glamour")
        elif style == "生活场景系":
            clauses.append("Use fresh relaxed lifestyle styling in public or shared home spaces, fully dressed softly fitted casual clothing, porcelain-fair East Asian skin with white-and-rosy cheek warmth, rested eyes, a lively 22-23 adult East Asian Chinese first-love face, translucent pale-pink transparent lip-balm lips, flattering fabric that follows a naturally full bust-to-waist line, a graceful three-quarter composition with a slight head turn, torso and waist visible, and a soft closed-lip youthful smile; avoid a flat front-facing passport-photo angle, tan or olive complexion, and deep red lip color")
        elif style in {"清纯系", "邻家女孩系"}:
            clauses.append("Use understated makeup, lived-in wardrobe detail, and ordinary available light")
        elif style == "职场系":
            clauses.append(
                "Use premium Chinese office-fashion styling, confident eye contact, a flattering three-quarter angle, "
                "catchlights, refined collarbone and waist cues, warm skyline or desk-lamp depth, natural black hair, "
                "and barely-there peach-nude lip color that stays low-saturation and close to natural skin warmth; avoid passport-photo, LinkedIn headshot, Westernized facial features, dyed highlighted hair, theatrical glam makeup, and flat office lighting"
            )
        elif style == "国风系":
            clauses.append("Favor tactile fabric detail and grounded styling over fantasy rendering")

        return clauses

    def _pick_art_direction(self, style: str = None) -> str:
        """按风格选择更贴近真实写真的视觉语气。"""
        grounded_styles = {
            "清纯系": [
                "soft lifestyle editorial portrait treatment, natural colors, flattering clean light",
                "quiet lifestyle editorial realism, restrained contrast, gentle tonal roll-off",
                "subtle film-like color with understated styling and a believable everyday mood"
            ],
            "甜美系": [
                "natural lifestyle magazine tone, warm but restrained colors, candid emotional feel",
                "soft editorial realism with believable light falloff and clean skin detail",
                "gentle filmic color and a relaxed contemporary portrait mood"
            ],
            "邻家女孩系": [
                "casual lifestyle portrait tone, natural colors, fresh relaxed everyday softness",
                "casual lifestyle editorial realism with minimal grading and real-world light",
                "candid neighborhood photography mood, grounded color, and unforced styling"
            ],
            "生活场景系": [
                "bright fresh sensual home-life portrait photography, soft sculpting window light, porcelain-fair rosy skin, pale-pink clear color accents, and face-led early-twenties adult sweetness",
                "fresh lifestyle cover realism with clear daylight contrast, fair ivory clean skin, lively expression, glossy translucent pale-pink lips, and fully dressed intimate warmth",
                "natural candid lifestyle portrait treatment with believable indoor side light, lively eyes, glossy pale-pink lip-balm lips, soft porcelain-fair rosy skin, and a sculpted feminine silhouette"
            ],
            "职场系": [
                "premium office fashion editorial with crisp window light, soft rim light, catchlights, and quiet sensual tension",
                "cinematic office portrait with warm skyline bokeh, tailored fabric detail, glossy hair texture, and confident eye contact",
                "high-end lifestyle cover portrait, polished but intimate, shallow depth of field, and a magnetic professional presence"
            ],
            "国风系": [
                "grounded historical portrait styling with tactile fabric detail and restrained color",
                "classical portrait realism with gentle contrast and a believable cultural setting",
                "subtle cinematic color inspired by period photography rather than fantasy rendering"
            ]
        }

        if style in grounded_styles:
            return self.pick_one(grounded_styles[style])

        art_key, art_style = self.pick_from_dict(self.library.get("art_styles", {}))
        self._last_art_style_key = art_key
        return art_style

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
        art_style = self._pick_art_direction(style)
        enhancement = self.pick_one(self.library.get("enhancement_keywords", []))

        # --- 组装自然语言段落 ---
        sections = []

        # 1. 主体描述（质量基调 + 人物身份）
        if style == "性感系":
            sections.append(
                f"A tasteful young-adult sensual fashion portrait with refined adult femininity, natural full-bust silhouette, defined waist, youthful softness, and confident feminine allure, featuring {asian_id}"
            )
        elif style == "职场系":
            sections.append(
                f"A refined modern Chinese office-fashion portrait featuring {asian_id}, with unmistakable East Asian Chinese facial features, natural black or very dark brown hair, clean understated makeup, and barely tinted peach-beige lips with a transparent lip-balm finish and low-saturation natural color"
            )
        elif style == "生活场景系":
            sections.append(
                f"A realistic fresh adult Chinese lifestyle half-body portrait in soft neutral daylight, featuring {asian_id}. "
                "The face and expression are the priority: classically beautiful contemporary mainland Chinese East Asian facial aesthetics with visible variation, gentle first-meeting warmth, "
                "warm lifted almond eyes with subtle double eyelids and gentle eye contact back toward camera, harmonious attractive facial proportions, small straight high nose bridge with compact nostrils, graceful oval-melon lower face, petal-shaped medium-small smile lips, translucent pale clear-pink jelly balm, porcelain-fair East Asian skin with rosy cheek warmth, and relaxed early-twenties adult presence"
            )
        else:
            sections.append(f"{quality}, featuring {asian_id}")

        sections.append(self._build_east_asian_aesthetic_clause(style))

        # 2. 外貌特征
        traits = []
        if character.get("face_mood"):
            traits.append(character["face_mood"])
        if character.get("face"):
            traits.append(character["face"])
        if character.get("hair"):
            traits.append(character["hair"])
        if character.get("skin"):
            traits.append(character["skin"])
        if character.get("body") and self._should_include_body(pose_type, style):
            traits.append(character["body"])
        if traits:
            sections.append("She has " + ". ".join(traits))

        feminine_presence = self._build_feminine_presence_clause(style, pose_type)
        if feminine_presence:
            sections.append(feminine_presence)

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

        # 10. 真实摄影约束
        sections.extend(self._build_realism_clauses(style, pose_type))

        # 11. 自定义元素
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

def _upload_imgbb(host: dict, base64_data: str, api_key: str, image_bytes: bytes = None) -> dict:
    """上传到 imgbb，优先走 multipart 二进制上传以避免大图 base64 写入超时"""
    ssl_context = _get_ssl_context()
    try:
        if image_bytes is not None:
            boundary = f"----CodexBoundary{int(time.time() * 1000)}"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="image"; filename="beauty.png"\r\n'
                f"Content-Type: image/png\r\n\r\n"
            ).encode("utf-8") + image_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
            headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        else:
            body = urllib.parse.urlencode({"image": base64_data}).encode("utf-8")
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

        req = urllib.request.Request(
            f"{host['endpoint']}?key={api_key}",
            data=body,
            headers=headers,
            method="POST"
        )
        timeout = host.get("timeout", 180)
        with urllib.request.urlopen(req, context=ssl_context, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("success"):
                return {"success": True, "url": result["data"]["url"]}
            return {"success": False, "error": f"imgbb 返回: {result}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _upload_smms(host: dict, base64_data: str, api_key: str, image_bytes: bytes = None) -> dict:
    """上传到 sm.ms"""
    ssl_context = _get_ssl_context()
    try:
        # sm.ms 需要 multipart/form-data 格式
        image_bytes = image_bytes or base64.b64decode(base64_data)
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


def upload_image(base64_data: str, image_bytes: bytes = None) -> dict:
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
                result = _upload_imgbb(host, base64_data, api_key, image_bytes=image_bytes)
            elif host_name == "smms":
                result = _upload_smms(host, base64_data, api_key, image_bytes=image_bytes)
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
        upload_result = upload_image(b64_data, image_bytes=image_bytes)
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


def _get_google_key_candidates() -> list[tuple[str, str]]:
    """返回按优先级排序的 Google API Key 候选。"""
    candidates = []
    seen = set()
    for env_name, label in [
        ("GOOGLE_API_KEY", "primary"),
        ("GOOGLE_API_KEY_BACKUP", "backup")
    ]:
        value = os.environ.get(env_name, "").strip()
        if value and value not in seen:
            candidates.append((label, value))
            seen.add(value)
    return candidates


def _has_google_key_configured() -> bool:
    return bool(_get_google_key_candidates())


def _is_google_key_retryable_error(error: str) -> bool:
    """判断当前错误是否值得切到下一把 Google Key。"""
    text = (error or "").lower()
    return any(token in text for token in [
        "google api 限流或配额不足 (429)",
        "google api key 无效",
        "google api key 已过期",
        "api key invalid",
        "paid plans",
        "upgrade",
        "quota",
        "resource exhausted",
        "google 连接失败",
        "temporarily unavailable",
        "429"
    ])


def _generate_image_google_with_key(prompt: str, google_key: str) -> dict:
    """调用单把 Google Key 生成图片，结果上传到图床返回 URL。"""

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
            return "Google API Key 已过期，请更新当前配置的 Google Key"
        if reason == "API_KEY_INVALID":
            return f"Google API Key 无效，请检查当前配置的 Google Key: {message}"
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

            image_bytes = base64.b64decode(b64_data)
            log("  上传到图床...")
            upload_result = upload_image(b64_data, image_bytes=image_bytes)
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
                return {"success": False, "error": error_message, "error_type": "rate_limit"}

            if "Key 已过期" in error_message or "Key 无效" in error_message:
                return {"success": False, "error": error_message, "error_type": "key_invalid"}

            if e.code == 400 and ("paid plans" in error_message or "upgrade" in error_message.lower()):
                return {"success": False, "error": error_message, "error_type": "quota_exceeded"}

            return {"success": False, "error": error_message}

        except urllib.error.URLError as e:
            return {"success": False, "error": f"Google 连接失败: {e.reason}"}
        except json.JSONDecodeError:
            return {"success": False, "error": "Google API 响应 JSON 解析失败"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "Google API 重试后仍失败"}


def generate_image_google(prompt: str) -> dict:
    """调用 Google Imagen 生成图片，支持主备 Key 轮换。"""
    google_keys = _get_google_key_candidates()
    if not google_keys:
        return {"success": False, "error": "GOOGLE_API_KEY / GOOGLE_API_KEY_BACKUP 均未设置"}

    suspended = _get_google_suspend_message()
    if suspended:
        return {"success": False, "error": suspended, "error_type": "suspended"}

    last_result = {"success": False, "error": "Google API 未返回结果"}

    for index, (label, google_key) in enumerate(google_keys, start=1):
        log(f"  [Google] 尝试第 {index} 把 Key ({label})")
        result = _generate_image_google_with_key(prompt, google_key)
        if result["success"]:
            return result

        last_result = result
        error_message = result.get("error", "Google API 未知错误")
        if _is_google_key_retryable_error(error_message) and index < len(google_keys):
            log(f"  [Google] 第 {index} 把 Key 不可用，切下一把: {error_message}", "WARN")
            continue

        if result.get("error_type") == "rate_limit":
            _suspend_google(error_message, GOOGLE_COOLDOWN_SECONDS)
        elif result.get("error_type") in {"key_invalid", "quota_exceeded"}:
            _suspend_google(error_message, None)
        return result

    return last_result


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
    force_google_only = os.environ.get("FORCE_GOOGLE_ONLY", "").strip().lower() in {"1", "true", "yes"}

    if _has_google_key_configured():
        log("  [Google] 使用 Imagen 主力引擎...")
        result = generate_image_google(prompt)
        if result["success"]:
            log("  [Google] 生成成功")
            return result
        if force_google_only:
            log(f"  [Google] 失败且已启用 FORCE_GOOGLE_ONLY: {result.get('error')}", "WARN")
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


def _describe_runtime_engine() -> tuple[str, str]:
    """返回当前运行时的引擎描述与生成文案。"""
    google_keys = _get_google_key_candidates()
    has_google = bool(google_keys)
    has_google_backup = len(google_keys) > 1
    has_doubao = bool(os.environ.get("DOUBAO_API_KEY"))
    force_google_only = os.environ.get("FORCE_GOOGLE_ONLY", "").strip().lower() in {"1", "true", "yes"}

    if has_google and force_google_only:
        return (
            f"Google Imagen 4 Ultra {'双 Key ' if has_google_backup else ''}强制模式（模型: {GOOGLE_MODEL}）",
            f"Google Imagen 4 Ultra，{GOOGLE_ASPECT_RATIO}，{GOOGLE_IMAGE_SIZE}"
        )

    if has_google and has_doubao:
        return (
            f"Google Imagen 4 Ultra {'双 Key 主力' if has_google_backup else '主力'} + 豆包 Seedream 4.5 备选（Google: {GOOGLE_MODEL}）",
            f"Google Imagen 4 Ultra 主力，{GOOGLE_ASPECT_RATIO}，{GOOGLE_IMAGE_SIZE}"
        )

    if has_google:
        return (
            f"Google Imagen 4 Ultra {'双 Key ' if has_google_backup else ''}单引擎（模型: {GOOGLE_MODEL}）",
            f"Google Imagen 4 Ultra，{GOOGLE_ASPECT_RATIO}，{GOOGLE_IMAGE_SIZE}"
        )

    return (
        f"豆包 Seedream 4.5 单引擎（模型: {API_MODEL}）",
        f"豆包 Seedream 4.5，{DOUBAO_SIZE}"
    )


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
    r_lighting = strategy.get("lighting") or (
        generator.pick_one(strategy["lighting_pool"]) if "lighting_pool" in strategy else None
    )
    scene = generator.generate_scene(r_scene, r_lighting)

    # 姿势
    pose_types = strategy.get("pose_types", ["半身"])
    pose_type = generator.pick_one(pose_types)

    # 穿搭：CLI 参数 > 固定值 > 随机池
    r_outfit = outfit_style or strategy.get("outfit") or (
        generator.pick_one(strategy["outfit_pool"]) if "outfit_pool" in strategy else None
    )

    # 表情：已有值优先 > 固定值 > 随机池
    if style == "生活场景系" and resolved_expression == "微笑":
        resolved_expression = "清新微笑"

    if not resolved_expression:
        resolved_expression = strategy.get("expression") or (
            generator.pick_one(strategy["expression_pool"]) if "expression_pool" in strategy else None
        )

    # 体态池：生活场景使用单独的日常丰满池，避免性感池污染脸部气质。
    face_mood_pool = strategy.get("face_mood_pool")
    if face_mood_pool:
        face_mood_list = generator.library.get(face_mood_pool, [])
        if face_mood_list:
            character = dict(character)  # 浅拷贝避免污染原始
            character["face_mood"] = generator.pick_one(face_mood_list)

    hair_pool = strategy.get("hair_pool")
    if hair_pool:
        hair_list = generator.library.get(hair_pool, [])
        if hair_list:
            character = dict(character)  # 浅拷贝避免污染原始
            character["hair"] = generator.pick_one(hair_list)

    body_pool = strategy.get("body_pool")
    if body_pool:
        body_list = generator.library.get(body_pool, [])
        if body_list:
            character = dict(character)  # 浅拷贝避免污染原始
            character["body"] = generator.pick_one(body_list)
    elif strategy.get("use_sexy_body"):
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
    if not os.environ.get("DOUBAO_API_KEY") and not _has_google_key_configured():
        log("错误: 请设置 GOOGLE_API_KEY / GOOGLE_API_KEY_BACKUP 或 DOUBAO_API_KEY 环境变量", "ERROR")
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
                    emotion: str = None,
                    seed: int = None) -> dict:
    """生成系列图片"""

    if not os.environ.get("DOUBAO_API_KEY") and not _has_google_key_configured():
        log("错误: 请设置 GOOGLE_API_KEY / GOOGLE_API_KEY_BACKUP 或 DOUBAO_API_KEY 环境变量", "ERROR")
        return {"success": False, "count": 0, "total": count, "character": {}, "images": []}

    engine_title, generation_desc = _describe_runtime_engine()
    log("=" * 60)
    log(f"美女生成 V{VERSION} - {engine_title}")
    log("=" * 60)

    # 加载元素库
    library = load_prompt_library()
    generator = SmartPromptGenerator(library, seed=seed)

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
    log(f"开始生成 {count} 张图片（{generation_desc}）...")
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
    parser.add_argument("--seed", type=int, help="随机种子：用于复现某次 prompt 组合")
    parser.add_argument("--list-options", "-l", action="store_true", help="列出所有可用选项")
    parser.add_argument("--preview", "-p", action="store_true", help="只预览 Prompt，不生成图片")

    args = parser.parse_args()

    # 加载元素库
    library = load_prompt_library()

    if args.list_options:
        list_options(library)
        return 0

    # 检查 API Key（预览和列表模式不需要）
    if not args.preview and not _has_google_key_configured() and not os.environ.get("DOUBAO_API_KEY"):
        print("错误: 请设置 GOOGLE_API_KEY / GOOGLE_API_KEY_BACKUP 或 DOUBAO_API_KEY 环境变量")
        print("Google: export GOOGLE_API_KEY='your-api-key'")
        print("豆包:   export DOUBAO_API_KEY='your-api-key'")
        return 1

    if args.preview:
        generator = SmartPromptGenerator(library, seed=args.seed)
        character = generator.generate_character(args.style)
        resolved_expression = EMOTION_EXPRESSION_MAP.get(args.emotion) if args.emotion else None

        print("\n" + "=" * 60)
        print(f"Prompt 预览 (V{VERSION})")
        print("=" * 60)

        for i in range(3):
            scene, pose_type, resolved_outfit, resolved_expression, preview_character = \
                _apply_style_strategy(
                    generator, args.style, args.scene, args.outfit,
                    resolved_expression, character, i
                )
            styling = generator.generate_styling(resolved_outfit, resolved_expression)
            prompt = generator.build_prompt(
                character=preview_character,
                scene=scene,
                styling=styling,
                pose_type=pose_type,
                style=args.style
            )
            print(
                f"\n【{pose_type} | 场景:{scene.get('type', '随机')} | "
                f"穿搭:{styling.get('outfit_style', '随机')} | 表情:{styling.get('expression_type', '随机')} | "
                f"光影:{scene.get('lighting_type', '随机')}】"
            )
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
            emotion=args.emotion,
            seed=args.seed
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
