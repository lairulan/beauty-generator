#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美女生成 V12.45 - Google Imagen 4 Ultra 统一 Gemini Key 主力 + 豆包 Seedream 4.5 备选
- Google Imagen 4 Ultra 作为纯文生图主力引擎，使用 GEMINI_API_KEY（兼容旧 GOOGLE_API_KEY）
- 豆包 Seedream 4.5 作为 fallback（含 URLError 重试）
- 自动重试 + 429 指数退避（最多 3 次）
- 配置驱动风格策略（style_strategies.json）
- 多图床容错上传 + 重试机制
- SSL fail-closed（仅 BEAUTY_ALLOW_INSECURE_SSL=1 时回退）
- 自动文生图固定为性感/吸引力写真风格，不再轮换其他风格
"""

import argparse
import base64
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import ssl
from datetime import date, datetime
from pathlib import Path


VERSION = "12.45.1"


# ─── 风格枚举常量（避免散字符串） ─────────────────────────────
STYLE_SWEET = "甜美系"
STYLE_PURE = "清纯系"
STYLE_SEXY = "性感系"
STYLE_GIRL_NEXT_DOOR = "邻家女孩系"
STYLE_GUOFENG = "国风系"
STYLE_OFFICE = "职场系"
STYLE_LIFESTYLE = "生活场景系"

ALL_STYLES = {STYLE_SEXY}
FORCED_STYLE = STYLE_SEXY
FORCED_OUTFIT = "性感"
FORCED_EXPRESSION = "性感"
FORCED_SCENES = ("室内", "城市", "特殊")
FORCED_LIGHTING = ("写真光", "氛围", "影棚")
FORCED_POSES = ("写真",)

# 哪些风格在豆包负面里需要补 anti_hair_makeup（强约束唇/发）
HAIR_MAKEUP_STYLES = {STYLE_SEXY}

# 半身/全身/写真类 pose 才需要 body+scene 负面
WIDE_FRAME_POSES = {"半身", "全身", "写真", "动态", "职场半身", "生活半身"}


MANUAL_PROMPT_LOG_PREFIX_RE = re.compile(
    r"^\s*\[\d{4}-\d{2}-\d{2}\s+[0-9:]+\]\s+\[(?:INFO|WARN|ERROR)\]\s+随机种子:\s*\d+\s*"
)


def clean_manual_prompt(prompt: str) -> str:
    """移除误复制进手动 prompt 的本地日志前缀。"""
    if not prompt:
        return ""
    return MANUAL_PROMPT_LOG_PREFIX_RE.sub("", str(prompt).strip(), count=1).strip()


def _normalize_generation_style(style: str = None, warn: bool = True) -> str:
    """自动文生图统一使用性感系；非性感 style 仅作为历史兼容输入。"""
    requested = (style or "").strip()
    if warn and requested and requested != FORCED_STYLE:
        log(f"  ⚠️ 自动文生图已固定为{FORCED_STYLE}，忽略传入风格：{requested}", "WARN")
    return FORCED_STYLE


def _get_ssl_context():
    """获取 SSL context。

    安全策略（fail-closed）：
      - 默认始终返回 ssl.create_default_context()，证书校验严格开启。
      - 若系统证书 bundle 不可用（极少见），抛出原异常，由调用方决定是否捕获。
      - 仅当显式设置环境变量 BEAUTY_ALLOW_INSECURE_SSL=1 时，才允许回退到不校验证书；
        回退时打印 WARN，提示手动启用了不安全模式。
    """
    try:
        return ssl.create_default_context()
    except Exception as exc:
        allow = os.environ.get("BEAUTY_ALLOW_INSECURE_SSL", "0").strip().lower() in {"1", "true", "yes"}
        if allow:
            print(f"⚠️  [SSL] create_default_context 失败 ({exc})，BEAUTY_ALLOW_INSECURE_SSL=1 已启用不校验证书回退。建议尽快修复系统证书 bundle。")
            return ssl._create_unverified_context()
        raise


# 脚本目录
SCRIPT_DIR = Path(__file__).parent.absolute()
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
LOGS_DIR = SKILL_DIR / "logs"

# 确保目录存在
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Google 限流抑制文件：_suspend_google / _get_google_suspend_message 共用
# 字段: {"message": str, "ts": float, "until": float (unix 秒，到期自动清除)}
_GOOGLE_SUSPEND_FILE = LOGS_DIR / "google_suspended.json"


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
GOOGLE_API_KEY_ENV = _google_cfg.get("api_key_env", "GEMINI_API_KEY")
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
    """加载 Prompt 元素库（V12.39 起 fail-fast：缺失即报错，不再使用内置硬编码 fallback）"""
    library_path = CONFIG_DIR / "prompt_library.json"
    if not library_path.exists():
        raise FileNotFoundError(
            f"Prompt 元素库缺失: {library_path}。"
            "V12.39 起不再内置硬编码 fallback，请确保 config/prompt_library.json 存在。"
        )
    with open(library_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _legacy_default_library_DELETED() -> dict:
    raise NotImplementedError("V12.39 已删除内置 fallback，请使用 config/prompt_library.json")




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
        return pose_type in {"全身", "写真", "动态"} or style in {STYLE_SEXY, STYLE_LIFESTYLE, STYLE_OFFICE, STYLE_GUOFENG}

    def _pick_lip_color(self, style: str = None) -> str:
        """从 lip_color_palette 按风格选一个唇色描述（V12.39 新增多样化）。"""
        palette = self.library.get("lip_color_palette", {})
        if not isinstance(palette, dict):
            return "near-clear pale baby-pink balm"
        candidates = palette.get(style or "") or palette.get("default") or []
        if not candidates:
            return "near-clear pale baby-pink balm"
        return self.pick_one(candidates)

    def _build_east_asian_aesthetic_clause(self, style: str = None, lip_color: str = "") -> str:
        """给 Google 正向提示稳定注入东亚审美脸部锚点。V12.39: 收紧、唇色按 palette 注入。"""
        lip = lip_color or "near-clear pale baby-pink balm"
        if style == STYLE_LIFESTYLE:
            return (
                "Face: a clearly adult contemporary mainland Chinese beauty face, slim oval-melon outline, "
                "smooth narrow cheek-to-jaw taper, softly rounded small chin, willow brows, lifted phoenix-almond / fox-almond eyes "
                "with subtle double eyelids and clear catchlights, refined straight high nose bridge with compact nostrils, "
                "petal-shaped medium-small mouth, side-parted natural black hair, and luminous milk-fair Chinese skin; "
                f"lip finish: {lip}, glossy and low-saturation"
            )

        return (
            "Face: contemporary East Asian Chinese clean-beauty styling — slim oval-melon outline, softly defined cheekbones, "
            "smooth narrow cheek-to-jaw transition, lifted fox-almond / phoenix-almond eyes with strong catchlights, "
            "willow brows, refined straight high nose bridge, compact petal-shaped mouth, "
            f"natural black hair, milk-fair white-and-pink skin; lip finish: {lip}"
        )

    def _build_common_aesthetic_clause(self, style: str = None) -> str:
        """注入跨风格通用审美原则，并叠加当前风格的适配规则。"""
        principles = self.library.get("common_aesthetic_principles", {})
        if not isinstance(principles, dict):
            return ""

        base = str(principles.get("base", "")).strip()
        style_clause = str(principles.get(style or "", "")).strip()
        parts = []
        if base:
            parts.append(f"Common aesthetic principles: {base}")
        if style_clause:
            parts.append(f"Style adaptation for {style}: {style_clause}")
        return " ".join(parts)

    def _build_feminine_presence_clause(self, style: str = None, pose_type: str = None) -> str:
        """V12.39 精简：每风格只保留一句体态/穿搭氛围描述，去掉 sensual/magnetic/alluring。"""
        if style == STYLE_SEXY:
            return (
                "Tasteful fully dressed fashion art portrait: refined feminine silhouette through fitted or structured fabric, "
                "defined waist, soft hips, confident eye contact, three-quarter pose; non-explicit and photographic"
            )

        if style == STYLE_LIFESTYLE:
            return (
                "Fresh relaxed 22-23 year old Chinese lifestyle portrait: side-window light, lightweight fitted square-neck top, "
                "natural feminine silhouette through fabric, a readable lived-in apartment background, three-quarter waist-up angle"
            )

        if style == STYLE_SWEET:
            return (
                "Sweet but adult tone: slim dimensional face, bright eye-smile, light pastel or casual styling, "
                "candid cheerful pose in a readable cafe, garden, apartment or city scene"
            )

        if style == STYLE_PURE:
            return (
                "Clean adult freshness: white-and-pink milk-fair skin, soft lifted eyes, airy fully dressed blouse or dress, "
                "light fitted torso with visible collarbone and waist; no school-uniform or underage cues"
            )

        if style == STYLE_GIRL_NEXT_DOOR:
            return (
                "Everyday girl-next-door moment: approachable eye contact, natural black hair, casual fitted clothing, "
                "clear neckline and waist cue, relaxed movement in a neighborhood / cafe / street / apartment background"
            )

        if style == STYLE_GUOFENG:
            return (
                "Classical Chinese styling grounded and photogenic: tactile silk or embroidered fabric, "
                "clear waist line, elegant three-quarter posture in a real garden, tea room, pavilion or Jiangnan setting"
            )

        if style == STYLE_OFFICE:
            return (
                "Modern Chinese office-fashion portrait: tailored garment structure with collarbone and waist cues, "
                "natural black hair, clean understated makeup, confident eye contact, warm cinematic office depth"
            )

        if pose_type in {"特写", "半身"}:
            return "Clearly adult feminine upper-body silhouette visible through neckline and shoulder line"

        return "Refined adult femininity with realistic full-body proportions and believable balance"

    def _build_realism_clauses(self, style: str = None, pose_type: str = None) -> list[str]:
        """V12.39 精简：从 6-9 条缩到 3-4 条；生活场景系交给专用 prompt，不再叠加。

        v12.42: 加入眼睛硬约束 — Imagen 主路径不读 negative_prompt，必须在正向 prompt
        前置"both eyes fully open"以避免随机出闭眼/眨眼/半闭眼。"""
        eyes_open_clause = (
            "Both eyes are fully open, symmetric, bright, and engaged with direct or "
            "near-camera gaze; no wink, no closed eyes, no half-lidded eyes, no "
            "narrowed or squinting eyes, no hair covering one eye, no asymmetric eye opening"
        )

        if style == STYLE_LIFESTYLE:
            # 生活场景系完全由 _build_lifestyle_prompt 控制，仅追加眼睛硬约束
            return [eyes_open_clause]

        clauses = [
            "Real-world photography with healthy skin, real hair texture, restrained retouching, and natural hand placement",
            "Subject clearly adult but visibly 22-23: youthful cheek softness, bright rested eyes, smooth lower-face contours; no mature 30s impression",
            "Realistic body proportions with a softly fitted or structured silhouette, not hidden by bulky layers, not cartoon-exaggerated",
            eyes_open_clause,
        ]

        # 风格细化：单句风格补充
        style_clause_map = {
            STYLE_SEXY: "Tasteful fully dressed fashion styling in lounge / hotel / city-interior depth; no explicit exposure",
            STYLE_SWEET: "Warm cafe / garden / apartment / city details, playful candid motion, light fresh clothing",
            STYLE_PURE: "Clean natural light, airy blouse or dress, transparent pale lips; no school-uniform styling",
            STYLE_GIRL_NEXT_DOOR: "Neighborhood / cafe / street / apartment depth, natural fitted everyday clothing, real available light",
            STYLE_OFFICE: "Premium Chinese office-fashion styling, three-quarter angle, warm skyline or desk-lamp depth; not a LinkedIn headshot",
            STYLE_GUOFENG: "Grounded classical Chinese portrait realism with tactile silk or embroidery and side light; not fantasy rendering"
        }
        if style in style_clause_map:
            clauses.append(style_clause_map[style])

        return clauses

    def _pick_art_direction(self, style: str = None) -> str:
        """V12.39: 去掉 sensual / magnetic / alluring，生活场景系换成纯净「日常清新」语气。"""
        grounded_styles = {
            STYLE_SEXY: [
                "tasteful fully dressed fashion-editorial realism with clean directional light, real room depth, and elegant fabric shaping a realistic silhouette",
                "refined Chinese fashion art-portrait photography with soft side light, polished but natural skin, and confident eye contact",
                "cinematic lifestyle fashion portrait with lounge or city-interior depth, fitted structured clothing, and restrained retouching"
            ],
            STYLE_PURE: [
                "soft lifestyle editorial portrait treatment, natural colors, flattering clean light",
                "quiet lifestyle editorial realism, restrained contrast, gentle tonal roll-off",
                "subtle film-like color with understated styling and a believable everyday mood"
            ],
            STYLE_SWEET: [
                "natural lifestyle magazine tone, warm but restrained colors, candid emotional feel",
                "soft editorial realism with believable light falloff and clean skin detail",
                "gentle filmic color and a relaxed contemporary portrait mood"
            ],
            STYLE_GIRL_NEXT_DOOR: [
                "casual lifestyle portrait tone, natural colors, fresh relaxed everyday softness",
                "casual lifestyle editorial realism with minimal grading and real-world light",
                "candid neighborhood photography mood, grounded color, and unforced styling"
            ],
            STYLE_LIFESTYLE: [
                "fresh candid home-life environmental portrait photography with side-window light, clean white-and-pink skin tones, and readable apartment background depth",
                "fresh lifestyle cover realism with clean daylight contrast, milk-fair skin, lively bright eyes, believable natural hair texture, and lightweight fitted styling",
                "natural candid lifestyle portrait treatment with soft directional indoor window light, three-dimensional facial planes, realistic strand-by-strand hair, and visible home objects behind her"
            ],
            STYLE_OFFICE: [
                "premium office fashion editorial with crisp window light, soft rim light, and quiet professional tension",
                "cinematic office portrait with warm skyline bokeh, tailored fabric detail, and confident eye contact",
                "high-end lifestyle cover portrait, polished but intimate, shallow depth of field, and a confident professional presence"
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

    def _build_lifestyle_prompt(
        self,
        asian_id: str,
        character: dict,
        scene: dict,
        styling: dict,
        pose: str,
        camera: str,
        art_style: str,
        enhancement: str,
        style: str = None,
        custom_elements: list = None,
        lip_color: str = "",
    ) -> str:
        """V12.39 重写：从 13+ 段精简到 6 段，去掉 sensual/magnetic/alluring，
        合并 upper-body / outfit / fully-dressed 三处描写为一句。

        Imagen 主路径不接收 negative_prompt，所以肤色/唇色/比例约束放在正向前半段。
        """
        lip = lip_color or "near-clear pale baby-pink balm"

        core = [
            # 1. 主体定位
            "A realistic high-key clean daylight waist-up lifestyle portrait of a clearly adult 22-23 year old mainland Chinese woman in a lived-in apartment, not a plain studio portrait",
            f"Subject identity: {asian_id}",
            # 2. 面部锚定（合并 face/eyes/skin/lip 为单段）
            (
                "Face anchor: slim oval-melon outline with three-dimensional cheekbone arc and narrow cheek-to-jaw taper, "
                "small softly pointed chin, willow brows, lifted phoenix-almond / fox-almond eyes with double-eyelid creases, "
                "clear black irises with strong catchlights, refined straight high East Asian nose bridge with compact nostrils, "
                "petal-shaped medium-small mouth; "
                f"skin: cool-neutral milk-fair Chinese complexion with faint fresh pink undertone, no warm filter, no tan, no amber cast; "
                f"lips: {lip}, glossy and visibly lighter than cheek blush, no red / rose / brown / mauve / dark lipstick"
            ),
            # 3. 头发与真实度（合并 hair + real-person）
            (
                "Real photograph realism: natural long black hair with a believable scalp part, varied strand thickness, "
                "fine baby hairs and light flyaways, soft lived-in movement; subtle facial asymmetry, fine skin texture, "
                "small clothing wrinkles, restrained retouching; not CGI, not beauty-filter, not porcelain-doll smoothness"
            ),
            # 4. 体态 + 穿搭 + 构图（合并三处 body / outfit / composition 描述）
            (
                "Body and styling: tasteful fully dressed lightweight fitted square-neck or scoop-neck top following a "
                "natural feminine silhouette through fabric, visible neckline and waist cue, realistic adult proportions; "
                "three-quarter waist-up framing with shoulders angled, head slightly turned toward camera, lively eye-smile; "
                "no thick sweater, no bulky cardigan, no high crewneck hiding collarbone, hands not covering torso"
            ),
            # 4.5 眼睛硬约束（v12.42 - 防止闭眼/眨眼/单眼闭）
            (
                "Both eyes are fully open, symmetric, bright, and engaged with direct or near-camera gaze; "
                "no wink, no closed eyes, no half-lidded eyes, no narrowed or squinting eyes, "
                "no hair covering one eye, no asymmetric eye opening"
            ),
            # 5. 背景
            (
                "Background: lived-in apartment details such as sheer curtains, sofa, green plant, side table, coffee cup, "
                "books or wall art; softly blurred but readable; not plain white, not empty studio"
            ),
        ]

        common_clause = self._build_common_aesthetic_clause(style)
        if common_clause:
            core.append(common_clause)

        details = []
        for key in ("face_mood", "face", "hair", "skin", "body"):
            if character.get(key):
                details.append(character[key])
        if details:
            core.append("Individual details: " + ". ".join(details))

        if styling.get("outfit"):
            core.append(f"She is wearing {styling['outfit']}")
        if styling.get("expression"):
            core.append(styling["expression"])
        if pose:
            core.append(pose)

        env = []
        if scene.get("scene"):
            env.append(scene["scene"])
        if scene.get("lighting"):
            env.append(scene["lighting"])
        if env:
            core.append(", ".join(env))

        if camera:
            core.append(f"Shot with {camera}")
        if art_style:
            core.append(art_style)
        if enhancement:
            core.append(enhancement)

        if custom_elements:
            core.extend(custom_elements)

        prompt = ". ".join(core)
        while "  " in prompt:
            prompt = prompt.replace("  ", " ")
        prompt = prompt.replace("..", ".").replace(". .", ".").strip()
        if not prompt.endswith("."):
            prompt += "."
        return prompt

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
        lip_color = self._pick_lip_color(style)

        if style == STYLE_LIFESTYLE:
            return self._build_lifestyle_prompt(
                asian_id=asian_id,
                character=character,
                scene=scene,
                styling=styling,
                pose=pose,
                camera=camera,
                art_style=art_style,
                enhancement=enhancement,
                style=style,
                custom_elements=custom_elements,
                lip_color=lip_color,
            )

        # --- 组装自然语言段落（V12.39 精简：去掉 sensual/magnetic/alluring）---
        sections = []

        # 1. 主体描述（质量基调 + 人物身份）
        if style == STYLE_SEXY:
            sections.append(
                f"A tasteful young-adult fashion art portrait with refined adult femininity, a natural feminine silhouette through structured clothing, defined waist, and confident presence, featuring {asian_id}"
            )
        elif style == STYLE_OFFICE:
            sections.append(
                f"A refined modern Chinese office-fashion portrait featuring {asian_id}, with East Asian Chinese facial features, natural black hair, clean understated makeup, and {lip_color}"
            )
        else:
            sections.append(f"{quality}, featuring {asian_id}")

        sections.append(self._build_east_asian_aesthetic_clause(style, lip_color=lip_color))

        common_clause = self._build_common_aesthetic_clause(style)
        if common_clause:
            sections.append(common_clause)

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

    def get_negative_prompt(self, pose_type: str = None, style: str = None) -> str:
        """V12.39 重写：按 pose / style 分类拼接 ≤75 token 子串，避免被豆包静默截断。

        - 总是: standard + asian_focused + quality + anti_face + anti_age_mood
        - 半身/全身/写真/动态/职场半身/生活半身: 加 anti_body + anti_scene
        - 性感/职场/国风/生活: 加 anti_hair_makeup
        """
        neg = self.library.get("negative_prompts", {})
        parts = []

        for key in ("standard", "asian_focused", "quality", "anti_face", "anti_age_mood"):
            if neg.get(key):
                parts.append(neg[key])

        if pose_type in WIDE_FRAME_POSES:
            for key in ("anti_body", "anti_scene"):
                if neg.get(key):
                    parts.append(neg[key])

        if style in HAIR_MAKEUP_STYLES and neg.get("anti_hair_makeup"):
            parts.append(neg["anti_hair_makeup"])

        # 兼容旧字段：若 anti_ai 仍存在（用户未升级 prompt_library.json）则保底拼接
        if neg.get("anti_ai") and not any(neg.get(k) for k in ("anti_face", "anti_body")):
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
    """返回 Google Imagen 使用的统一 Key；优先 GEMINI_API_KEY，兼容旧 GOOGLE_API_KEY。"""
    primary_env = GOOGLE_API_KEY_ENV or "GEMINI_API_KEY"
    primary_key = os.environ.get(primary_env, "").strip()
    if primary_key:
        return [(primary_env, primary_key)]

    if primary_env != "GOOGLE_API_KEY":
        legacy_key = os.environ.get("GOOGLE_API_KEY", "").strip()
        if legacy_key:
            return [("GOOGLE_API_KEY legacy", legacy_key)]

    return []


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
    """调用 Google Imagen 4 Ultra 生成图片，使用统一 Gemini API Key。"""
    google_keys = _get_google_key_candidates()
    if not google_keys:
        return {"success": False, "error": f"{GOOGLE_API_KEY_ENV} 未设置（兼容旧 GOOGLE_API_KEY）"}

    suspended = _get_google_suspend_message()
    if suspended:
        return {"success": False, "error": suspended, "error_type": "suspended"}

    last_result = {"success": False, "error": "Google API 未返回结果"}

    for index, (label, google_key) in enumerate(google_keys, start=1):
        log(f"  [Google] 使用 Key: {label}")
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
            # 网络错误（DNS、连接超时、reset 等）也走重试，与 5xx 行为一致
            if attempt < DOUBAO_RETRY_MAX_ATTEMPTS - 1:
                delay = min(DOUBAO_RETRY_MAX_DELAY, DOUBAO_RETRY_BASE_DELAY * (2 ** attempt))
                log(f"  [豆包] 连接失败: {e.reason}，{delay}s 后重试 ({attempt + 1}/{DOUBAO_RETRY_MAX_ATTEMPTS})", "WARN")
                time.sleep(delay)
                continue
            return {"success": False, "error": f"豆包连接失败（已重试 {DOUBAO_RETRY_MAX_ATTEMPTS} 次）: {e.reason}"}

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
    google_key_label = google_keys[0][0] if google_keys else ""
    has_doubao = bool(os.environ.get("DOUBAO_API_KEY"))
    force_google_only = os.environ.get("FORCE_GOOGLE_ONLY", "").strip().lower() in {"1", "true", "yes"}

    if has_google and force_google_only:
        return (
            f"Google Imagen 4 Ultra 强制模式（模型: {GOOGLE_MODEL}，Key: {google_key_label}）",
            f"Google Imagen 4 Ultra，{GOOGLE_ASPECT_RATIO}，{GOOGLE_IMAGE_SIZE}"
        )

    if has_google and has_doubao:
        return (
            f"Google Imagen 4 Ultra 主力 + 豆包 Seedream 4.5 备选（Google: {GOOGLE_MODEL}，Key: {google_key_label}）",
            f"Google Imagen 4 Ultra 主力，{GOOGLE_ASPECT_RATIO}，{GOOGLE_IMAGE_SIZE}"
        )

    if has_google:
        return (
            f"Google Imagen 4 Ultra 单引擎（模型: {GOOGLE_MODEL}，Key: {google_key_label}）",
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
    style = _normalize_generation_style(style, warn=False)
    strategy = STYLE_STRATEGIES.get(style) if style else None

    if not strategy:
        # 配置缺失时仍保持性感系兜底，不回退到其他风格。
        if scene_type and scene_type not in FORCED_SCENES:
            log(
                f"  ⚠️ 自动文生图只保留性感系场景 {','.join(FORCED_SCENES)}，忽略传入场景：{scene_type}",
                "WARN",
            )
            scene_type = None
        scene = generator.generate_scene(scene_type or generator.pick_one(FORCED_SCENES))
        return scene, "写真", FORCED_OUTFIT, FORCED_EXPRESSION, {"style": style}

    # 场景
    allowed_scenes = set(strategy.get("scenes") or FORCED_SCENES)
    if scene_type and scene_type not in allowed_scenes:
        log(
            f"  ⚠️ 自动文生图只保留性感系场景 {','.join(FORCED_SCENES)}，忽略传入场景：{scene_type}",
            "WARN",
        )
        scene_type = None
    scenes = strategy.get("scenes", [])
    r_scene = scene_type or (generator.pick_one(scenes) if scenes else None)
    r_lighting = strategy.get("lighting") or (
        generator.pick_one(strategy["lighting_pool"]) if "lighting_pool" in strategy else None
    )
    scene = generator.generate_scene(r_scene, r_lighting)

    # 姿势
    pose_types = strategy.get("pose_types", ["半身"])
    pose_type = generator.pick_one(pose_types)

    # 性感系为硬约束：忽略外部传入的非性感 outfit/emotion，避免回到其他图片风格。
    r_outfit = strategy.get("outfit") or FORCED_OUTFIT

    resolved_expression = strategy.get("expression") or FORCED_EXPRESSION

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

    character = dict(character)
    character["style"] = style
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
    prompt = clean_manual_prompt(prompt)

    if not os.environ.get("DOUBAO_API_KEY") and not _has_google_key_configured():
        log("错误: 请设置 GEMINI_API_KEY（兼容 GOOGLE_API_KEY）或 DOUBAO_API_KEY 环境变量", "ERROR")
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
        log("错误: 请设置 GEMINI_API_KEY（兼容 GOOGLE_API_KEY）或 DOUBAO_API_KEY 环境变量", "ERROR")
        return {"success": False, "count": 0, "total": count, "character": {}, "images": []}

    engine_title, generation_desc = _describe_runtime_engine()
    log("=" * 60)
    log(f"美女生成 V{VERSION} - {engine_title}")
    log("=" * 60)

    # 加载元素库
    library = load_prompt_library()
    generator = SmartPromptGenerator(library, seed=seed)
    requested_style = style
    style = _normalize_generation_style(style)
    if emotion and EMOTION_EXPRESSION_MAP.get(emotion) != FORCED_EXPRESSION:
        log(f"  ⚠️ 自动文生图已固定为{FORCED_STYLE}/{FORCED_EXPRESSION}，忽略传入情绪：{emotion}", "WARN")

    # 每次生成全新随机人物（不再用日期种子，确保每天都是不同的人）
    character = generator.generate_character(style)

    log(f"日期: {date.today()}")
    log(f"自动风格: {style}（固定性感/吸引力写真，原始输入：{requested_style or '自动'}）")
    log(f"人物特征:")
    log(f"  风格: {character.get('style', '随机')}")
    log(f"  脸型: {character.get('face', '')[:50]}...")
    log(f"  发型: {character.get('hair', '')[:50]}...")

    # emotion -> expression 类别映射（用户显式 --emotion 时贯穿全部图，
    # 否则每张图都从策略池里重新随机）
    initial_expression = FORCED_EXPRESSION

    images = []
    inter_delay = GENERATION_CFG.get("inter_image_delay", 2)

    log("")
    log("=" * 60)
    log(f"开始生成 {count} 张图片（{generation_desc}）...")
    log("=" * 60)

    for i in range(count):
        # 每张图前重置为初始值，避免上一张随机出的表情污染后续所有图
        resolved_expression = initial_expression
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

        # 根据姿势 + 风格调整负面提示词（V12.39: 分类拼接，避免被截断）
        negative_prompt = generator.get_negative_prompt(pose_type, style=style)

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
    print(f"   - {FORCED_STYLE}（固定）")

    print("\n体态类型:")
    for item in library.get("body_types", []):
        print(f"   - {item[:40]}...")

    print("\n场景类型 (--scene):")
    for key in FORCED_SCENES:
        print(f"   - {key}")

    print("\n穿搭风格 (--outfit):")
    print(f"   - {FORCED_OUTFIT}（自动模式固定）")

    print("\n表情类型:")
    print(f"   - {FORCED_EXPRESSION}（自动模式固定）")

    print("\n光影类型:")
    for key in FORCED_LIGHTING:
        print(f"   - {key}")

    print("\n艺术风格:")
    for key in library.get("art_styles", {}).keys():
        print(f"   - {key}")

    print("\n姿势类型:")
    for key in FORCED_POSES:
        print(f"   - {key}")

    print("\n情绪 (--emotion):")
    print(f"   - {FORCED_EXPRESSION}（自动模式固定）")


def main():
    parser = argparse.ArgumentParser(
        description=f"美女生成 V{VERSION} - 双引擎高清生成系统"
    )

    parser.add_argument("--count", "-c", type=int, default=GENERATION_CFG.get("default_count", 3),
                        help=f"生成数量 (默认: {GENERATION_CFG.get('default_count', 3)})")
    parser.add_argument("--prompt", help="手动模式：直接使用自定义提示词生成（跳过随机元素库）")
    parser.add_argument("--style", "-s", help="人物风格固定为性感系；传其他值会自动归一为性感系")
    parser.add_argument("--scene", help="自动模式只保留性感系场景: 室内, 城市, 特殊")
    parser.add_argument("--outfit", "-o", help="自动模式固定为性感穿搭；该参数仅保留兼容")
    parser.add_argument("--emotion", "-e", help="自动模式固定为性感表达；该参数仅保留兼容")
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
        print("错误: 请设置 GEMINI_API_KEY（兼容 GOOGLE_API_KEY）或 DOUBAO_API_KEY 环境变量")
        print("Google: export GEMINI_API_KEY='your-api-key'")
        print("豆包:   export DOUBAO_API_KEY='your-api-key'")
        return 1

    if args.preview:
        generator = SmartPromptGenerator(library, seed=args.seed)
        preview_style = _normalize_generation_style(args.style)
        character = generator.generate_character(preview_style)
        resolved_expression = FORCED_EXPRESSION

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
                style=preview_style
            )
            print(
                f"\n【{pose_type} | 场景:{scene.get('type', '随机')} | "
                f"穿搭:{styling.get('outfit_style', '随机')} | 表情:{styling.get('expression_type', '随机')} | "
                f"光影:{scene.get('lighting_type', '随机')}】"
            )
            # V12.39: preview 输出 token 估计（粗略：split 词数）
            token_est = len(prompt.split())
            print(f"  [token≈{token_est}]")
            print(prompt)
            print(f"\n【Negative Prompt - {pose_type}】")
            neg = generator.get_negative_prompt(pose_type, style=preview_style)
            print(f"  [neg-token≈{len(neg.split())}]")
            print(neg)

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

        # v12.43: 同时输出结构化 JSON（publish_wechat 优先消费此行；META: 行作为兼容 fallback）
        json_payload = {
            "version": VERSION,
            "count": len(result["images"]),
            "images": [
                {
                    "index": img.get("index"),
                    "url": img.get("url"),
                    "pose_type": img.get("pose_type", ""),
                    "scene_type": img.get("scene_type", ""),
                    "outfit_style": img.get("outfit_style", ""),
                    "expression_type": img.get("expression_type", ""),
                    "lighting_type": img.get("lighting_type", ""),
                    "art_style": img.get("art_style", ""),
                    "style": img.get("style", ""),
                }
                for img in result["images"]
            ],
        }
        print("RESULT_JSON: " + json.dumps(json_payload, ensure_ascii=False))
        return 0
    else:
        print(f"\n部分失败 ({result['count']}/{result['total']})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
