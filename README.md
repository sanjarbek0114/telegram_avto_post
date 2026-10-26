# Robototexnika kanali: "Claude maslahatlar" avtopost

Har kuni 19:00 (Asia/Tashkent) da kanalga rasm + matn + audio post chiqaradi.

| Agent | Fayl | Vazifa |
|---|---|---|
| 1 | `agents/a1_research.py` | Gemini + Google Search bilan yangi mavzular izlaydi, takrorlanmasin |
| 2 | `agents/a2_writer.py` | `config/style.md` stilida post, audio matni va rasm promptini yozadi |
| 3 | `agents/a3_image.py` | Nano Banana (`gemini-2.5-flash-image`) bilan rasm |
| 4 | `agents/a4_audio.py` | ElevenLabs bilan MP3 audio |
| 5 | `agents/a5_quality.py` | Qoidalar + model tekshiruvi, ball < 8 bo'lsa qayta yozdiradi (3 marta) |
| 6 | `agents/a6_publish.py` | Bot orqali kanalga: rasm+izoh, ostidan audio. Xato bo'lsa adminga xabar |

## Sozlash
1. Bu papkani GitHub repoga yuklang.
2. Repo > Settings > Secrets and variables > Actions ga qo'shing:
   `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`,
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`, `TELEGRAM_ADMIN_CHAT_ID` (ixtiyoriy).
3. Botni kanalga admin qiling ("Post messages" huquqi bilan).
4. `config/style.md` ga o'z namunaviy postlaringizni qo'ying.
5. Actions > "Kunlik post" > Run workflow (dry_run) bilan sinab ko'ring; natija Artifacts'da.

## Lokal sinov
```
pip install -r requirements.txt
cp .env.example .env   # kalitlarni to'ldiring
python main.py --dry-run
```
