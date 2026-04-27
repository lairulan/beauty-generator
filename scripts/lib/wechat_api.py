#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""微信公众号 API 封装：SSL 证书检查 + 请求发送。"""

import json
import os
import ssl
import urllib.error
import urllib.request


API_BASE = "https://wx.limyai.com/api/openapi"


def get_api_key() -> str:
    return os.environ.get("WECHAT_API_KEY", "")


def _build_ssl_context(verify: bool = True) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _is_cert_error(exc: Exception) -> bool:
    if isinstance(exc, ssl.SSLCertVerificationError):
        return True
    reason = getattr(exc, "reason", None)
    if isinstance(reason, ssl.SSLCertVerificationError):
        return True
    text = str(exc).lower()
    return "certificate verify failed" in text or "certificate_verify_failed" in text


def _allow_insecure_ssl_fallback() -> bool:
    """默认关闭，仅在 WECHAT_API_ALLOW_INSECURE_SSL=1 时回退。"""
    value = os.environ.get("WECHAT_API_ALLOW_INSECURE_SSL", "0").strip().lower()
    return value in {"1", "true", "yes"}


def _open_json_request(req, timeout: int, ssl_context):
    with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
        return json.loads(response.read().decode("utf-8"))


def make_request(endpoint: str, data: dict = None, timeout: int = 60) -> dict:
    """POST 微信公众号 API。SSL 证书异常时按需回退。"""
    api_key = get_api_key()
    if not api_key:
        return {"success": False, "error": "环境变量 WECHAT_API_KEY 未设置"}

    url = f"{API_BASE}/{endpoint}"
    payload = json.dumps(data or {}, ensure_ascii=False).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            return _open_json_request(req, timeout=timeout, ssl_context=_build_ssl_context())
        except (urllib.error.URLError, ssl.SSLCertVerificationError) as e:
            if _is_cert_error(e):
                if not _allow_insecure_ssl_fallback():
                    return {
                        "success": False,
                        "error": "SSL 证书校验失败，且已禁用不安全回退（WECHAT_API_ALLOW_INSECURE_SSL=0）",
                    }
                print("⚠️ 微信发布接口 SSL 证书校验失败，已回退到不校验证书连接。建议尽快修复服务端证书。")
                return _open_json_request(req, timeout=timeout, ssl_context=_build_ssl_context(verify=False))
            raise
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"success": False, "error": f"HTTP {e.code}: {body[:200]}"}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"连接失败: {e.reason}"}
    except json.JSONDecodeError:
        return {"success": False, "error": "响应 JSON 解析失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def publish_to_wechat(
    appid: str,
    title: str,
    content: str,
    images: list,
    article_type: str = "newspic",
    tags: str = "#每日美女 #写真 #人像摄影 #今日心动",
) -> dict:
    """发布到公众号草稿箱。

    images: List[(url, caption)]
    """
    if article_type == "newspic":
        content_lines = []
        if content.strip():
            content_lines.append(content.strip())
            content_lines.append("")
        for img_url, caption in images:
            content_lines.append(f"![]({img_url})")
            if caption:
                content_lines.append(f"\n{caption}\n")
        content_lines.append(f"\n{tags}")
        content_md = "\n".join(content_lines)
    else:
        content_md = content

    data = {
        "wechatAppid": appid,
        "title": title,
        "content": content_md,
        "contentFormat": "markdown",
        "articleType": article_type,
    }
    if article_type == "newspic" and images:
        data["mainImages"] = [img_url for img_url, _ in images]

    return make_request("wechat-publish", data)
