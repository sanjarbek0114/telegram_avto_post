"""6-agent: admin bot orqali kanalga chiqaradi: rasm -> to'liq matn -> audio."""
import requests

from .common import env

CAPTION_LIMIT = 1024


def _api(method, **kw):
    r = requests.post(
        f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/{method}", timeout=120, **kw
    )
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method}: {data.get('description')}")
    return data["result"]


def publish(post_text, image_path, audio_path, title):
    chat = env("TELEGRAM_CHANNEL_ID")
    with open(image_path, "rb") as img:
        if len(post_text) <= CAPTION_LIMIT:
            msg = _api("sendPhoto", data={"chat_id": chat, "caption": post_text}, files={"photo": img})
        else:
            _api("sendPhoto", data={"chat_id": chat}, files={"photo": img})
            msg = _api("sendMessage", json={"chat_id": chat, "text": post_text,
                                            "link_preview_options": {"is_disabled": True}})
    if not audio_path:
        return msg["message_id"]
    with open(audio_path, "rb") as aud:
        _api("sendAudio", data={"chat_id": chat, "title": title, "performer": "Robototexnika kursi",
                                "reply_to_message_id": msg["message_id"]},
             files={"audio": ("post.mp3", aud, "audio/mpeg")})
    return msg["message_id"]


def notify_admin(text):
    admin = env("TELEGRAM_ADMIN_CHAT_ID", required=False)
    if not admin:
        return
    try:
        _api("sendMessage", data={"chat_id": admin, "text": text[:4000]})
    except Exception as e:  # asosiy xatoni yashirmasin
        print(f"Adminga xabar yuborilmadi ({e}). Botga /start bosilganmi?", flush=True)
