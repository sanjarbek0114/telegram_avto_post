import json
import os
import re
from pathlib import Path

from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parent.parent
_client = None


def env(name, default=None, required=True):
    val = os.getenv(name, default)
    if required and not val:
        raise RuntimeError(f"{name} muhit o'zgaruvchisi berilmagan")
    return val


def gemini():
    global _client
    if _client is None:
        _client = genai.Client(api_key=env("GEMINI_API_KEY"))
    return _client


def ask(prompt, search=False, json_out=False):
    """Matn modeliga so'rov. search=True bo'lsa Google Search bilan ishlaydi."""
    cfg = {}
    if search:
        cfg["tools"] = [types.Tool(google_search=types.GoogleSearch())]
    elif json_out:
        cfg["response_mime_type"] = "application/json"
    resp = gemini().models.generate_content(
        model=env("TEXT_MODEL", "gemini-2.5-flash"),
        contents=prompt,
        config=types.GenerateContentConfig(**cfg),
    )
    text = resp.text or ""
    return parse_json(text) if json_out else text


def parse_json(text):
    m = re.search(r"\{.*\}|\[.*\]", text, re.S)
    if not m:
        raise ValueError(f"JSON topilmadi: {text[:300]}")
    return json.loads(m.group(0))


def load_rubric():
    return json.loads((ROOT / "config/rubric.json").read_text(encoding="utf-8"))


def load_style():
    return (ROOT / "config/style.md").read_text(encoding="utf-8")


def load_history():
    p = ROOT / "state/history.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"posts": []}


def save_history(h):
    (ROOT / "state/history.json").write_text(
        json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8"
    )
