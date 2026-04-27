#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手动提示词库读写。文件 schema:

{
  "version": "1.0",
  "prompts": [
    {"id": int, "prompt": str, "caption": str, "tags": str,
     "title": str, "image_url": str, "created_at": "YYYY-MM-DD HH:MM:SS"}
  ]
}
"""

import json
import re
from datetime import datetime
from pathlib import Path


MANUAL_PROMPT_LOG_PREFIX_RE = re.compile(
    r"^\s*\[\d{4}-\d{2}-\d{2}\s+[0-9:]+\]\s+\[(?:INFO|WARN|ERROR)\]\s+随机种子:\s*\d+\s*"
)


def clean_manual_prompt(prompt: str) -> str:
    """移除误复制进手动 prompt 的本地日志前缀。"""
    if not prompt:
        return ""
    return MANUAL_PROMPT_LOG_PREFIX_RE.sub("", str(prompt).strip(), count=1).strip()


def load_manual_prompts(prompts_file: Path) -> dict:
    if prompts_file.exists():
        with open(prompts_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": "1.0", "prompts": []}


def save_manual_prompt(
    prompts_file: Path,
    prompt: str,
    caption: str = "",
    tags: str = "",
    title: str = "",
    image_url: str = "",
) -> int:
    """保存到库，返回新条目的 ID。"""
    prompt = clean_manual_prompt(prompt)
    data = load_manual_prompts(prompts_file)
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
    with open(prompts_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  📚 提示词已保存到库（ID: {next_id}）")
    return next_id


def list_manual_prompts(prompts_file: Path):
    data = load_manual_prompts(prompts_file)
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


def get_manual_prompt(prompts_file: Path, prompt_id: int) -> dict:
    data = load_manual_prompts(prompts_file)
    for p in data.get("prompts", []):
        if p.get("id") == prompt_id:
            return p
    return {}
