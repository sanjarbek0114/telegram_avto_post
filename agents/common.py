import json
import os
import re
import time
from pathlib import Path

import httpx
import requests
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

ROOT = Path(__file__).resolve().parent.parent
_client = None


def env(name, default=None, required=True):
    val = os.getenv(name, default)
    if isinstance(val, str):
        val = val.strip()  # Secrets'ga nusxa olinganda bo'sh joy/yangi qator qo'shilib qolishi mumkin
    if required and not val:
        raise RuntimeError(f"{name} muhit o'zgaruvchisi berilmagan")
    return val


def gemini():
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=env("GEMINI_API_KEY"),
            http_options=types.HttpOptions(timeout=90_000, retry_options=types.HttpRetryOptions(attempts=1)),
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
GEMINI_BUDGET = int(os.getenv("GEMINI_BUDGET_SECONDS", "240"))


def generate(kind, contents, config):
    """generate_content: band bo'lsa kutib qayta urinadi, keyin keyingi modelga o'tadi."""
    last = None
    start = time.time()
    for name in models(kind):
        for attempt, wait in enumerate((0, 20, 60)):
            if last is not None and time.time() - start + wait > GEMINI_BUDGET:
                raise last  # Gemini juda band: zaxiraga o'tish uchun vaqtni tejaymiz
            if wait:
                print(f"{name} band, {wait} s kutib qayta urinish ({attempt + 1}/3)", flush=True)
                time.sleep(wait)
            try:
                t0 = time.time()
                print(f"  -> {name} ({kind})", flush=True)
                resp = gemini().models.generate_content(model=name, contents=contents, config=config)
                print(f"  <- {name}: {time.time() - t0:.0f} s", flush=True)
                return resp
            except (genai_errors.APIError, httpx.TimeoutException) as e:
                last = e
                code = getattr(e, "code", 504)  # mijoz tomonidagi timeout ham 504 deb hisoblanadi
                print(f"  !! {name}: {code} {str(e)[:150]}", flush=True)
                if code in (404, 504) or (code == 429 and "quota" in str(e).lower()):
                    break  # model yopilgan, javob bermayapti yoki kvota tugagan: keyingisiga o'tamiz
                if code not in RETRY_CODES:
                    raise
    raise last


def ask(prompt, search=False, json_out=False):
    """Matn modeliga so'rov. search=True bo'lsa Google Search bilan ishlaydi."""
    cfg = {}
    if search:
        cfg["tools"] = [types.Tool(google_search=types.GoogleSearch())]
    elif json_out:
        cfg["response_mime_type"] = "application/json"
    try:
        text = generate("text", prompt, types.GenerateContentConfig(**cfg)).text or ""
    except (genai_errors.APIError, httpx.TimeoutException) as e:
        if not os.getenv("OPENAI_API_KEY"):
            raise
        print(f"Gemini ishlamadi ({getattr(e, 'code', 'timeout')}), OpenAI matn modeliga o'tilmoqda", flush=True)
        text = openai_chat(prompt, json_out)
    return parse_json(text) if json_out else text


_openai_model = None
OPENAI_PREFERRED = ("gpt-5-mini", "gpt-4.1-mini", "gpt-4o-mini")


def openai_chat(prompt, json_out=False):
    """Zaxira: Gemini band bo'lsa OpenAI Chat Completions."""
    global _openai_model
    headers = {"Authorization": f"Bearer {env('OPENAI_API_KEY')}"}
    if _openai_model is None:
        _openai_model = os.getenv("OPENAI_TEXT_MODEL")
    if not _openai_model:
        ids = [m["id"] for m in requests.get("https://api.openai.com/v1/models", headers=headers,
                                             timeout=30).json().get("data", [])]
        _openai_model = next((m for m in OPENAI_PREFERRED if m in ids), None) or next(
            (m for m in sorted(ids, reverse=True) if m.startswith("gpt-") and "mini" in m), "gpt-4o-mini")
        print(f"OpenAI matn modeli: {_openai_model}", flush=True)
    body = {"model": _openai_model, "messages": [{"role": "user", "content": prompt}]}
    if json_out:
        body["response_format"] = {"type": "json_object"}
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI matn xatosi {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"]


def parse_json(text):
    """Javobdagi birinchi JSON obyekt/ro'yxatni oladi (```json bloklari va ortiqcha matnga chidamli)."""
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch in "{[":
            try:
                return decoder.raw_decode(text, i)[0]
            except json.JSONDecodeError:
                continue
    raise ValueError(f"JSON topilmadi: {text[:300]}")


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
