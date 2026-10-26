"""3-agent: post rasmi.

Navbat: 1) Nano Banana (Gemini rasm modeli), 2) Gemini Imagen, 3) Pollinations (bepul, kalitsiz),
4) zaxira: Pillow bilan chizilgan rangli fon. Shunda rasm sababli post hech qachon to'xtab qolmaydi.
"""
import io
import os
import random
import urllib.parse

import requests
from google.genai import errors as genai_errors
from google.genai import types

from .common import _version, gemini, generate

STYLE = ("Style: clean modern illustration, bright, square 1:1, for a Telegram robotics education "
         "channel. No text, no letters, no logos.")


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


def _pollinations(prompt):
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt[:900])
    try:
        print("  -> pollinations", flush=True)
        r = requests.get(url, params={"width": 1024, "height": 1024, "nologo": "true",
                                      "seed": random.randint(1, 10**6)}, timeout=120)
        if r.ok and r.headers.get("content-type", "").startswith("image/"):
            return r.content
        print(f"  !! pollinations: {r.status_code}", flush=True)
    except requests.RequestException as e:
        print(f"  !! pollinations: {e}", flush=True)
    return None


def _fallback_card():
    """Hech bir servis ishlamasa: gradient fon va sxema chiziqlari."""
    from PIL import Image, ImageDraw

    size = 1024
    a, b = random.choice([((14, 30, 80), (0, 170, 200)), ((40, 10, 90), (255, 120, 60)),
                          ((5, 60, 50), (120, 220, 90))])
    img = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(img)
    for y in range(size):
        t = y / size
        draw.line([(0, y), (size, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))
    rnd = random.Random()
    for _ in range(40):
        x, y = rnd.randrange(0, size, 64), rnd.randrange(0, size, 64)
        x2, y2 = (x + rnd.choice([-128, 128]), y) if rnd.random() < 0.5 else (x, y + rnd.choice([-128, 128]))
        draw.line([(x, y), (x2, y2)], fill=(255, 255, 255), width=4)
        draw.ellipse([x2 - 10, y2 - 10, x2 + 10, y2 + 10], outline=(255, 255, 255), width=4)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def make_image(image_prompt, out_path):
    prompt = f"{image_prompt}\n\n{STYLE}"
    for source, fn in (("Nano Banana", _gemini_image), ("Imagen", _imagen), ("Pollinations", _pollinations)):
        data = fn(prompt)
        if data:
            print(f"3-agent: rasm manbasi {source}", flush=True)
            out_path.write_bytes(data)
            return out_path
    print("3-agent: barcha servislar ishlamadi, zaxira rasm chizildi", flush=True)
    out_path.write_bytes(_fallback_card())
    return out_path
