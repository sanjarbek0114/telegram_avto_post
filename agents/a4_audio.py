"""4-agent: ElevenLabs orqali maslahatni audio qiladi."""
import requests

from .common import env


def make_audio(script, out_path):
    voice = env("ELEVENLABS_VOICE_ID")
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": env("ELEVENLABS_API_KEY"), "Content-Type": "application/json"},
        json={"text": script, "model_id": env("ELEVENLABS_MODEL", "eleven_v3")},
        timeout=180,
    )
    r.raise_for_status()
    out_path.write_bytes(r.content)
    return out_path
