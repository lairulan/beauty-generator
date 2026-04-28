#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配文与标签生成。两 repo 共用，纯函数无副作用。"""

import random
import re
from datetime import date


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
    """加载手动提示词库"""
    prompts_file = CONFIG_DIR / "manual_prompts.json"
    if prompts_file.exists():
        with open(prompts_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": "1.0", "prompts": []}


def save_manual_prompt(prompt: str, caption: str = "", tags: str = "", title: str = "", image_url: str = ""):
    """保存手动提示词到库中（发布成功后自动调用）"""
    prompt = clean_manual_prompt(prompt)
    data = load_manual_prompts()
    # 计算下一个 ID
    next_id = max((p.get("id", 0) for p in data["prompts"]), default=0) + 1
    entry = {
        "id": next_id,
        "prompt": prompt,
        "caption": caption,
        "tags": tags,
        "title": title,
        "image_url": image_url,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    data["prompts"].append(entry)
    prompts_file = CONFIG_DIR / "manual_prompts.json"
    with open(prompts_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  📚 提示词已保存到库（ID: {next_id}）")
    return next_id


def list_manual_prompts():
    """列出所有已保存的手动提示词"""
    data = load_manual_prompts()
    prompts = data.get("prompts", [])
    if not prompts:
        print("📚 提示词库为空，还没有保存过手动提示词。")
        return
    print(f"📚 手动提示词库（共 {len(prompts)} 条）")
    print("=" * 60)
    for p in prompts:
        pid = p.get("id", "?")
        created = p.get("created_at", "")
        prompt_text = p.get("prompt", "")
        preview = prompt_text[:80] + "..." if len(prompt_text) > 80 else prompt_text
        caption = p.get("caption", "")
        print(f"  [{pid}] {created}")
        print(f"      Prompt: {preview}")
        if caption:
            print(f"      配文: {caption}")
        print()


def get_manual_prompt(prompt_id: int) -> dict:
    """按 ID 获取已保存的提示词"""
    data = load_manual_prompts()
    for p in data.get("prompts", []):
        if p.get("id") == prompt_id:
            return p
    return {}


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


# ── 风格开场文案（3条/风格，按日期轮换） ──────────────────────────
_STYLE_OPENERS = {
    "性感系": [
        "不经意间，眼神轻抬，万种风情自然流露。这种美，不需要解释。",
        "美从来不是刻意摆出来的，而是那一刻突然涌现的心跳。",
        "靠近，是本能。今日这帧，记得多看一眼。",
    ],
    "甜美系": [
        "笑起来眼睛弯弯的，甜度爆表，让人心情瞬间好起来。",
        "春风十里，不如今天这个微笑来得直接。",
        "今日份甜蜜准时送达，请查收。",
    ],
    "国风系": [
        "一袭古风，把岁月的柔情都装进了镜头里，东方美学从不过时。",
        "青砖黛瓦，美人如画。古典与现代之间，美总是共通的。",
        "千年审美，一帧定格。今天的国风，今天的她。",
    ],
    "邻家女孩系": [
        "转角遇见的美好，就是这种感觉——自然又温柔，不用力。",
        "不需要刻意，清新感扑面而来，像邻家姑娘的一个眼神。",
        "最喜欢这种不加滤镜的真实，干净，让人放松。",
    ],
    "职场系": [
        "干练中透着温柔，自信是最好的妆容。这种气场，无法复制。",
        "精致不失亲切，职场里最迷人的，是那份从容与笃定。",
        "气场全开，眼神里依然有温度。今日这帧，请认真欣赏。",
    ],
    "生活场景系": [
        "生活里最真实的美好，往往藏在平凡的瞬间。今天这一帧也是。",
        "烟火气里的她，才是最动人的模样——真实，鲜活，有温度。",
        "不是舞台，是生活，但每一帧都值得被珍藏。",
    ],
    "清纯系": [
        "干净的眼神，比任何滤镜都好看。清水出芙蓉，天然去雕饰。",
        "最纯粹的美，是不需要任何装饰的那种，自然天成。",
        "简单的美好，像一阵清风，让人心里安静下来。",
    ],
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
    "性感系": "今日写真 · 性感系",
    "甜美系": "今日写真 · 甜美系",
    "国风系": "今日写真 · 国风",
    "邻家女孩系": "今日写真 · 邻家女孩",
    "职场系": "今日写真 · 职场气质",
    "生活场景系": "今日写真 · 烟火日常",
    "清纯系": "今日写真 · 清纯系",
}


def generate_smart_caption(scene: str = "", emotion: str = "", makeup: str = "",
                           art_style: str = "", style: str = "",
                           image_url: str = "", prompt_text: str = "",
                           kind: str = "opener") -> str:
    """生成开场文案。

    新链路（image_url 非空时优先尝试）：Qwen-VL 看图 → DeepSeek 写文 → 历史去重 → 通过则返回。
    任一步失败回退到原有模板池逻辑，保证发布链路不阻塞。
    """
    from datetime import date

    # ── 新链路：LLM + VLM ────────────────────────────────────────────
    if image_url:
        try:
            from .llm_caption import generate_unique_caption
        except ImportError:
            try:
                from llm_caption import generate_unique_caption  # type: ignore
            except ImportError:
                generate_unique_caption = None  # type: ignore

        if generate_unique_caption is not None:
            meta = {
                "style": style,
                "scene_type": scene,
                "expression_type": emotion,
                "lighting_type": "",
                "outfit_style": "",
                "art_style": art_style,
            }
            llm_caption = generate_unique_caption(
                image_url=image_url,
                meta=meta,
                prompt_text=prompt_text,
                kind=kind,
            )
            if llm_caption:
                return llm_caption
            print("  ⚠️ LLM 文案不可用，回退到模板池")

    # ── 回退：原模板池逻辑 ───────────────────────────────────────────
    parts = []

    # 第1段：风格专属开场（按日期轮换，同一天同风格固定同一句）
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


def generate_image_caption(image_url: str = "", meta: dict | None = None,
                           prompt_text: str = "") -> str:
    """图片下方一句话配文。

    优先走 LLM short 模式（看图 + 14-22 字），失败回退到现有 meta/prompt 模板。
    """
    meta = meta or {}

    if image_url:
        try:
            from .llm_caption import generate_unique_caption
        except ImportError:
            try:
                from llm_caption import generate_unique_caption  # type: ignore
            except ImportError:
                generate_unique_caption = None  # type: ignore

        if generate_unique_caption is not None:
            text = generate_unique_caption(
                image_url=image_url,
                meta=meta,
                prompt_text=prompt_text,
                tone="short",
                kind="short",
            )
            if text:
                return text

    # 回退：原模板逻辑
    if prompt_text:
        return generate_caption_from_prompt(prompt_text)
    if meta and meta.get("scene_type") and meta.get("scene_type") != "custom":
        return generate_caption_from_meta(meta)
    return "今日份心动瞬间。"
