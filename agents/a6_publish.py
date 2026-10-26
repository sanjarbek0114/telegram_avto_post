"""6-agent: admin bot orqali kanalga chiqaradi."""
import requests

from .common import env


def _api(method, **kw):
    r = requests.post(
        f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/{method}", timeout=120, **kw
    )
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method}: {data}")
    return data["result"]


def publish(post_html, image_path, audio_path, title):
    chat = env("TELEGRAM_CHANNEL_ID")
    with open(image_path, "rb") as img:
        msg = _api("sendPhoto", data={"chat_id": chat, "caption": post_html, "parse_mode": "HTML"},
                   files={"photo": img})
    with open(audio_path, "rb") as aud:
        _api("sendAudio", data={"chat_id": chat, "title": title, "performer": "Claude maslahatlar",
                                "reply_to_message_id": msg["message_id"]},
             files={"audio": ("maslahat.mp3", aud, "audio/mpeg")})
    return msg["message_id"]


def notify_admin(text):
    admin = env("TELEGRAM_ADMIN_CHAT_ID", required=False)
    if admin:
        _api("sendMessage", data={"chat_id": admin, "text": text[:4000]})
