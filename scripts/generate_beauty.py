#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美女生成 V5.0 - 智能随机 Prompt 系统
- 从丰富的元素库中随机组合
- 确保每次生成都有新鲜感
- 严格东方美女风格
- 基于 Civitai/Stable Diffusion 社区最佳实践
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

    log_file = LOGS_DIR / f"v5-{datetime.now().strftime('%Y%m%d')}.log"
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
    """内置默认元素库"""
    return {
        "base_quality": [
            "RAW photo, masterpiece, best quality, ultra detailed, 8K UHD, DSLR",
            "masterpiece, best quality, ultra realistic, 8k resolution, photorealistic"
        ],
        "asian_identity": [
            "East Asian Chinese young woman, Asian facial features, Asian beauty",
            "beautiful Chinese woman, delicate Asian features, oriental beauty"
        ],
        "face_types": {
            "甜美系": ["sweet innocent face, round cheeks, bright sparkling eyes"],
            "清纯系": ["pure innocent face, clear bright eyes, natural beauty"],
            "御姐系": ["mature elegant face, sharp jawline, sophisticated features"]
        },
        "hair_styles": [
            "long silky black hair flowing in wind, glossy healthy shine",
            "shoulder-length dark brown hair with subtle waves"
        ],
        "skin_textures": [
            "flawless porcelain skin, visible pores, natural skin texture, healthy glow"
        ],
        "outfits": {
            "优雅": ["elegant silk evening gown, flowing fabric"],
            "清新": ["white cotton sundress with floral embroidery"]
        },
        "poses": {
            "特写": ["extreme close-up portrait, looking directly at camera"],
            "半身": ["upper body shot, hands near face, graceful gesture"],
            "全身": ["full body standing pose, natural S-curve"]
        },
        "expressions": {
            "微笑": ["gentle natural smile, eyes crinkled with joy"],
            "性感": ["sultry gaze, lips slightly parted"]
        },
        "scenes": {
            "自然": ["cherry blossom garden, pink petals falling"],
            "城市": ["Tokyo neon-lit street at night, urban glamour"],
            "室内": ["sunlit bedroom, morning light through sheer curtains"]
        },
        "lighting": {
            "自然光": ["golden hour sunlight, warm orange glow, magical atmosphere"],
            "影棚": ["professional studio softbox, clean even lighting"]
        },
        "camera_settings": [
            "85mm f/1.2 lens, ultra shallow depth of field, creamy bokeh"
        ],
        "enhancement_keywords": [
            "award-winning photo, professional photography, magazine cover quality"
        ],
        "negative_prompts": {
            "standard": "(deformed, bad anatomy, disfigured:1.3), ugly, duplicate, morbid",
            "asian_focused": "Western face, Caucasian features, European features, blonde hair, blue eyes",
            "quality": "low quality, worst quality, jpeg artifacts, blurry"
        }
    }


class SmartPromptGenerator:
    """智能 Prompt 生成器"""

    def __init__(self, library: dict):
        self.library = library
        # 使用时间戳确保每次运行都不同
        self.seed = int(time.time() * 1000) % 1000000
        random.seed(self.seed)
        log(f"🎲 随机种子: {self.seed}")

    def pick_random(self, items: list, count: int = 1) -> list:
        """从列表中随机选择"""
        if not items:
            return []
        count = min(count, len(items))
        return random.sample(items, count)

    def pick_one(self, items: list) -> str:
        """随机选择一个"""
        if not items:
            return ""
        return random.choice(items)

    def pick_from_dict(self, d: dict, key: str = None) -> tuple:
        """从字典中随机选择，返回 (key, value)"""
        if not d:
            return ("", "")
        if key and key in d:
            values = d[key]
        else:
            key = random.choice(list(d.keys()))
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

        return {
            "style": face_key,
            "face": face_desc,
            "hair": hair,
            "skin": skin
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

        # 8. 增强关键词
        enhancements = self.pick_random(self.library.get("enhancement_keywords", []), 2)
        parts.extend(enhancements)

        # 9. 自定义元素
        if custom_elements:
            parts.extend(custom_elements)

        # 组合并清理
        prompt = ", ".join(parts)
        while "  " in prompt:
            prompt = prompt.replace("  ", " ")
        prompt = prompt.replace(", ,", ",").strip()

        return prompt

    def get_negative_prompt(self) -> str:
        """获取负面提示词"""
        neg = self.library.get("negative_prompts", {})
        parts = []

        if neg.get("standard"):
            parts.append(neg["standard"])
        if neg.get("asian_focused"):
            parts.append(neg["asian_focused"])
        if neg.get("quality"):
            parts.append(neg["quality"])

        return ", ".join(parts)


def generate_image(prompt: str, negative_prompt: str, reference_url: str = None) -> dict:
    """调用 API 生成图片"""

    payload = {
        "model": API_MODEL,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "size": "2k",
        "response_format": "url",
        "watermark": False
    }

    if reference_url:
        payload["image"] = reference_url
        log("📎 使用图生图模式")

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

    print("=" * 70)
    print("🎨 美女生成 V5.0 - 智能随机 Prompt 系统")
    print("=" * 70)

    # 加载元素库
    library = load_prompt_library()
    generator = SmartPromptGenerator(library)

    # 生成统一的人物特征（保持一致性）
    character = generator.generate_character(style)

    print(f"\n📅 日期: {date.today()}")
    print(f"\n👤 人物特征:")
    print(f"   风格: {character.get('style', '随机')}")
    print(f"   脸型: {character.get('face', '')[:50]}...")
    print(f"   发型: {character.get('hair', '')[:50]}...")

    # 不同姿势类型
    pose_types = ["特写", "半身", "全身", "动态"]

    images = []
    reference_url = None
    negative_prompt = generator.get_negative_prompt()

    print(f"\n🚫 Negative Prompt: {negative_prompt[:80]}...")

    print("\n" + "=" * 70)
    print(f"🎨 开始生成 {count} 张图片...")
    print("=" * 70)

    for i in range(count):
        # 每张图使用不同的场景、穿搭、姿势
        scene = generator.generate_scene(scene_type)
        styling = generator.generate_styling(outfit_style)
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

        # 第一张文生图，后续图生图
        use_reference = (i > 0) and (reference_url is not None)

        result = generate_image(
            prompt,
            negative_prompt,
            reference_url if use_reference else None
        )

        if result["success"]:
            url = result["url"]
            if i == 0:
                reference_url = url

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

    print("\n📷 姿势类型:")
    for key in library.get("poses", {}).keys():
        print(f"   • {key}")


def main():
    parser = argparse.ArgumentParser(
        description="美女生成 V5.0 - 智能随机 Prompt 系统"
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

        print(f"\n【Negative Prompt】")
        print(generator.get_negative_prompt())

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
