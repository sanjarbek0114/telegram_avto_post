"""3-agent: Gemini (Nano Banana) bilan post rasmi."""
from google.genai import types

from .common import env, gemini


def make_image(image_prompt, out_path):
    prompt = (
        f"{image_prompt}\n\nStyle: clean modern illustration, bright, square 1:1, "
        "for a Telegram robotics education channel. No text, no letters, no logos."
    )
    resp = gemini().models.generate_content(
        model=env("IMAGE_MODEL", "gemini-2.5-flash-image"),
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )
    for part in resp.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            out_path.write_bytes(part.inline_data.data)
            return out_path
    raise RuntimeError("Rasm qaytmadi")
