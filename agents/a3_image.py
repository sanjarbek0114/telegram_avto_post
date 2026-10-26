"""3-agent: Gemini (Nano Banana) bilan post rasmi."""
from google.genai import types

from .common import generate


def make_image(image_prompt, out_path):
    prompt = (
        f"{image_prompt}\n\nStyle: clean modern illustration, bright, square 1:1, "
        "for a Telegram robotics education channel. No text, no letters, no logos."
    )
    resp = generate("image", prompt, types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]))
    for part in resp.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            out_path.write_bytes(part.inline_data.data)
            return out_path
    raise RuntimeError("Rasm qaytmadi")
