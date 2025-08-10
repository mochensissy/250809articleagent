from __future__ import annotations

import os
import json
from typing import List, Dict, Any

import requests


PPLX_BASE_URL = os.environ.get("TEXT_LLM_BASE_URL", "https://api.perplexity.ai")
PPLX_CHAT_COMPLETIONS = f"{PPLX_BASE_URL.rstrip('/')}/chat/completions"


class PerplexityError(RuntimeError):
    pass


def _headers() -> Dict[str, str]:
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise PerplexityError("缺少 PERPLEXITY_API_KEY 环境变量")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def chat(
    messages: List[Dict[str, str]], *, model: str = "sonar-medium-online", temperature: float = 0.2, max_tokens: int = 2048
) -> str:
    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    resp = requests.post(PPLX_CHAT_COMPLETIONS, headers=_headers(), json=payload, timeout=60)
    if resp.status_code >= 400:
        raise PerplexityError(f"Perplexity API 错误: {resp.status_code} {resp.text}")
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise PerplexityError(f"解析 Perplexity 响应失败: {exc}; 原始: {data}")


def chat_json(system_prompt: str, user_prompt: str, *, model: str = "sonar-medium-online", temperature: float = 0.2) -> Any:
    content = chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=model,
        temperature=temperature,
    )
    # 试图解析为 JSON（容错处理：截取首尾 ```json 包裹等）
    text = content.strip()
    if text.startswith("```json") or text.startswith("```"):
        # 去掉三引号包装
        text = text.strip("`\n ")
        if text.lower().startswith("json\n"):
            text = text[5:]
    try:
        return json.loads(text)
    except Exception:
        # 如果无法直接解析，尝试从文本中找到第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise PerplexityError("Perplexity 响应不是有效JSON，且无法纠正")


