#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号发布脚本 V12.38
将生成的美女图片发布到公众号草稿箱（小绿书形式）
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

# 脚本目录
SCRIPT_DIR = Path(__file__).parent.absolute()
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
BEAUTY_GENERATE_SCRIPT = SKILL_DIR / "scripts" / "generate_beauty.py"

# 加载 skill 根目录的 .env（QWEN/DEEPSEEK 等 key），不覆盖已有环境变量
def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    except Exception:
        pass


_load_dotenv(SKILL_DIR / ".env")

# 本地 lib（与 i2i 保持同源）
sys.path.insert(0, str(SCRIPT_DIR))
from lib.wechat_api import publish_to_wechat, get_api_key
from lib.captions import (  # noqa: E402
    generate_image_caption,
    generate_smart_article,
    generate_smart_caption as generate_smart_caption_llm,
)

# 公众号配置
DEFAULT_APPID = "wx287cdb9d78a498aa"  # 三更熟
FORCED_STYLE = "性感系"
FORCED_EMOTION = "性感"

MANUAL_PROMPT_LOG_PREFIX_RE = re.compile(
    r"^\s*\[\d{4}-\d{2}-\d{2}\s+[0-9:]+\]\s+\[(?:INFO|WARN|ERROR)\]\s+随机种子:\s*\d+\s*"
)


def clean_manual_prompt(prompt: str) -> str:
    """移除误复制进手动 prompt 的本地日志前缀。"""
    if not prompt:
        return ""
    return MANUAL_PROMPT_LOG_PREFIX_RE.sub("", str(prompt).strip(), count=1).strip()


def generate_caption_from_meta(meta: dict) -> str:
    """基于图片元数据动态生成图片配文（2句，场景+表情组合）

    meta 结构: {scene_type, outfit_style, expression_type, lighting_type, art_style}
    """
    import random

    scene = meta.get("scene_type", "")
    outfit = meta.get("outfit_style", "")
    # 修复：自动将 workflow emotion 值映射到 expr_phrases key
    raw_expr = meta.get("expression_type", "")
    expression = _EMOTION_ALIAS.get(raw_expr, raw_expr)
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

    # 补第2句：从光影/穿搭里再取一个维度
    if len(parts) == 1:
        if lighting and lighting in light_phrases:
            candidate = random.choice(light_phrases[lighting])
            if candidate not in parts:
                parts.append(candidate)
        elif outfit and outfit in outfit_phrases:
            candidate = random.choice(outfit_phrases[outfit])
            if candidate not in parts:
                parts.append(candidate)

    # 保底：至少有一句
    if not parts:
        fallback = ["今日份心动瞬间", "美好值得被定格", "每一帧都是风景",
                     "镜头里的温柔", "光影之间的故事", "被美好击中的瞬间"]
        parts.append(random.choice(fallback))

    # 组合：最多2句
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


def generate_caption_from_prompt(prompt: str) -> str:
    """基于用户自定义英文提示词，提取关键元素生成中文配文"""
    import random

    prompt_lower = prompt.lower()

    import re

    # --- 场景关键词 -> 中文描写 ---
    # 长关键词优先匹配（子串安全）
    scene_map = {
        "izakaya": ["居酒屋的烟火气", "昏黄灯光下的深夜食堂", "日式小酒馆的温暖"],
        "coffee shop": ["咖啡香里的慵懒时光", "午后咖啡馆的邂逅"],
        "cherry blossom": ["樱花树下的约定", "春风十里不如你"],
        "cafe": ["咖啡香里的慵懒时光", "午后咖啡馆的邂逅"],
        "beach": ["海风轻抚的温柔", "浪花写下的情书", "海边的自在"],
        "ocean": ["海风轻抚的温柔", "海与天的交界处"],
        "street": ["街角转弯遇见美好", "街拍质感满分"],
        "garden": ["花园里的秘密", "被花包围的浪漫时光"],
        "forest": ["林间光影斑驳", "绿意盎然的画面"],
        "snow": ["初雪的浪漫", "雪景里的温柔"],
        "temple": ["古寺中的静谧", "青砖黛瓦间的古典美"],
        "library": ["书香气里的安静", "图书馆的光影"],
        "kitchen": ["厨房里的烟火气", "生活最真实的模样"],
        "bedroom": ["窗边的慵懒时光", "清晨最柔软的光"],
        "rooftop": ["天台上的风和故事", "城市上空的自由"],
        "train": ["列车窗外的风景", "旅途中的偶遇"],
        "subway": ["地铁里的一瞬间", "城市脉搏里的故事"],
        "park": ["公园里的闲适", "阳光和绿荫最配"],
        "mountain": ["山间的清风", "远方的风景值得追寻"],
        "sunset": ["日落把一切都镀了金", "黄昏是最浪漫的滤镜"],
        "sunflower": ["向日葵田里的笑容", "被阳光追着跑的季节"],
        "sakura": ["樱花树下的约定", "花瓣落满肩头"],
        "pool": ["泳池边的夏日", "水光粼粼的午后"],
        "hotel": ["旅途中的小憩", "酒店窗边的风景"],
        "market": ["市集里的烟火气", "人间烟火最抚人心"],
        "restaurant": ["美食与美人都不可辜负", "餐厅的暖光里"],
        "balcony": ["阳台上的小世界", "阳台是家里最浪漫的角落"],
        "window": ["窗边的光影故事", "透过窗户看世界"],
    }

    # 需要词边界匹配的短关键词（避免 rain/grain, bar/sidebar, night/nightlife 误匹配）
    scene_word_boundary = {
        "bar": ["吧台边的微醺时光", "酒杯里映着的故事", "深夜酒吧的低语"],
        "rain": ["雨天自带电影感", "雨中的浪漫"],
        "city": ["城市光影中的故事", "都市里的片刻宁静"],
        "night": ["夜色温柔", "深夜的故事最动人"],
    }

    # --- 情绪/氛围关键词 -> 中文描写 ---
    mood_map = {
        "smile": ["笑容是最好的滤镜", "嘴角上扬的弧度刚好"],
        "gentle": ["温柔是最好的答案", "岁月温柔以待"],
        "sweet": ["甜度爆表", "甜到心里了"],
        "sexy": ["恰到好处的性感", "眼角眉梢全是故事"],
        "elegant": ["优雅是骨子里的气质", "美得不动声色"],
        "nostalgic": ["怀旧的色调最有故事", "时光在这里慢下来"],
        "candid": ["不经意的瞬间最动人", "真实的样子最美"],
        "intimate": ["亲密的氛围感", "靠近一点，再靠近一点"],
        "cozy": ["温暖的氛围感拉满", "想把这一刻留住"],
        "melancholy": ["微微忧郁的眼神", "故事写在眼睛里"],
        "confident": ["自信是最好的妆容", "气场全开"],
        "mysterious": ["神秘感刚刚好", "让人想靠近的距离感"],
        "playful": ["古灵精怪招人爱", "元气少女上线"],
        "dreamy": ["梦幻般的画面", "像走进了一场梦"],
        "lonely": ["独处的时光也很美", "一个人的风景"],
    }

    # --- 风格关键词 -> 中文描写 ---
    style_map = {
        "film": ["胶片质感的温柔", "每一帧都像电影"],
        "analog": ["复古胶片的色调真好看", "模拟胶片的温度"],
        "vintage": ["复古的色调最有味道", "时光倒流的美感"],
        "kodak": ["柯达色调的浪漫", "胶片里的光影故事"],
        "portra": ["Portra色调就是yyds", "胶片感拉满"],
        "cinematic": ["电影感十足", "每一帧都值得截图"],
        "wong kar-wai": ["王家卫式的光影", "暧昧的色调太绝了"],
        "moriyama": ["森山大道式的粗粝", "街头的诗意"],
        "showa": ["昭和风的怀旧感", "那个年代的浪漫"],
        "retro": ["复古风永不过时", "旧时光的美好"],
    }

    parts = []

    # 匹配场景（先查子串安全的长关键词）
    matched_scene = False
    for key, phrases in scene_map.items():
        if key in prompt_lower:
            parts.append(random.choice(phrases))
            matched_scene = True
            break

    # 再查需要词边界的短关键词
    if not matched_scene:
        for key, phrases in scene_word_boundary.items():
            if re.search(r'\b' + re.escape(key) + r'\b', prompt_lower):
                parts.append(random.choice(phrases))
                break

    # 匹配情绪
    for key, phrases in mood_map.items():
        if key in prompt_lower:
            parts.append(random.choice(phrases))
            break

    # 如果不够2句，匹配风格
    if len(parts) < 2:
        for key, phrases in style_map.items():
            if key in prompt_lower:
                parts.append(random.choice(phrases))
                break

    # 保底
    if not parts:
        fallback = ["今日份心动瞬间", "美好值得被定格", "镜头里的温柔",
                     "光影之间的故事", "被美好击中的瞬间", "每一帧都是风景"]
        parts.append(random.choice(fallback))

    if len(parts) >= 2:
        return f"{parts[0]}，{parts[1]}。"
    return f"{parts[0]}。"


def load_manual_prompts() -> dict:
    """加载手动提示词库（thin wrapper over lib.manual_prompts.load_manual_prompts）。"""
    from lib.manual_prompts import load_manual_prompts as _lib_load
    return _lib_load(CONFIG_DIR / "manual_prompts.json")


def save_manual_prompt(prompt: str, caption: str = "", tags: str = "", title: str = "", image_url: str = "") -> int:
    """保存手动提示词到库中。"""
    from lib.manual_prompts import save_manual_prompt as _lib_save
    return _lib_save(
        CONFIG_DIR / "manual_prompts.json",
        prompt=prompt,
        caption=caption,
        tags=tags,
        title=title,
        image_url=image_url,
    )


def list_manual_prompts():
    """列出所有已保存的手动提示词。"""
    from lib.manual_prompts import list_manual_prompts as _lib_list
    return _lib_list(CONFIG_DIR / "manual_prompts.json")


def get_manual_prompt(prompt_id: int) -> dict:
    """按 ID 获取已保存的提示词。"""
    from lib.manual_prompts import get_manual_prompt as _lib_get
    return _lib_get(CONFIG_DIR / "manual_prompts.json", prompt_id)


def generate_tags_from_prompt(prompt: str) -> str:
    """基于用户自定义英文提示词生成话题标签"""
    import re
    prompt_lower = prompt.lower()
    tags = ["#每日美女", "#写真"]

    tag_map = {
        "izakaya": "#日式居酒屋", "cafe": "#咖啡时光",
        "coffee shop": "#咖啡时光", "beach": "#海边", "ocean": "#海边",
        "street": "#街拍", "garden": "#花园",
        "forest": "#户外写真", "temple": "#国风",
        "sunset": "#日落", "pool": "#泳池",
        "sakura": "#樱花", "cherry blossom": "#樱花",
        "sunflower": "#向日葵",
        "kodak": "#胶片质感", "cinematic": "#电影感",
        "wong kar-wai": "#王家卫", "showa": "#昭和风",
        "vintage": "#复古", "retro": "#复古",
        "candid": "#抓拍", "cozy": "#氛围感",
    }

    # 需要词边界匹配的短关键词（避免 rain/grain, bar/ebar 等误匹配）
    word_boundary_tags = {
        "bar": "#深夜酒吧", "rain": "#雨天", "night": "#夜景",
        "city": "#都市", "film": "#胶片质感", "sexy": "#性感",
        "sweet": "#甜美", "elegant": "#优雅", "gentle": "#温柔",
    }

    for key, tag in tag_map.items():
        if key in prompt_lower and tag not in tags:
            tags.append(tag)
        if len(tags) >= 5:
            break

    if len(tags) < 5:
        for key, tag in word_boundary_tags.items():
            if re.search(r'\b' + re.escape(key) + r'\b', prompt_lower) and tag not in tags:
                tags.append(tag)
            if len(tags) >= 5:
                break

    tags.append("#人像摄影")
    return " ".join(tags[:6])


# ── 风格开场文案（性感系固定） ────────────────────────────────
_STYLE_OPENERS = {
    "性感系": [
        "不经意间，眼神轻抬，万种风情自然流露。这种美，不需要解释。",
        "美从来不是刻意摆出来的，而是那一刻突然涌现的心跳。",
        "靠近，是本能。今日这帧，记得多看一眼。",
    ]
}

# ── workflow emotion 值 → 补充结尾句 ───────────────────────────────
_EMOTION_CLOSERS = {
    "挑逗": "眼角眉梢都是故事，靠近，是本能。",
    "俏皮": "灵动的眼神藏着小心思，古灵精怪招人爱。",
    "温柔": "温柔是最让人心动的力量，久久回味。",
    "自信": "这样的她，发光。不需要理由，只需要欣赏。",
    "微笑": "一个微笑，就足以让这一天变得不同。",
    "性感": "这种美，带着温度，有点危险，却让人想靠近。",
}

# ── workflow emotion → expr_phrases key（修复匹配缺失） ────────────
_EMOTION_ALIAS = {
    "挑逗": "性感妩媚",
    "俏皮": "俏皮灵动",
    "温柔": "清纯自然",
    "自信": "优雅端庄",
    "微笑": "甜美微笑",
    "性感": "性感妩媚",
}

# ── 风格标题（更有辨识度） ──────────────────────────────────────────
STYLE_TITLES = {
    "性感系": "今日写真 · 性感系"
}


def generate_smart_caption(scene: str = "", emotion: str = "", makeup: str = "", art_style: str = "", style: str = "") -> str:
    """生成开场文案（2段，风格感更强）"""
    from datetime import date

    parts = []

    # 第1段：性感写真开场（同一天固定同一句，保持发布稳定）
    if style and style in _STYLE_OPENERS:
        idx = date.today().toordinal() % len(_STYLE_OPENERS[style])
        parts.append(_STYLE_OPENERS[style][idx])

    # 第2段：emotion 补充结尾句
    if emotion and emotion in _EMOTION_CLOSERS:
        parts.append(_EMOTION_CLOSERS[emotion])

    # 没有 style 时回退到基于 meta 的旧逻辑
    if not parts:
        # 修复：将 workflow emotion 值映射到 expr_phrases key
        mapped_emotion = _EMOTION_ALIAS.get(emotion, emotion)
        base = generate_caption_from_meta({
            "scene_type": scene,
            "expression_type": mapped_emotion,
            "art_style": art_style,
        })

        makeup_phrases = {
            "韩妆": "韩系妆感更显清透",
            "欧美妆": "欧美妆感把轮廓衬得更立体",
            "烟熏妆": "烟熏妆把氛围感拉满",
            "玻璃妆": "玻璃肌质感很适合近景",
            "裸妆": "裸妆更贴近自然抓拍感",
            "红唇妆": "红唇让画面更有记忆点",
        }
        art_phrases = {
            "电影感": "电影感色调让故事更完整",
            "王家卫": "王家卫式氛围格外迷人",
            "韩剧": "韩剧感光影自带温柔滤镜",
            "时尚杂志": "时尚杂志感让镜头更高级",
            "ins风": "ins 风构图干净又轻盈",
            "暗调": "暗调氛围更显情绪张力",
            "复古胶片": "复古胶片感把时间都放慢了",
        }
        details = []
        if makeup:
            details.append(makeup_phrases.get(makeup, f"{makeup}细节也很加分"))
        if art_style:
            details.append(art_phrases.get(art_style, f"{art_style}氛围很有辨识度"))
        if details:
            base = base[:-1] if base.endswith("。") else base
            parts.append(f"{base}，{details[0]}。")
        else:
            parts.append(base)

    return "\n\n".join(parts)


def generate_one_line_caption(style: str = "") -> str:
    """生成一句话介绍（兼容旧接口）"""
    return generate_smart_caption()


def _extract_images_with_meta(output: str) -> list:
    """从脚本输出中提取图片 URL 和 META 元数据。

    优先解析结构化 JSON 行（v12.43+ 增加）：
        RESULT_JSON: {"images": [{"url": "...", "scene_type": "...", ...}, ...]}
    若未找到 RESULT_JSON，回退到旧版 stdout 双行扫描：
        <url>
        META:场景|穿搭|表情|光影|艺术风格

    返回: [(url, meta_dict), ...]
    """
    import re
    import json as _json

    # 1) 优先解析结构化 JSON
    for line in output.split("\n"):
        s = line.strip()
        if not s.startswith("RESULT_JSON:"):
            continue
        try:
            payload = _json.loads(s[len("RESULT_JSON:"):].strip())
        except (ValueError, TypeError):
            continue
        images = payload.get("images") or []
        results = []
        for img in images:
            url = img.get("url")
            if not url:
                continue
            meta = {
                "scene_type": img.get("scene_type", ""),
                "outfit_style": img.get("outfit_style", ""),
                "expression_type": img.get("expression_type", ""),
                "lighting_type": img.get("lighting_type", ""),
                "art_style": img.get("art_style", ""),
            }
            results.append((url, meta))
        if results:
            return results

    # 2) 回退到旧版 META: 行扫描（向下兼容）
    results = []
    lines = output.split("\n")

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("http"):
            continue
        # 匹配所有已知图片 URL 来源
        if any(domain in stripped for domain in [
            "ark-content", "doubao", "volces.com",
            "imgbb", "i.ibb.co", "ibb.co",
            "imgur.com",
            "sm.ms", "loli.net",
        ]):
            urls = re.findall(r'https?://[^\s\)\]"\']+', stripped)
            for url in urls:
                # 向后查找对应的 META 行
                meta = {}
                found_meta = False
                for j in range(i + 1, min(i + 3, len(lines))):
                    if lines[j].strip().startswith("META:"):
                        found_meta = True
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
                if found_meta:
                    results.append((url, meta))
    return results


def _extract_image_urls(output: str) -> list:
    """兼容旧接口：只返回 URL 列表"""
    return [url for url, _ in _extract_images_with_meta(output)]


def generate_daily_images(
    count: int = 3,
    style: str = "",
    scene: str = "",
    emotion: str = "",
    prompt: str = "",
) -> list:
    """
    生成多张一致性人物图片
    使用双引擎 (Google Imagen 4 Ultra + Doubao Seedream 4.5 fallback)

    prompt: 手动模式 - 直接使用用户自定义提示词（跳过随机元素库）
    返回: [(url, meta_dict), ...]  meta 含 scene_type/outfit_style/expression_type/lighting_type/art_style
    """
    import re

    images_with_meta = []

    if prompt:
        print(f"\n🎨 [手动模式] 正在使用自定义提示词生成 {count} 张图片...")
    else:
        if style and style != FORCED_STYLE:
            print(f"⚠️ 自动文生图已固定为{FORCED_STYLE}，忽略传入风格：{style}")
        if emotion and emotion != FORCED_EMOTION:
            print(f"⚠️ 自动文生图已固定为{FORCED_EMOTION}表达，忽略传入情绪：{emotion}")
        style = FORCED_STYLE
        emotion = FORCED_EMOTION
        print(f"\n🎨 [自动模式] 正在生成 {count} 张{FORCED_STYLE}图片 (Google Imagen 4 Ultra → 豆包 Seedream 4.5 fallback)...")

    cmd = [
        "python3", str(BEAUTY_GENERATE_SCRIPT),
        "--count", str(count)
    ]
    if prompt:
        cmd.extend(["--prompt", prompt])
    elif style:
        cmd.extend(["--style", style])
    if scene and not prompt:
        cmd.extend(["--scene", scene])
    if emotion and not prompt:
        cmd.extend(["--emotion", emotion])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
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
        print("  ❌ 生成超时 (600s)")
    except Exception as e:
        print(f"  ❌ 生成异常: {e}")

    return images_with_meta


def main():
    parser = argparse.ArgumentParser(
        description="每日美女图 - 发布到公众号"
    )

    parser.add_argument("--count", "-c", type=int, default=1, help="生成图片数量（默认1张）")
    parser.add_argument("--prompt", help="手动模式：直接使用自定义提示词生成（跳过随机元素库）")
    parser.add_argument("--caption-text", help="手动模式下的自定义配文（可选，不提供则用默认）")
    parser.add_argument("--style", "-s", help="自动模式固定为性感系；其他值仅兼容接收")
    parser.add_argument("--scene", help="自动模式只保留性感系场景：室内、城市、特殊")
    parser.add_argument("--emotion", help="自动模式固定为性感表达；其他值仅兼容接收")
    parser.add_argument("--makeup", help="妆容关键词：用于补充介绍文案")
    parser.add_argument("--art-style", help="艺术风格关键词：用于补充介绍文案")
    parser.add_argument("--appid", help="公众号 AppID（默认：三更熟）")
    parser.add_argument("--title", "-t", help="文章标题（自动生成默认）")
    parser.add_argument("--caption", help="小绿书开场一句话（自动生成默认）")
    parser.add_argument("--list-prompts", action="store_true", help="列出已保存的手动提示词库")
    parser.add_argument("--use-prompt", type=int, metavar="ID", help="使用已保存的提示词（按 ID）")
    parser.add_argument("--test", action="store_true", help="测试模式：只生成不发布")
    parser.add_argument("--type", choices=["news", "newspic"], default="newspic", help="文章类型")

    args = parser.parse_args()
    loaded_prompt_from_library = False

    # 列出提示词库
    if args.list_prompts:
        list_manual_prompts()
        return 0

    # 从库中加载提示词
    if args.use_prompt:
        saved = get_manual_prompt(args.use_prompt)
        if not saved:
            print(f"❌ 未找到 ID={args.use_prompt} 的提示词，请用 --list-prompts 查看可用列表")
            return 1
        loaded_prompt_from_library = True
        args.prompt = clean_manual_prompt(saved["prompt"])
        if not args.caption_text and saved.get("caption"):
            args.caption_text = saved["caption"]
        if not args.title and saved.get("title"):
            args.title = saved["title"]
        print(f"📚 已加载提示词库 ID={args.use_prompt}")
        print(f"   Prompt: {args.prompt[:80]}...")

    if args.prompt:
        args.prompt = clean_manual_prompt(args.prompt)

    # 发布模式才需要公众号 API Key
    if not args.test and not get_api_key():
        print("❌ 环境变量 WECHAT_API_KEY 未设置")
        return 1

    # 获取今日主题
    today = date.today()
    weekday_str = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][today.weekday()]

    # 判断模式
    is_manual = bool(args.prompt)
    if not is_manual:
        if args.style and args.style != FORCED_STYLE:
            print(f"⚠️ 自动文生图已固定为{FORCED_STYLE}，忽略传入风格：{args.style}")
        if args.emotion and args.emotion != FORCED_EMOTION:
            print(f"⚠️ 自动文生图已固定为{FORCED_EMOTION}表达，忽略传入情绪：{args.emotion}")
        args.style = FORCED_STYLE
        args.emotion = FORCED_EMOTION
    should_save_manual_prompt = is_manual and bool(args.prompt) and not loaded_prompt_from_library

    # 标题：优先用户 --title；否则等图生成后由 LLM "图启思考"输出 title 字段填充
    # 模板兜底（v2 已不再使用，仅在 LLM 全失败时启用）
    fallback_title = None
    if not args.title:
        if is_manual:
            fallback_title = "📸 每日写真 | 手动精选"
        elif args.style and args.style in STYLE_TITLES:
            fallback_title = f"📸 {STYLE_TITLES[args.style]}"
        else:
            fallback_title = f"📸 今日写真 · {weekday_str}"

    print("=" * 50)
    print(f"📅 日期: {today}")
    if is_manual:
        print(f"🔧 模式: 手动提示词")
        print(f"📝 Prompt: {args.prompt[:100]}...")
    else:
        print(f"🔧 模式: 自动（元素库随机）")
    print(f"📋 标题: {args.title or '(待 LLM 生成)'}")
    if args.scene:
        print(f"🎬 场景: {args.scene}")
    if args.emotion:
        print(f"😊 情绪: {args.emotion}")
    print("=" * 50)

    # 生成图片（返回 [(url, meta), ...]）
    images_with_meta = generate_daily_images(
        args.count,
        args.style,
        args.scene or "",
        args.emotion or "",
        prompt=args.prompt or "",
    )

    if len(images_with_meta) == 0:
        print("❌ 没有成功生成任何图片")
        return 1

    print(f"\n✅ 成功生成 {len(images_with_meta)} 张图片")

    # 用第一张图喂 VLM + LLM，生成长开场（args.caption）
    first_url = images_with_meta[0][0] if images_with_meta else ""
    first_meta_for_opener = images_with_meta[0][1] if images_with_meta else {}
    if not args.caption:
        print("\n💬 正在用 VLM+LLM 生成图启思考短文（标题+正文）...")
        article = generate_smart_article(
            image_url=first_url,
            meta=first_meta_for_opener,
            prompt_text=args.prompt or "",
            style=args.style or "",
        )
        if article:
            # 用 LLM 生成的标题（覆盖 fallback）
            if not args.title:
                args.title = article["title"]
            args.caption = article["body"]
            print(f"📋 标题: {args.title}")
        else:
            # 全失败回退：用模板标题 + 老的 generate_smart_caption_llm
            print("  ⚠️ 哲思短文生成失败，回退到旧文案链路")
            if not args.title:
                args.title = fallback_title
            args.caption = generate_smart_caption_llm(
                scene=args.scene or "",
                emotion=args.emotion or "",
                makeup=args.makeup or "",
                art_style=args.art_style or "",
                style=args.style or "",
                image_url=first_url,
                prompt_text=args.prompt or "",
                kind="opener",
            )
    elif not args.title:
        # 用户给了 caption 但没给标题，用 fallback
        args.title = fallback_title
    print(f"💬 介绍:\n{args.caption}")

    # 手动模式：用户显式给的 caption_text 优先（覆盖 LLM 短文）
    manual_caption_override = args.caption_text if (is_manual and args.caption_text) else None

    # 测试模式
    if args.test:
        print("\n🧪 测试模式：不发布到公众号")
        print("\n生成的图片链接:")
        for i, (url, meta) in enumerate(images_with_meta, 1):
            if manual_caption_override:
                caption = manual_caption_override
            else:
                caption = generate_image_caption(
                    image_url=url,
                    meta=meta or {},
                    prompt_text=args.prompt or "",
                )

            if is_manual and args.prompt:
                tags = generate_tags_from_prompt(args.prompt)
            else:
                tags = generate_tags_from_meta(meta) if meta else "#每日美女 #写真 #人像摄影 #今日心动"
            print(f"  {i}. {url}")
            print(f"     配文: {caption}")
            print(f"     标签: {tags}")
        return 0

    # 发布到公众号
    appid = args.appid or DEFAULT_APPID

    print(f"\n📤 正在发布到公众号...")

    # 构建图片和说明配对（LLM 短文 + 历史去重，撞库自动重生）
    image_pairs = []
    first_meta = first_meta_for_opener

    for i, (img_url, meta) in enumerate(images_with_meta):
        if manual_caption_override:
            caption = manual_caption_override
        else:
            caption = generate_image_caption(
                image_url=img_url,
                meta=meta or {},
                prompt_text=args.prompt or "",
            )
        image_pairs.append((img_url, caption))

    # 标签：手动模式从 prompt 智能生成，自动模式基于元数据
    if is_manual and args.prompt:
        dynamic_tags = generate_tags_from_prompt(args.prompt)
    else:
        dynamic_tags = generate_tags_from_meta(first_meta) if first_meta else "#每日美女 #写真 #人像摄影 #今日心动"
    print(f"🏷️ 标签: {dynamic_tags}")

    result = publish_to_wechat(
        appid=appid,
        title=args.title,
        content=args.caption or "",
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
        # 只有直接输入的新 prompt 才自动保存；复用库内 prompt 不重复入库。
        if should_save_manual_prompt:
            first_url = images_with_meta[0][0] if images_with_meta else ""
            save_manual_prompt(
                prompt=args.prompt,
                caption=manual_caption_override or "",
                tags=dynamic_tags,
                title=args.title,
                image_url=first_url,
            )
        elif is_manual and loaded_prompt_from_library:
            print("  📚 使用已保存提示词，本次不重复保存到库")
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
