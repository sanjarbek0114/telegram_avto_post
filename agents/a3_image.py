"""3-agent: OpenAI (DALL-E 3) bilan post rasmi."""
import base64

import requests

from .common import env

API_URL = "https://api.openai.com/v1/images/generations"
FALLBACK_MODEL = "gpt-image-1"  # dall-e-3 yopilgan bo'lsa


def _request(model, prompt):
    body = {"model": model, "prompt": prompt, "n": 1, "size": "1024x1024"}
    if model.startswith("dall-e"):
        body.update(quality="hd", style="vivid", response_format="b64_json")
    r = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {env('OPENAI_API_KEY')}"},
        json=body,
        timeout=180,
    )
    return r


def make_image(image_prompt, out_path):
    prompt = (
        f"{image_prompt}\n\nStyle: clean modern illustration, bright, square 1:1, "
        "for a Telegram robotics education channel. No text, no letters, no logos."
    )[:4000]
    model = env("OPENAI_IMAGE_MODEL", "dall-e-3", required=False)
    r = _request(model, prompt)
    if r.status_code in (400, 404) and "model" in r.text.lower() and model != FALLBACK_MODEL:
        print(f"{model} ishlamadi ({r.status_code}), {FALLBACK_MODEL} bilan urinilmoqda", flush=True)
        r = _request(FALLBACK_MODEL, prompt)
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI rasm xatosi {r.status_code}: {r.text[:300]}")
    out_path.write_bytes(base64.b64decode(r.json()["data"][0]["b64_json"]))
    return out_path
