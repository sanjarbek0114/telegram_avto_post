import json
import os
import re
import time
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
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
        _client = genai.Client(
            api_key=env("GEMINI_API_KEY"),
            http_options=types.HttpOptions(timeout=180_000, retry_options=types.HttpRetryOptions(attempts=1)),
        )
    return _client


_models = {}
_SKIP = ("lite", "live", "tts", "audio", "embedding", "preview-tts", "thinking", "robotics", "computer")


def _version(name):
    nums = re.findall(r"\d+(?:\.\d+)?", name.split("/")[-1])
    return [float(n) for n in nums] or [0.0]


def models(kind):
    """Matn yoki rasm modellari ro'yxati: env da berilgan bo'lsa birinchi o'sha, keyin eng yangi Flash'lar."""
    if kind in _models:
        return _models[kind]
    names = []
    for m in gemini().models.list():
        n = m.name.split("/")[-1]
        actions = getattr(m, "supported_actions", None) or []
        if actions and "generateContent" not in actions:
            continue
        if "flash" not in n or any(x in n for x in _SKIP):
            continue
        if (kind == "image") == ("image" in n):
            names.append(n)
    stable = sorted((n for n in names if "preview" not in n and "exp" not in n), key=_version, reverse=True)
    preview = sorted((n for n in names if n not in stable), key=_version, reverse=True)
    override = os.getenv("TEXT_MODEL" if kind == "text" else "IMAGE_MODEL")
    order = ([override] if override else []) + stable[:2] + preview[:1]
    _models[kind] = list(dict.fromkeys(order))
    if not _models[kind]:
        raise RuntimeError(f"Mos Gemini {kind} modeli topilmadi")
    print(f"Gemini {kind} modellari: {_models[kind]}", flush=True)
    return _models[kind]


RETRY_CODES = (429, 500, 502, 503, 504)


def generate(kind, contents, config):
    """generate_content: band bo'lsa kutib qayta urinadi, keyin keyingi modelga o'tadi."""
    last = None
    for name in models(kind):
        for attempt, wait in enumerate((0, 15, 45, 90)):
            if wait:
                print(f"{name} band, {wait} s kutib qayta urinish ({attempt + 1}/4)", flush=True)
                time.sleep(wait)
            try:
                t0 = time.time()
                print(f"  -> {name} ({kind})", flush=True)
                resp = gemini().models.generate_content(model=name, contents=contents, config=config)
                print(f"  <- {name}: {time.time() - t0:.0f} s", flush=True)
                return resp
            except genai_errors.APIError as e:
                last = e
                print(f"  !! {name}: {e.code} {str(e)[:150]}", flush=True)
                if e.code == 404:
                    break  # bu model yopilgan, keyingisiga o'tamiz
                if e.code not in RETRY_CODES:
                    raise
    raise last


def ask(prompt, search=False, json_out=False):
    """Matn modeliga so'rov. search=True bo'lsa Google Search bilan ishlaydi."""
    cfg = {}
    if search:
        cfg["tools"] = [types.Tool(google_search=types.GoogleSearch())]
    elif json_out:
        cfg["response_mime_type"] = "application/json"
    resp = generate("text", prompt, types.GenerateContentConfig(**cfg))
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
