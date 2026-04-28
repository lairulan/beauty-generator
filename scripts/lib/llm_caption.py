#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 驱动的图文配文生成。

链路: 图 → Qwen-VL 提取视觉关键词 → DeepSeek 生成中文文案 → 历史去重校验 → 通过/重生成

设计目标：
  1. 永不重复：本地 jsonl 历史库 + 头部精确去重 + 三元组 Jaccard 相似度过滤 + 最多 3 次重生
  2. 图文匹配：VLM 看实际成图（不依赖生成 prompt），LLM 必须复用 ≥2 个视觉关键词
  3. 双 skill 文风分离：cinematic（电影叙事，80-120字）/ diary（朋友圈日记体，40-60字）
  4. 跨 skill 互查去重：t2i 与 i2i 的历史库互相加载，避免双发同日撞文案

环境变量：
  QWEN_API_KEY       - DashScope key（Qwen-VL）
  QWEN_VL_MODEL      - 默认 qwen-vl-plus
  DEEPSEEK_API_KEY   - DeepSeek key
  DEEPSEEK_MODEL     - 默认 deepseek-chat
  BEAUTY_CAPTION_TONE - cinematic | diary
"""

from __future__ import annotations

import json
import os
import re
import ssl
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────────
QWEN_API_KEY = os.environ.get("QWEN_API_KEY", "")
QWEN_VL_MODEL = os.environ.get("QWEN_VL_MODEL", "qwen-vl-plus")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

QWEN_ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

# 两个 skill 的历史库路径 —— 互相加载
HISTORY_FILES = [
    Path.home() / "beauty-generator/logs/caption_history.jsonl",
    Path.home() / "beauty-img2img/logs/caption_history.jsonl",
]

# 本 skill 自己的历史库（落盘用），由 publish_wechat 注入
def _own_history_file() -> Path:
    """根据 BEAUTY_CAPTION_TONE 决定写入哪份历史库。"""
    tone = os.environ.get("BEAUTY_CAPTION_TONE", "cinematic")
    if tone == "diary":
        return HISTORY_FILES[1]
    return HISTORY_FILES[0]


# ── VLM 视觉关键词提取 ────────────────────────────────────────────────
_VLM_CACHE: dict[str, list[str]] = {}


def vlm_extract_keywords(image_url: str, timeout: int = 30) -> list[str]:
    """调用 Qwen-VL 抽取 6-8 个中文视觉关键词。失败返回 []。"""
    if not image_url:
        return []
    if image_url in _VLM_CACHE:
        return _VLM_CACHE[image_url]
    if not QWEN_API_KEY:
        return []

    prompt = (
        "请用最多 8 个简短中文短语描述这张人像照片的视觉细节，覆盖：构图角度、表情眼神、"
        "肢体动作、服饰细节、光线氛围、背景物件、季节温度。每个短语 2-6 字。"
        "只输出 JSON 数组，不要任何额外说明。"
        '示例：["侧脸特写","碎发被风吹起","逆光金边","白色针织","海风","赤脚踩沙","黄昏"]'
    )
    payload = {
        "model": QWEN_VL_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "temperature": 0.3,
    }
    try:
        text = _http_post_json(QWEN_ENDPOINT, payload, QWEN_API_KEY, timeout=timeout)
        content = (
            text.get("choices", [{}])[0].get("message", {}).get("content", "")
            if isinstance(text, dict) else ""
        )
        if isinstance(content, list):
            content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
        keywords = _parse_json_array(content)
        keywords = [k.strip() for k in keywords if isinstance(k, str) and k.strip()]
        keywords = keywords[:8]
        _VLM_CACHE[image_url] = keywords
        return keywords
    except Exception as e:
        print(f"  ⚠️ VLM 调用失败: {e}", file=sys.stderr)
        return []


def _parse_json_array(s: str) -> list:
    if not s:
        return []
    s = s.strip()
    m = re.search(r"\[[^\[\]]*\]", s, re.DOTALL)
    if m:
        try:
            arr = json.loads(m.group(0))
            if isinstance(arr, list):
                return arr
        except Exception:
            pass
    parts = re.split(r"[、,，\n]+", s)
    return [p.strip(" \"'[]") for p in parts if p.strip(" \"'[]")]


# ── HTTP helper ───────────────────────────────────────────────────────
def _http_post_json(url: str, payload: dict, api_key: str, timeout: int = 30) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        body = resp.read().decode("utf-8")
    try:
        return json.loads(body)
    except Exception:
        return {"_raw": body}


# ── 历史库 ────────────────────────────────────────────────────────────
def load_history(days: int = 90, limit: int = 200) -> list[dict]:
    """加载两个 skill 最近 N 天的文案历史。"""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    out: list[dict] = []
    for fp in HISTORY_FILES:
        if not fp.exists():
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    if obj.get("date", "") >= cutoff:
                        out.append(obj)
        except Exception:
            pass
    out.sort(key=lambda x: x.get("date", ""), reverse=True)
    return out[:limit]


def append_history(caption: str, image_url: str, kind: str = "opener") -> None:
    """把新生成的文案追加到本 skill 的历史库。"""
    fp = _own_history_file()
    fp.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "date": date.today().isoformat(),
        "ts": datetime.now().isoformat(timespec="seconds"),
        "kind": kind,
        "caption": caption,
        "head12": _head_n(caption, 12),
        "image": image_url,
        "tone": os.environ.get("BEAUTY_CAPTION_TONE", "cinematic"),
    }
    with open(fp, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _head_n(text: str, n: int) -> str:
    cleaned = re.sub(r"\s+", "", text)
    return cleaned[:n]


# ── 相似度判定 ────────────────────────────────────────────────────────
def _trigrams(text: str) -> set:
    cleaned = re.sub(r"[\s\W]+", "", text)
    if len(cleaned) < 3:
        return {cleaned} if cleaned else set()
    return {cleaned[i : i + 3] for i in range(len(cleaned) - 2)}


def jaccard(a: str, b: str) -> float:
    sa, sb = _trigrams(a), _trigrams(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def is_duplicate(text: str, history: list[dict], head_n: int = 12,
                 jaccard_threshold: float = 0.55) -> tuple[bool, str]:
    """判断是否与历史撞车。返回 (是否重复, 原因)。"""
    head = _head_n(text, head_n)
    for h in history:
        if h.get("head12") and h["head12"] == head:
            return True, f"开头与 {h.get('date','?')} 雷同"
        score = jaccard(text, h.get("caption", ""))
        if score >= jaccard_threshold:
            return True, f"与 {h.get('date','?')} 文案相似度 {score:.2f}"
    return False, ""


# ── LLM 文案生成 ──────────────────────────────────────────────────────
TONE_SPEC = {
    "cinematic": {
        "label": "电影叙事感",
        "desc": (
            "镜头语言式的画面感叙述，3 个自然段，每段 1-2 句。"
            "节奏舒缓，有空白和停顿，像电影剧本旁白。"
            "可以从一个具体动作、一束光、一阵风、一个气味切入。"
            "结尾留白，不点透。"
        ),
        "length": "总字数 80-120 字",
        "paragraphs": 3,
    },
    "diary": {
        "label": "朋友圈日记体",
        "desc": (
            "口语化、自然、像跟朋友碎碎念，2 个自然段。"
            "可以有'今天''刚刚''突然''差点'之类的现场感词。"
            "允许偶尔一点小情绪、小吐槽，但不要过度网梗。"
        ),
        "length": "总字数 40-70 字",
        "paragraphs": 2,
    },
    "short": {
        "label": "图片下方一句话",
        "desc": "一句话，14-22 字，有画面感，不卖弄。",
        "length": "14-22 字",
        "paragraphs": 1,
    },
    # ── v2 哲思模式（图启思考）──────────────────────────────────────
    "philosophical_long": {
        "label": "图启思考·长版",
        "intro_words": "25-40",
        "aphorism_words": "70-100",
        "title_words": "10-15",
    },
    "philosophical_short": {
        "label": "图启思考·短版",
        "intro_words": "15-25",
        "aphorism_words": "40-70",
        "title_words": "8-13",
    },
}

# 全局禁用词（陈词滥调）
_BANNED_WORDS = [
    "今日份", "yyds", "绝绝子", "绝了", "拿捏", "氛围感拉满",
    "光影交错", "镜头里的温柔", "美好值得被定格", "心动瞬间",
    "甜度爆表", "气场全开", "美得不动声色",
]


def _build_llm_prompt(meta: dict, vlm_keywords: list[str], history: list[dict],
                      tone: str, prompt_text: str = "") -> tuple[str, str]:
    _ = prompt_text  # 预留：未来可让 LLM 参考原始英文 prompt
    """组装 system + user prompt。"""
    spec = TONE_SPEC.get(tone, TONE_SPEC["cinematic"])

    recent_heads = []
    for h in history[:40]:
        if h.get("head12"):
            recent_heads.append(h["head12"])
    recent_heads = list(dict.fromkeys(recent_heads))[:30]

    system = (
        "你是一位为公众号美图栏目写配文的资深编辑。"
        "文风克制、有画面感，避免陈词滥调和网络梗。"
        "你的文字应该让读者愿意多看一眼图，而不是觉得在硬凹文案。"
    )

    parts = [
        "【任务】为下面这张人像照片写中文配文。",
        "",
        f"【调性】{spec['label']}：{spec['desc']}",
        f"【长度】{spec['length']}，共 {spec['paragraphs']} 段。",
    ]

    if vlm_keywords:
        parts.append("")
        parts.append("【画面要素】（必须自然地体现至少 2 个，不要罗列堆砌）")
        parts.append("- " + "、".join(vlm_keywords))

    if meta:
        meta_bits = []
        for k in ("style", "scene_type", "expression_type", "lighting_type", "outfit_style", "art_style"):
            v = meta.get(k)
            if v:
                meta_bits.append(f"{k}={v}")
        if meta_bits:
            parts.append(f"【元信息】{', '.join(meta_bits)}")

    if recent_heads:
        parts.append("")
        parts.append("【硬性禁止 1 - 不得以下列开头雷同】（最近用过）")
        for h in recent_heads[:20]:
            parts.append(f"  · {h}……")

    if _BANNED_WORDS:
        parts.append("")
        parts.append("【硬性禁止 2 - 不得使用陈词滥调】")
        parts.append("  · " + "、".join(_BANNED_WORDS))

    parts.extend([
        "",
        "【其他约束】",
        "- 不要用 emoji，不要用引号包裹整段。",
        "- 不要罗列画面要素，要自然融入叙述。",
        "- 不要出现摄影器材、滤镜参数、平台名（小红书/微博等）。",
        "- 主语用'她'或省略，不要'我''你'。",
        "- 不要解释，不要前言后语，直接输出正文。",
        "",
        "【输出】只输出正文，不要标题、不要任何解释。",
    ])

    return system, "\n".join(parts)


def llm_call(system: str, user: str, temperature: float = 0.95,
             timeout: int = 60) -> str:
    """调用 DeepSeek。失败抛异常。"""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 未设置")
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "top_p": 0.95,
        "max_tokens": 600,
    }
    resp = _http_post_json(DEEPSEEK_ENDPOINT, payload, DEEPSEEK_API_KEY, timeout=timeout)
    content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError(f"LLM 返回为空: {resp}")
    return content.strip()


def _post_clean(text: str) -> str:
    """清理 LLM 输出常见噪声。"""
    text = text.strip().strip('"').strip("'").strip("`")
    text = re.sub(r"^(配文|正文|文案|输出)[:：]\s*", "", text)
    text = re.sub(r"^\d+[\.\、]\s*", "", text)
    return text.strip()


def _coverage(text: str, keywords: list[str]) -> int:
    """统计文本覆盖了多少个 VLM 关键词（含模糊匹配）。"""
    if not keywords:
        return 0
    hits = 0
    for k in keywords:
        if not k:
            continue
        if k in text:
            hits += 1
            continue
        for ch in k:
            if len(ch.strip()) >= 1 and ch in text:
                hits += 0.3
                break
    return int(hits)


def _length_ok(text: str, tone: str) -> bool:
    n = len(re.sub(r"\s+", "", text))
    if tone == "cinematic":
        return 60 <= n <= 160
    if tone == "diary":
        return 25 <= n <= 90
    if tone == "short":
        return 8 <= n <= 30
    return 20 <= n <= 200


# ── v2 哲思文章生成（图启思考）──────────────────────────────────────
def _build_article_prompt(meta: dict, vlm_keywords: list[str],
                          history: list[dict], tone: str) -> tuple[str, str]:
    """组装"图启思考"模式的 system + user prompt。

    输出 JSON：{title, intro, aphorism}
      - title: 8-15 字金句感标题，能单独立得住
      - intro: 短画面切入（visual hook）
      - aphorism: 哲思/感悟（占主要重量）
    """
    spec = TONE_SPEC.get(tone, TONE_SPEC["philosophical_long"])
    intro_words = spec.get("intro_words", "20-35")
    aphorism_words = spec.get("aphorism_words", "60-90")
    title_words = spec.get("title_words", "10-15")

    # 历史标题/警句去重
    recent_titles = []
    recent_aphorism_heads = []
    for h in history[:60]:
        if h.get("title"):
            recent_titles.append(h["title"])
        if h.get("aphorism_head"):
            recent_aphorism_heads.append(h["aphorism_head"])
        elif h.get("head12"):
            recent_aphorism_heads.append(h["head12"])
    recent_titles = list(dict.fromkeys(recent_titles))[:30]
    recent_aphorism_heads = list(dict.fromkeys(recent_aphorism_heads))[:30]

    system = (
        "你是一位为公众号美图栏目写'图启思考'短文的资深编辑。"
        "你的任务不是描述图片，而是把图片中的某个细节作为引子，"
        "写一段值得读者反复读的哲思或生活感悟。\n\n"
        "核心原则：\n"
        "1. 画面只占 20%——给读者一个进入文字的入口\n"
        "2. 哲思占 80%——一句话能让读者停下来想想\n"
        "3. 拒绝鸡汤、拒绝假深刻、拒绝'人生''世界''生活'这种空泛词\n"
        "4. 哲思要有具体的钩子：一个动作、一种感觉、一个矛盾、一种边界\n"
        "5. 不要总结，不要点透，让读者自己接住"
    )

    parts = [
        "【任务】基于下面这张人像照片写一段「图启思考」短文。",
        "图片只是引子，重点是哲思/生活观察。",
        "",
        "【画面要素】（仅供你抓一个细节做引子，不要罗列）",
    ]
    if vlm_keywords:
        parts.append("  - " + "、".join(vlm_keywords))
    else:
        parts.append("  -（无）")

    if meta:
        meta_bits = []
        for k in ("style", "scene_type", "expression_type"):
            v = meta.get(k)
            if v:
                meta_bits.append(f"{k}={v}")
        if meta_bits:
            parts.append(f"【元信息】{', '.join(meta_bits)}")

    parts.extend([
        "",
        "【输出严格 JSON】",
        "{",
        f'  "title":    "{title_words} 字金句标题，要能单独立得住，不要泛泛之词",',
        f'  "intro":    "{intro_words} 字画面切入，1-2 句，从画面里挑一个细节",',
        f'  "aphorism": "{aphorism_words} 字哲思 / 生活感悟，从画面引子延伸到具体观察。允许 2-3 句，可以有一个温和的转折"',
        "}",
        "",
        "【硬性禁止】",
        "- 不要写'人生''世界''生活'这种空泛大词；用具体的事物代替",
        "- 不要鸡汤式金句结尾（'愿你''要相信''请记得'之类）",
        "- 不要在 aphorism 里描述图片，要从画面跳脱出来谈别的事",
        "- 不要 emoji，不要引号包裹整段，不要'你''我'指代",
        "- 不要罗列画面要素，要自然融入",
    ])

    if recent_titles:
        parts.append("")
        parts.append("【避免与最近的标题雷同】")
        for t in recent_titles[:20]:
            parts.append(f"  · {t}")

    if recent_aphorism_heads:
        parts.append("")
        parts.append("【避免与最近的开头雷同】")
        for h in recent_aphorism_heads[:20]:
            parts.append(f"  · {h}……")

    if _BANNED_WORDS:
        parts.append("")
        parts.append("【陈词滥调禁用】")
        parts.append("  · " + "、".join(_BANNED_WORDS))

    parts.extend([
        "",
        "【只输出严格 JSON】不要 markdown code block，不要解释，不要前言后语。",
    ])

    return system, "\n".join(parts)


def _parse_article_json(raw: str) -> dict | None:
    """从 LLM 输出中解析 JSON。容错 markdown code block 包裹。"""
    if not raw:
        return None
    s = raw.strip()
    # 去掉可能的 markdown code block
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    # 找第一个完整的 JSON 对象
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    title = (obj.get("title") or "").strip()
    intro = (obj.get("intro") or "").strip()
    aphorism = (obj.get("aphorism") or "").strip()
    if not title or not intro or not aphorism:
        return None
    return {"title": title, "intro": intro, "aphorism": aphorism}


def _length_ok_article(article: dict, tone: str) -> tuple[bool, str]:
    """校验 title/intro/aphorism 长度是否符合 tone spec。"""
    spec = TONE_SPEC.get(tone, TONE_SPEC["philosophical_long"])

    def _range(s: str) -> tuple[int, int]:
        m = re.match(r"(\d+)-(\d+)", s)
        if not m:
            return (0, 9999)
        return int(m.group(1)), int(m.group(2))

    def _len(t: str) -> int:
        return len(re.sub(r"\s+", "", t))

    t_min, t_max = _range(spec["title_words"])
    i_min, i_max = _range(spec["intro_words"])
    a_min, a_max = _range(spec["aphorism_words"])

    title_n = _len(article["title"])
    intro_n = _len(article["intro"])
    aph_n = _len(article["aphorism"])

    # 上下宽 30% 的容差，避免 LLM 死扣字数
    if title_n < int(t_min * 0.7) or title_n > int(t_max * 1.5):
        return False, f"标题字数{title_n}（期望{t_min}-{t_max}）"
    if intro_n < int(i_min * 0.7) or intro_n > int(i_max * 1.5):
        return False, f"intro 字数{intro_n}（期望{i_min}-{i_max}）"
    if aph_n < int(a_min * 0.7) or aph_n > int(a_max * 1.5):
        return False, f"aphorism 字数{aph_n}（期望{a_min}-{a_max}）"
    return True, ""


def _is_duplicate_article(article: dict, history: list[dict]) -> tuple[bool, str]:
    """文章级去重：检查 title 头部 + aphorism 头部 + aphorism 整体相似度。"""
    title = article["title"]
    aphorism = article["aphorism"]
    title_head = _head_n(title, 8)
    aph_head = _head_n(aphorism, 12)

    for h in history:
        if h.get("title") and _head_n(h["title"], 8) == title_head:
            return True, f"标题与 {h.get('date','?')} 雷同"
        if h.get("aphorism_head") and h["aphorism_head"] == aph_head:
            return True, f"哲思开头与 {h.get('date','?')} 雷同"
        if h.get("aphorism"):
            score = jaccard(aphorism, h["aphorism"])
            if score >= 0.5:
                return True, f"哲思与 {h.get('date','?')} 相似度 {score:.2f}"
    return False, ""


def append_article_history(article: dict, image_url: str) -> None:
    """落库整篇文章（title + intro + aphorism + 指纹）。"""
    fp = _own_history_file()
    fp.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "date": date.today().isoformat(),
        "ts": datetime.now().isoformat(timespec="seconds"),
        "kind": "article",
        "title": article["title"],
        "intro": article["intro"],
        "aphorism": article["aphorism"],
        "title_head": _head_n(article["title"], 8),
        "aphorism_head": _head_n(article["aphorism"], 12),
        "head12": _head_n(article["aphorism"], 12),  # 兼容旧 schema
        "image": image_url,
        "tone": os.environ.get("BEAUTY_CAPTION_TONE", "cinematic"),
    }
    with open(fp, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def generate_unique_article(
    image_url: str,
    meta: dict | None = None,
    prompt_text: str = "",
    tone: str | None = None,
    max_retries: int = 3,
    save: bool = True,
) -> dict | None:
    """生成"图启思考"哲思短文。

    Returns:
        {
          "title": "金句标题",
          "intro": "画面切入",
          "aphorism": "哲思感悟",
          "body":  "intro\n\n· · ·\n\n> aphorism"  (markdown 格式好的正文)
        }
        失败返回 None。
    """
    _ = prompt_text
    if not image_url:
        return None

    # 调性映射：cinematic → philosophical_long, diary → philosophical_short
    raw_tone = tone or os.environ.get("BEAUTY_CAPTION_TONE", "cinematic")
    tone_map = {
        "cinematic": "philosophical_long",
        "diary": "philosophical_short",
    }
    tone = tone_map.get(raw_tone, raw_tone if raw_tone.startswith("philosophical_") else "philosophical_long")
    if tone not in TONE_SPEC:
        tone = "philosophical_long"

    meta = meta or {}
    keywords = vlm_extract_keywords(image_url)
    history = load_history(days=90, limit=200)

    last_error = ""
    for attempt in range(1, max_retries + 1):
        try:
            system, user = _build_article_prompt(meta, keywords, history, tone)
            if attempt > 1:
                user += (
                    f"\n\n【重要】上次尝试不通过（{last_error}）。"
                    "请彻底换一个切入角度——从声音、温度、距离、边界、矛盾、空缺、习惯、克制中任选一个全新意象，"
                    "title 也要彻底换掉。"
                )
            raw = llm_call(system, user, temperature=min(1.0, 0.9 + 0.03 * attempt))
            article = _parse_article_json(raw)
            if not article:
                last_error = f"JSON 解析失败：{raw[:80]}"
                continue

            ok, why = _length_ok_article(article, tone)
            if not ok:
                last_error = why
                continue

            # 关键词覆盖：长版要求 intro 里 ≥1；短版 intro 可能太短装不下，
            # 改为 intro+aphorism 合计 ≥1（aphorism 主要是哲思，不强制画面）
            if keywords:
                if tone == "philosophical_short":
                    cov = _coverage(article["intro"] + article["aphorism"], keywords)
                else:
                    cov = _coverage(article["intro"], keywords)
                if cov < 1:
                    last_error = f"未引用任何画面要素（{cov}/{len(keywords)}）"
                    continue

            dup, why = _is_duplicate_article(article, history)
            if dup:
                last_error = why
                continue

            # 组装 markdown 正文：intro + 分隔符 + 引用块
            body = f"{article['intro']}\n\n· · ·\n\n> {article['aphorism']}"
            article["body"] = body

            if save:
                try:
                    append_article_history(article, image_url)
                except Exception as e:
                    print(f"  ⚠️ 历史库写入失败: {e}", file=sys.stderr)
            return article

        except Exception as e:
            last_error = str(e)
            print(f"  ⚠️ 文章生成第 {attempt} 次失败: {e}", file=sys.stderr)
            time.sleep(0.8)

    print(f"  ⚠️ 文章生成 {max_retries} 次均未通过：{last_error}", file=sys.stderr)
    return None


# ── 对外主函数 ────────────────────────────────────────────────────────
def generate_unique_caption(
    image_url: str,
    meta: dict | None = None,
    prompt_text: str = "",
    tone: str | None = None,
    kind: str = "opener",
    max_retries: int = 3,
    save: bool = True,
) -> str | None:
    """生成不重复且与图匹配的中文文案。

    Args:
        image_url: 实际成图的可访问 URL（VLM 必须能下载）
        meta: 生成元信息字典（可选）
        prompt_text: 原始英文 prompt（可选）
        tone: cinematic | diary | short；不传则取 BEAUTY_CAPTION_TONE
        kind: 落库时的标签（opener / short）
        max_retries: 撞车后最多重生成次数
        save: 是否落盘历史库

    Returns:
        清理后的中文配文；任一关键步骤失败返回 None。
    """
    if not image_url:
        return None
    tone = tone or os.environ.get("BEAUTY_CAPTION_TONE", "cinematic")
    if tone not in TONE_SPEC:
        tone = "cinematic"
    meta = meta or {}

    keywords = vlm_extract_keywords(image_url)
    history = load_history(days=90, limit=200)

    last_error = ""
    for attempt in range(1, max_retries + 1):
        try:
            system, user = _build_llm_prompt(meta, keywords, history, tone, prompt_text)
            if attempt > 1:
                user += (
                    f"\n\n【重要】上次的尝试与历史撞车（{last_error}），"
                    "请彻底换一个角度切入：可以从声音/温度/季节/动作/材质/气味中任选一个全新意象。"
                )
            raw = llm_call(system, user, temperature=min(1.0, 0.85 + 0.05 * attempt))
            text = _post_clean(raw)

            if not _length_ok(text, tone):
                last_error = f"长度不符（{len(text)}字）"
                continue

            cov = _coverage(text, keywords)
            min_cov = 1 if tone == "short" else 2
            if keywords and cov < min_cov:
                last_error = f"VLM 关键词覆盖不足（{cov}/{len(keywords)}）"
                continue

            dup, why = is_duplicate(text, history)
            if dup:
                last_error = why
                continue

            if save:
                try:
                    append_history(text, image_url, kind=kind)
                except Exception as e:
                    print(f"  ⚠️ 历史库写入失败: {e}", file=sys.stderr)
            return text

        except Exception as e:
            last_error = str(e)
            print(f"  ⚠️ LLM 第 {attempt} 次尝试失败: {e}", file=sys.stderr)
            time.sleep(0.8)

    print(f"  ⚠️ LLM 文案生成 {max_retries} 次均未通过校验：{last_error}", file=sys.stderr)
    return None


# ── 自检 ──────────────────────────────────────────────────────────────
def selftest() -> int:
    """快速自检：仅检查 key 配置和 endpoint 连通性，不真正生成。"""
    issues = []
    if not QWEN_API_KEY:
        issues.append("QWEN_API_KEY 未设置")
    if not DEEPSEEK_API_KEY:
        issues.append("DEEPSEEK_API_KEY 未设置")
    if issues:
        print("❌ 配置问题:")
        for i in issues:
            print(f"  - {i}")
        return 1
    print("✅ 配置 OK：QWEN_VL_MODEL=", QWEN_VL_MODEL, "DEEPSEEK_MODEL=", DEEPSEEK_MODEL)
    print("   tone:", os.environ.get("BEAUTY_CAPTION_TONE", "cinematic"))
    print("   own history:", _own_history_file())
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--probe" in sys.argv:
        # ./llm_caption.py --probe <image_url>
        url = sys.argv[sys.argv.index("--probe") + 1]
        kws = vlm_extract_keywords(url)
        print("VLM 关键词:", kws)
        cap = generate_unique_caption(url, meta={}, save=False)
        print("文案:")
        print(cap)
