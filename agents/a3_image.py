"""3-agent: OpenAI (DALL-E 3) bilan post rasmi."""
import base64

import requests

from .common import env

API_URL = "https://api.openai.com/v1/images/generations"
FALLBACK_MODEL = "gpt-image-1"  # dall-e-3 yopilgan bo'lsa
DALLE_EXTRAS = {"quality": "hd", "style": "vivid", "response_format": "b64_json"}


def _request(model, prompt, extras):
    body = {"model": model, "prompt": prompt, "n": 1, "size": "1024x1024", **extras}
    return requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {env('OPENAI_API_KEY')}"},
        json=body,
        timeout=180,
    )


def _generate(model, prompt):
    extras = dict(DALLE_EXTRAS) if model.startswith("dall-e") else {}
    while True:
        r = _request(model, prompt, extras)
        err = r.json().get("error", {}) if r.status_code != 200 else {}
        # OpenAI model parametrlarini o'zgartirgan bo'lsa, qo'llanmaydiganini olib tashlab qayta urinamiz
        if err.get("code") == "unknown_parameter" and err.get("param") in extras:
            print(f"{model}: '{err['param']}' parametri qo'llanmaydi, olib tashlandi", flush=True)
            extras.pop(err["param"])
            continue
        return r


def _image_bytes(item):
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    r = requests.get(item["url"], timeout=120)
    r.raise_for_status()
    return r.content


def make_image(image_prompt, out_path):
    prompt = (
        f"{image_prompt}\n\nStyle: clean modern illustration, bright, square 1:1, "
        "for a Telegram robotics education channel. No text, no letters, no logos."
    )[:4000]
    model = env("OPENAI_IMAGE_MODEL", "dall-e-3", required=False)
    r = _generate(model, prompt)
    if r.status_code in (400, 404) and "model" in r.text.lower() and model != FALLBACK_MODEL:
        print(f"{model} ishlamadi ({r.status_code}), {FALLBACK_MODEL} bilan urinilmoqda", flush=True)
        r = _generate(FALLBACK_MODEL, prompt)
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI rasm xatosi {r.status_code}: {r.text[:300]}")
    out_path.write_bytes(_image_bytes(r.json()["data"][0]))
    return out_path
