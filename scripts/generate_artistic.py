#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
艺术写真生成 V1.0
使用 OpenRouter (Gemini) 生成高质量真人艺术写真
- 每日生成一张精品写真
- 更性感、更吸引眼球
- 真人摄影风格
"""

import argparse
import json
import os
import random
import sys
import time
import tempfile
import subprocess
import urllib.request
import urllib.error
import ssl
from datetime import date, datetime
from pathlib import Path

# 脚本目录
SCRIPT_DIR = Path(__file__).parent.absolute()
SKILL_DIR = SCRIPT_DIR.parent
LOGS_DIR = SKILL_DIR / "logs"

# API 配置
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_IMAGE_MODEL = "google/gemini-3-pro-image-preview-20251120"
IMGBB_API_URL = "https://api.imgbb.com/1/upload"

# 创建 SSL 上下文
ssl_context = ssl._create_unverified_context()

# 确保目录存在
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str, level: str = "INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [{level}] {message}"
    print(log_msg)

    log_file = LOGS_DIR / f"artistic-{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")


# ========== Prompt 元素库 ==========

# 人物风格
PERSON_STYLES = [
    "stunning Asian model with perfect features",
    "gorgeous Chinese beauty with elegant features",
    "breathtaking Japanese model with delicate features",
    "beautiful Korean model with flawless skin",
    "captivating Asian woman with mesmerizing eyes"
]

# 性感元素
SEXY_ELEMENTS = [
    "sultry gaze, seductive expression, alluring pose",
    "sensual look, bedroom eyes, provocative stance",
    "smoldering eyes, pouty lips, confident sexy pose",
    "intense gaze, slightly parted lips, feminine curves",
    "captivating stare, elegant sensuality, graceful pose"
]

# 服装风格
OUTFIT_STYLES = [
    "elegant silk evening gown with deep neckline, form-fitting silhouette",
    "luxurious red dress with high slit, showing beautiful legs",
    "sophisticated black cocktail dress, off-shoulder design",
    "glamorous sequin mini dress, showcasing perfect figure",
    "chic bodycon dress in jewel tones, highlighting curves",
    "stunning backless gown, elegant and alluring",
    "stylish crop top with high-waisted pants, showing midriff",
    "classic little black dress with plunging back"
]

# 场景设置
SCENE_SETTINGS = [
    "luxury penthouse with city night view, ambient lighting",
    "high-end hotel suite, soft romantic lighting through sheer curtains",
    "exclusive rooftop bar at sunset, golden hour glow",
    "elegant private yacht at dusk, ocean breeze",
    "upscale lounge with velvet furnishings, moody lighting",
    "sophisticated wine cellar, warm candlelight atmosphere",
    "modern art gallery, dramatic spotlight illumination",
    "boutique hotel balcony, twinkling city lights below"
]

# 光影效果
LIGHTING_STYLES = [
    "dramatic Rembrandt lighting, deep shadows and highlights",
    "soft diffused golden hour light, warm skin tones",
    "cinematic low-key lighting, mysterious atmosphere",
    "glamorous beauty lighting, flawless skin illumination",
    "romantic candlelight ambiance, warm intimate glow",
    "professional studio strobe, magazine cover quality",
    "natural window light with subtle rim lighting"
]

# 摄影技术
PHOTOGRAPHY_TECH = [
    "shot on Sony A7R IV, 85mm f/1.4 lens, shallow depth of field",
    "captured with Canon EOS R5, 70-200mm f/2.8, bokeh background",
    "professional fashion photography, medium format camera quality",
    "editorial portrait lighting, Vogue magazine aesthetic",
    "high-end commercial photography, perfect exposure"
]

# 质量增强
QUALITY_BOOST = [
    "8K UHD, ultra detailed, masterpiece quality",
    "photorealistic, award-winning photography",
    "magazine cover quality, flawless retouching",
    "professional model photography, perfect composition",
    "high fashion editorial, stunning visual impact"
]


def build_prompt() -> str:
    """构建高质量艺术写真 Prompt"""

    parts = [
        # 质量基础
        random.choice(QUALITY_BOOST),

        # 人物
        random.choice(PERSON_STYLES),

        # 性感元素
        random.choice(SEXY_ELEMENTS),

        # 服装
        f"wearing {random.choice(OUTFIT_STYLES)}",

        # 场景
        random.choice(SCENE_SETTINGS),

        # 光影
        random.choice(LIGHTING_STYLES),

        # 摄影技术
        random.choice(PHOTOGRAPHY_TECH),

        # 额外强调
        "realistic skin texture, natural beauty, elegant and sophisticated",
        "eye-catching, visually stunning, professional model shoot"
    ]

    return ", ".join(parts)


def upload_to_imgbb(image_base64: str, retry: int = 3, retry_delay: int = 2) -> dict:
    """上传图片到 imgbb"""
    api_key = os.environ.get("IMGBB_API_KEY")
    if not api_key:
        return {"success": False, "error": "未设置 IMGBB_API_KEY"}

    last_error = None

    for attempt in range(retry):
        if attempt > 0:
            log(f"上传重试第 {attempt}/{retry-1} 次...")
            time.sleep(retry_delay)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(image_base64)
            image_file = f.name

        try:
            cmd = [
                "curl", "-s", "--max-time", "90",
                "-X", "POST",
                f"{IMGBB_API_URL}?key={api_key}",
                "-F", f"image=<{image_file}"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            response = json.loads(result.stdout)

            if response.get("success"):
                return {
                    "success": True,
                    "url": response["data"]["url"],
                    "display_url": response["data"]["display_url"]
                }
            else:
                last_error = {
                    "success": False,
                    "error": response.get("error", {}).get("message", "上传失败")
                }

        except Exception as e:
            last_error = {"success": False, "error": str(e)}
        finally:
            if os.path.exists(image_file):
                os.unlink(image_file)

    return last_error if last_error else {"success": False, "error": "上传失败"}


def generate_image_openrouter(prompt: str, retry: int = 3, retry_delay: int = 5) -> dict:
    """使用 OpenRouter (Gemini) 生成图片"""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return {"success": False, "error": "未设置 OPENROUTER_API_KEY"}

    last_error = None

    for attempt in range(retry):
        if attempt > 0:
            log(f"OpenRouter 重试第 {attempt}/{retry-1} 次...")
            time.sleep(retry_delay)

        payload = {
            "model": OPENROUTER_IMAGE_MODEL,
            "messages": [{"role": "user", "content": f"Generate an image: {prompt}"}],
            "modalities": ["image", "text"],
            "max_tokens": 4096
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                OPENROUTER_API_URL,
                data=data,
                headers={
                    'Authorization': f"Bearer {api_key}",
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://github.com/lairulan/beauty-generator',
                    'X-Title': 'Beauty Generator'
                }
            )

            with urllib.request.urlopen(req, timeout=180, context=ssl_context) as response:
                result = json.loads(response.read().decode('utf-8'))

            # 提取图片
            choices = result.get('choices', [])
            if choices:
                msg = choices[0].get('message', {})
                content = msg.get('content', [])

                # 处理多种响应格式
                image_url = None

                # 格式1: images 数组
                images = msg.get('images', [])
                if images:
                    img = images[0]
                    if isinstance(img, dict):
                        image_url = img.get('image_url', {})
                        if isinstance(image_url, dict):
                            image_url = image_url.get('url', '')
                    else:
                        image_url = str(img)

                # 格式2: content 中包含图片
                if not image_url and isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            if item.get('type') == 'image':
                                image_url = item.get('image_url', {})
                                if isinstance(image_url, dict):
                                    image_url = image_url.get('url', '')
                                break

                if image_url:
                    # 如果是 base64，需要上传到图床
                    if image_url.startswith('data:image'):
                        log("图片生成成功，正在上传到图床...")
                        base64_data = image_url.split(',')[1] if ',' in image_url else image_url
                        upload_result = upload_to_imgbb(base64_data, retry=retry, retry_delay=retry_delay)
                        if upload_result.get('success'):
                            return {
                                "success": True,
                                "url": upload_result['url'],
                                "display_url": upload_result.get('display_url', upload_result['url']),
                                "attempts": attempt + 1
                            }
                        else:
                            last_error = upload_result
                            continue
                    else:
                        return {
                            "success": True,
                            "url": image_url,
                            "attempts": attempt + 1
                        }

            last_error = {
                "success": False,
                "error": "未能从响应中提取图片",
                "attempt": attempt + 1
            }
            log(f"未提取到图片: {json.dumps(result, ensure_ascii=False)[:500]}", "WARN")

        except urllib.error.HTTPError as e:
            # 捕获 HTTP 错误并读取响应体
            error_body = ""
            try:
                error_body = e.read().decode('utf-8')
            except:
                pass
            last_error = {"success": False, "error": f"HTTP {e.code}: {error_body[:500]}", "attempt": attempt + 1}
            log(f"HTTP错误 {e.code}: {error_body[:500]}", "ERROR")
        except urllib.error.URLError as e:
            last_error = {"success": False, "error": f"网络错误: {str(e)}", "attempt": attempt + 1}
            log(f"网络错误: {e}", "ERROR")
        except Exception as e:
            last_error = {"success": False, "error": str(e), "attempt": attempt + 1}
            log(f"生成错误: {e}", "ERROR")

    return last_error if last_error else {"success": False, "error": "图片生成失败"}


def main():
    parser = argparse.ArgumentParser(description="艺术写真生成 - 使用 OpenRouter (Gemini)")
    parser.add_argument("--count", "-c", type=int, default=1, help="生成数量 (默认: 1)")
    parser.add_argument("--preview", "-p", action="store_true", help="只预览 Prompt，不生成图片")
    parser.add_argument("--retry", type=int, default=3, help="失败重试次数")

    args = parser.parse_args()

    print("=" * 70)
    print("🎨 艺术写真生成 V1.0 - OpenRouter (Gemini)")
    print("=" * 70)
    print(f"📅 日期: {date.today()}")
    print(f"📸 生成数量: {args.count}")
    print("=" * 70)

    images = []

    for i in range(args.count):
        prompt = build_prompt()

        print(f"\n📸 图片 {i+1}/{args.count}")
        print(f"   Prompt: {prompt[:150]}...")

        if args.preview:
            print(f"\n【完整 Prompt】\n{prompt}")
            continue

        log(f"开始生成图片 {i+1}/{args.count}")
        result = generate_image_openrouter(prompt, retry=args.retry)

        if result["success"]:
            url = result["url"]
            images.append(url)
            print(f"   ✅ 成功!")
            print(f"   🔗 {url}")
            log(f"图片 {i+1} 生成成功: {url}")
        else:
            print(f"   ❌ 失败: {result.get('error')}")
            log(f"图片 {i+1} 生成失败: {result.get('error')}", "ERROR")

        if i < args.count - 1:
            time.sleep(3)

    if args.preview:
        return 0

    print("\n" + "=" * 70)
    print(f"✅ 生成完成: {len(images)}/{args.count}")
    print("=" * 70)

    if images:
        print("\n🖼️ 生成的图片:")
        for i, url in enumerate(images, 1):
            print(f"  {i}. {url}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
