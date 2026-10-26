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


_models = {}
_SKIP = ("lite", "live", "tts", "audio", "embedding", "preview-tts", "thinking", "robotics", "computer")


def _version(name):
    nums = re.findall(r"\d+(?:\.\d+)?", name.split("/")[-1])
    return [float(n) for n in nums] or [0.0]


def model(kind):
    """Matn yoki rasm modelini tanlaydi: env da berilgan bo'lsa o'sha, aks holda eng yangi Flash."""
    if kind in _models:
        return _models[kind]
    override = os.getenv("TEXT_MODEL" if kind == "text" else "IMAGE_MODEL")
    if override:
        _models[kind] = override
        return override
    names = []
    for m in gemini().models.list():
        n = m.name.split("/")[-1]
        actions = getattr(m, "supported_actions", None) or []
        if actions and "generateContent" not in actions:
            continue
        if "flash" not in n or any(x in n for x in _SKIP):
            continue
        is_image = "image" in n
        if (kind == "image") == is_image:
            names.append(n)
    if not names:
        raise RuntimeError(f"Mos Gemini {kind} modeli topilmadi")
    stable = [n for n in names if "preview" not in n and "exp" not in n] or names
    _models[kind] = max(stable, key=_version)
    print(f"Gemini {kind} modeli: {_models[kind]}", flush=True)
    return _models[kind]


def ask(prompt, search=False, json_out=False):
    """Matn modeliga so'rov. search=True bo'lsa Google Search bilan ishlaydi."""
    cfg = {}
    if search:
        cfg["tools"] = [types.Tool(google_search=types.GoogleSearch())]
    elif json_out:
        cfg["response_mime_type"] = "application/json"
    resp = gemini().models.generate_content(
        model=model("text"),
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
    """Stil qoidalari + namuna sifatida kontent-plandagi 2 ta post."""
    rules = (ROOT / "config/style.md").read_text(encoding="utf-8")
    samples = "\n\n---\n\n".join(p["text"] for p in load_plan()[:2])
    return f"{rules}\n\nNAMUNA POSTLAR:\n{samples}"


def load_history():
    p = ROOT / "state/history.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"posts": []}


def save_history(h):
    (ROOT / "state/history.json").write_text(
        json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_settings():
    return json.loads((ROOT / "config/settings.json").read_text(encoding="utf-8"))


def load_plan():
    """config/content_plan.md ni postlarga ajratadi: [{"n": 1, "theme": "...", "text": "..."}]."""
    raw = (ROOT / "config/content_plan.md").read_text(encoding="utf-8")
    parts = re.split(r"^📌 (\d+)-POST: *(.+)$", raw, flags=re.M)
    posts = []
    for i in range(1, len(parts), 3):
        posts.append({"n": int(parts[i]), "theme": parts[i + 1].strip(), "text": parts[i + 2].strip()})
    if not posts:
        raise RuntimeError("content_plan.md da post topilmadi")
    return posts
