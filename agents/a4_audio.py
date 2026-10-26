"""4-agent: ElevenLabs orqali postni audio qiladi."""
import requests

from .common import env

API = "https://api.elevenlabs.io/v1"
# Hamma yangi akkauntlarda bor standart ovozlar (berilgan ovoz topilmasa navbat bilan sinaladi)
DEFAULT_VOICES = ("JBFqnCBsd6RMkjVDRZzb", "EXAVITQu4vr4xnSDxMaL", "Xb7hH8MSUJpSbSDYk0k2",
                  "pNInz6obpgDQGcFmaJgB", "21m05zcH5m83TcN7ExXA")


def _headers():
    return {"xi-api-key": env("ELEVENLABS_API_KEY")}


def _account_voices():
    """Akkauntdagi ovozlar (kalitda voices_read ruxsati bo'lmasa bo'sh ro'yxat)."""
    try:
        r = requests.get(f"{API}/voices", headers=_headers(), timeout=30)
        if r.ok:
            return [v["voice_id"] for v in r.json().get("voices", [])]
        print(f"  !! ovozlar ro'yxati olinmadi: {r.status_code}", flush=True)
    except requests.RequestException as e:
        print(f"  !! ovozlar ro'yxati olinmadi: {e}", flush=True)
    return []


def _tts(voice, script):
    return requests.post(
        f"{API}/text-to-speech/{voice}",
        params={"output_format": "mp3_44100_128"},
        headers={**_headers(), "Content-Type": "application/json"},
        json={"text": script, "model_id": env("ELEVENLABS_MODEL", "eleven_v3")},
        timeout=180,
    )


def make_audio(script, out_path):
    voice = env("ELEVENLABS_VOICE_ID", required=False)
    r = _tts(voice, script) if voice else None
    if r is None or (r.status_code == 404 and "voice_not_found" in r.text):
        print(f"4-agent: ovoz topilmadi ({voice}), boshqa ovoz qidirilmoqda", flush=True)
        for alt in dict.fromkeys(_account_voices() + list(DEFAULT_VOICES)):
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
