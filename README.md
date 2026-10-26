# Robototexnika kursi kanali: avtopost

Har kuni 19:00 (Asia/Tashkent) da kanalga rasm, to'liq matn va audio post chiqaradi.

## Nima chiqadi
`config/content_plan.md` dagi 5 ta post navbat bilan chiqadi: 1, 2, 3, 4, 5, keyin yana 1.
- 1-aylanish: asl matn aynan chiqadi.
- Keyingi aylanishlar (`config/settings.json` da `"mode": "rewrite"`): mavzu va faktlar saqlanadi, sarlavha, kirish va jumlalar yangicha yoziladi. `"mode": "exact"` bo'lsa har doim asl matn.
- `"alternate_with_claude_tips": true` bo'lsa, kontent-plan bilan "Claude maslahatlar" posti navbatlashadi.

Matn 1024 belgidan uzun bo'lsa: avval rasm, keyin matn, ostidan audio.

| Agent | Fayl | Vazifa |
|---|---|---|
| 1 | `agents/a1_research.py` | Yangi kirish g'oyalari va manbali faktlarni internetdan izlaydi |
| 2 | `agents/a2_writer.py` | Post varianti, audio matni va rasm promptini yozadi |
| 3 | `agents/a3_image.py` | Gemini rasm modeli (Nano Banana) bilan rasm |
| 4 | `agents/a4_audio.py` | ElevenLabs bilan MP3 audio |
| 5 | `agents/a5_quality.py` | Telefon, havola, hashteglar o'zgarmaganini va faktlarni tekshiradi, ball 8 dan past bo'lsa qayta yozdiradi |
| 6 | `agents/a6_publish.py` | Bot orqali kanalga chiqaradi, xato bo'lsa adminga xabar |

Navbat `state/history.json` da saqlanadi (workflow uni har kuni commit qiladi).

## Sozlash
- Secrets: `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`, `TELEGRAM_ADMIN_CHAT_ID`.
- Admin xabarlari kelishi uchun botga bir marta /start yozing.
- Sinov: Actions > "Kunlik post" > Run workflow (dry_run). Natija Artifacts'da.

## Lokal sinov
```
pip install -r requirements.txt
cp .env.example .env   # kalitlarni to'ldiring
python main.py --dry-run
```
