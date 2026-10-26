"""3-agent: post rasmi.

Uslub har doim bir xil: yorqin 3D render (Pixar/Disney), yoqimli robotlar, baxtli bolalar,
zamonaviy robototexnika laboratoriyasi. Abstrakt/geometrik chiziqli rasm hech qachon chizilmaydi.

Navbat: 1) oldindan tayyorlangan rasm (state/prepared), 2) Nano Banana, 3) Gemini Imagen,
4) Hugging Face FLUX (HF_TOKEN bo'lsa, bepul), 5) Pollinations (qisqa va aniq inglizcha prompt).
Har bir rasmni Gemini ko'zi bilan baholaymiz (uslub, mazmun, abstrakt chiziq yo'qligi); eng yaxshisi olinadi.
6) avval chiqqan sifatli rasmlardan biri (state/gallery). Hech biri bo'lmasa post rasmsiz chiqadi.
"""
import io
import os
import random
import shutil
import time
import urllib.parse

import requests
from google.genai import errors as genai_errors
from google.genai import types

from .common import ROOT, _version, gemini, generate, parse_json

PREPARED = ROOT / "state/prepared"
GALLERY = ROOT / "state/gallery"
GALLERY_KEEP = 10
GOOD_SCORE = 7  # shundan past rasm kanalga chiqmaydi
MIN_SCORE = 5

STYLE = ("Bright colorful 3D render in Pixar / Disney animation style, cinematic soft lighting, "
         "vivid cheerful colors, glossy materials, shallow depth of field, professional high quality, "
         "highly detailed, 8k, appealing to kids and parents. Square 1:1 composition.")
NEGATIVE = ("Do NOT include: abstract lines, geometric patterns, circuit-line backgrounds, flat vector "
            "shapes, low quality, blurry, distorted faces, extra fingers, creepy or scary robots, "
            "any text, letters, numbers, logos or watermarks.")

# Har bir kontent-plan posti uchun sahna (rasm mavzuga mos bo'lsin)
SCENES = {
    1: ("a happy 9-year-old Uzbek boy at a cozy home desk who has put his smartphone aside and is "
        "proudly building a cute small robot with big glowing blue eyes, his smiling mother watching"),
    2: ("a modern bright robotics classroom where cheerful Uzbek kids aged 8-14 build electronic "
        "circuits and small wheeled robots together, one kid holding up a shiny golden reward coin, "
        "a cute friendly robot with glowing eyes cheering on the table"),
    3: ("curious Uzbek kids in a modern robotics lab connecting an Arduino board with colorful wires, "
        "a glowing LED lighting up, sensors and small motors on the desk, a cute robot with glowing "
        "cyan eyes watching"),
    4: ("a proud Uzbek teenager presenting a smart robot car at a school project fair, the robot "
        "with glowing eyes avoiding obstacles, happy parents and classmates applauding"),
    5: ("a confident Uzbek teenage girl and boy holding a gold trophy at a robotics competition next "
        "to their cute robot with glowing eyes, bright stage lights and confetti"),
}
DEFAULT_SCENE = ("happy kids building a cute friendly robot with big glowing eyes in a bright modern "
                 "robotics laboratory")


def compose_prompt(scene_hint, plan_n=None):
    """Batafsil prompt (Gemini/Imagen uchun)."""
    scene = SCENES.get(plan_n, DEFAULT_SCENE)
    extra = f" Additional idea for the scene (keep it cute and friendly): {scene_hint.strip()[:300]}" if scene_hint else ""
    return f"{STYLE}\n\nScene: {scene}.{extra}\n\n{NEGATIVE}"


def pollinations_prompt(plan_n=None):
    """Pollinations uchun qisqa, aniq inglizcha prompt (uzun matnni yaxshi tushunmaydi)."""
    scene = SCENES.get(plan_n, DEFAULT_SCENE)
    return (f"Cute friendly 3D robot with glowing eyes, Pixar style, {scene}, bright robotics laboratory, "
            "vivid colors, soft cinematic lighting, high quality, highly detailed, no text")


def _imagen_models():
    override = os.getenv("IMAGEN_MODEL")
    if override:
        return [override]
    names = [m.name.split("/")[-1] for m in gemini().models.list()]
    imagen = [n for n in names if "imagen" in n and "generate" in n and "ultra" not in n]
    return sorted(imagen, key=_version, reverse=True)[:2]


def _imagen(prompt):
    for name in _imagen_models():
        try:
            print(f"  -> {name} (imagen)", flush=True)
            resp = gemini().models.generate_images(
                model=name, prompt=prompt,
                config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="1:1"),
            )
            if resp.generated_images:
                return resp.generated_images[0].image.image_bytes
        except genai_errors.APIError as e:
            print(f"  !! {name}: {e.code} {str(e)[:150]}", flush=True)
    return None


def _gemini_image(prompt):
    try:
        resp = generate("image", prompt, types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]))
    except Exception as e:  # noqa: BLE001 - keyingi manbaga o'tamiz
        print(f"  !! nano banana: {str(e)[:150]}", flush=True)
        return None
    for part in resp.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            return part.inline_data.data
    return None


def _huggingface(prompt):
    token = os.getenv("HF_TOKEN")
    if not token:
        return None
    model = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
    try:
        print(f"  -> huggingface {model}", flush=True)
        r = requests.post(f"https://router.huggingface.co/hf-inference/models/{model}",
                          headers={"Authorization": f"Bearer {token}"},
                          json={"inputs": prompt, "parameters": {"width": 1024, "height": 1024}}, timeout=180)
        if r.ok and r.headers.get("content-type", "").startswith("image/"):
            return r.content
        print(f"  !! huggingface: {r.status_code} {r.text[:150]}", flush=True)
    except requests.RequestException as e:
        print(f"  !! huggingface: {e}", flush=True)
    return None


def _remove_watermark(data):
    """Kalitsiz Pollinations pastki o'ng burchakka logo qo'yadi: chetini qirqib tashlaymiz."""
    from PIL import Image

    img = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = img.size
    cut = int(h * 0.075)
    img = img.crop((cut // 2, 0, w - cut // 2, h - cut)).resize((1024, 1024), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _pollinations(prompt):
    key = os.getenv("POLLINATIONS_KEY")
    params = {"width": 1024, "height": 1024, "nologo": "true", "model": "flux",
              "seed": random.randint(1, 10**6)}
    if key:
        url = "https://gen.pollinations.ai/image/" + urllib.parse.quote(prompt)
        headers = {"Authorization": f"Bearer {key}"}
    else:
        url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)
        headers = {}
    try:
        print("  -> pollinations", flush=True)
        r = requests.get(url, params=params, headers=headers, timeout=150)
        if r.ok and r.headers.get("content-type", "").startswith("image/") and len(r.content) > 20_000:
            return r.content if key else _remove_watermark(r.content)
        print(f"  !! pollinations: {r.status_code}", flush=True)
    except requests.RequestException as e:
        print(f"  !! pollinations: {e}", flush=True)
    return None


JUDGE = """You are a strict art director for a kids robotics course Telegram channel.
Rate this image from 1 to 10. Requirements: bright, colorful 3D render in Pixar/Disney style; cute friendly
robots with glowing eyes, and/or happy kids building circuits, and/or a modern robotics lab; professional,
appealing to kids and parents. Give a LOW score (1-4) for: abstract or geometric line art, dark or gloomy mood,
scary or creepy robots, distorted faces or hands, visible text, letters or watermarks, low quality.
Return JSON only: {"score": number, "reason": "short"}"""


def judge(data):
    """5-agent ko'zi: rasm talabga mosmi. Baholab bo'lmasa None."""
    mime = "image/jpeg" if data[:3] == b"\xff\xd8\xff" else "image/png"
    try:
        resp = generate("text", [types.Part.from_bytes(data=data, mime_type=mime), JUDGE],
                        types.GenerateContentConfig(response_mime_type="application/json"))
        res = parse_json(resp.text or "")
        print(f"  rasm bahosi: {res.get('score')} ({res.get('reason', '')[:120]})", flush=True)
        return float(res.get("score", 0))
    except Exception as e:  # noqa: BLE001
        print(f"  !! rasm baholanmadi: {str(e)[:150]}", flush=True)
        return None


def prepared_path(plan_n, cycle):
    return PREPARED / f"plan-{plan_n}-cycle-{cycle}.png"


def _to_gallery(path):
    GALLERY.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, GALLERY / f"{time.strftime('%Y%m%d-%H%M%S')}.png")
    for old in sorted(GALLERY.glob("*.png"))[:-GALLERY_KEEP]:
        old.unlink()


def generate_image(scene_hint, out_path, plan_n=None):
    """Faqat AI manbalaridan yangi rasm. Natija: (path, manba) yoki (None, None)."""
    prompt = compose_prompt(scene_hint, plan_n)
    short = pollinations_prompt(plan_n)
    sources = (("Nano Banana", _gemini_image, prompt, 1), ("Imagen", _imagen, prompt, 1),
               ("Hugging Face", _huggingface, short, 2), ("Pollinations", _pollinations, short, 4))
    best = (None, None, -1.0)  # data, manba, ball
    for source, fn, p, tries in sources:
        for _ in range(tries):
            data = fn(p)
            if not data:
                break
            score = judge(data)
            if score is None:
                score = GOOD_SCORE  # baholovchi ishlamasa ham AI rasmi abstrakt fondan yaxshi
            if score > best[2]:
                best = (data, source, score)
            if score >= GOOD_SCORE:
                break
        if best[2] >= GOOD_SCORE:
            break
    data, source, score = best
    if data is None or score < MIN_SCORE:
        return None, None
    print(f"3-agent: rasm manbasi {source}, baho {score}", flush=True)
    out_path.write_bytes(data)
    if score >= GOOD_SCORE:
        _to_gallery(out_path)
    return out_path, source


def make_image(scene_hint, out_path, plan_n=None, cycle=None, keep_prepared=False):
    """Post uchun rasm. Oldindan tayyorlangan bo'lsa o'shani ishlatadi."""
    if plan_n and cycle:
        ready = prepared_path(plan_n, cycle)
        if ready.exists():
            print(f"3-agent: oldindan tayyorlangan rasm ishlatiladi ({ready.name})", flush=True)
            (shutil.copy if keep_prepared else shutil.move)(ready, out_path)
            return out_path, "tayyorlangan"
    path, source = generate_image(scene_hint, out_path, plan_n)
    if path:
        return path, source
    old = sorted(GALLERY.glob("*.png")) if GALLERY.exists() else []
    if old:
        print("3-agent: servislar band, avvalgi sifatli rasmlardan biri olindi", flush=True)
        shutil.copy(random.choice(old), out_path)
        return out_path, "galereya"
    print("3-agent: rasm yo'q, post rasmsiz chiqadi (abstrakt rasm chizilmaydi)", flush=True)
    return None, None
