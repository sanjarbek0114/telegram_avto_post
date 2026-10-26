"""4-agent: ElevenLabs orqali postni audio qiladi."""
import requests

from .common import env

API = "https://api.elevenlabs.io/v1"
# Kanal ovozi: radio boshlovchisidek mayin, yoqimli ayol ovozi (SANJARBEK talabi).
# Standart kutubxonadagi ayol ovozlari, birinchisi asosiy: Sarah, Matilda, Lily, Alice.
DEFAULT_VOICES = ("EXAVITQu4vr4xnSDxMaL", "XrExE9yKIg1WjnnlVkGX", "pFZP5JQG7iQjIQuC4Bku",
                  "Xb7hH8MSUJpSbSDYk0k2")
MALE_VOICES = {"JBFqnCBsd6RMkjVDRZzb", "pNInz6obpgDQGcFmaJgB"}
# Yosh (16-18 yoshli qizdek), mayin va jonli ovoz uchun sozlamalar
VOICE_SETTINGS = {"stability": 0.35, "similarity_boost": 0.85, "style": 0.15, "use_speaker_boost": True}
V3_STABILITY = (0.0, 0.5, 1.0)  # eleven_v3 faqat shu qiymatlarni qabul qiladi


def _headers():
    return {"xi-api-key": env("ELEVENLABS_API_KEY")}


def _tts(voice, script):
    def call(settings):
        return requests.post(
            f"{API}/text-to-speech/{voice}",
            params={"output_format": "mp3_44100_128"},
            headers={**_headers(), "Content-Type": "application/json"},
            json={"text": script, "model_id": env("ELEVENLABS_MODEL", "eleven_v3"),
                  "voice_settings": settings},
            timeout=180,
        )

    r = call(VOICE_SETTINGS)
    if r.status_code in (400, 422) and "stability" in r.text:
        nearest = min(V3_STABILITY, key=lambda v: abs(v - VOICE_SETTINGS["stability"]))
        print(f"4-agent: model stability {VOICE_SETTINGS['stability']} ni qabul qilmadi, {nearest} ishlatiladi",
              flush=True)
        r = call({**VOICE_SETTINGS, "stability": nearest})
    return r


def make_audio(script, out_path):
    voice = env("ELEVENLABS_VOICE_ID", required=False)
    if not voice or voice in MALE_VOICES:
        voice = DEFAULT_VOICES[0]
    r = _tts(voice, script)
    if r.ok:
        print(f"4-agent: ovoz {voice} ishlatildi", flush=True)
    if r.status_code == 404 and "voice_not_found" in r.text:
        print(f"4-agent: ovoz topilmadi ({voice}), boshqa ovoz qidirilmoqda", flush=True)
        for alt in DEFAULT_VOICES:
            if alt == voice:
                continue
            r = _tts(alt, script)
            if r.ok or not (r.status_code == 404 and "voice_not_found" in r.text):
                print(f"4-agent: ovoz {alt} ishlatildi", flush=True)
                break
    if not r.ok:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
    out_path.write_bytes(r.content)
    return out_path
