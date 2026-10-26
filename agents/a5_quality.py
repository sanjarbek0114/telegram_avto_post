"""5-agent: sifat nazorati (qoidalar + model tekshiruvi)."""
import re

from .common import ask

PHONE = re.compile(r"\+?\d[\d\s\-]{8,}\d")
URL = re.compile(r"https?://\S+|t\.me/\S+")


def rule_check(draft, original=None, hashtag=None):
    issues = []
    text = draft.get("post_text", "")
    if len(text) > 4000:
        issues.append(f"Matn {len(text)} belgi, 4000 dan oshmasin")
    if len(text) < 300:
        issues.append("Matn juda qisqa")
    if re.search(r"</?[a-z]+>|\*\*", text):
        issues.append("HTML/Markdown belgilari bo'lmasin, oddiy matn kerak")
    if len(draft.get("audio_script", "")) < 150:
        issues.append("Audio matni juda qisqa")
    if hashtag and hashtag.lower() not in text.lower():
        issues.append(f"{hashtag} hashtegi yo'q")
    if original:
        norm = lambda s: re.sub(r"\D", "", s)
        orig_phones = {norm(p) for p in PHONE.findall(original)}
        for p in PHONE.findall(text):
            if norm(p) not in orig_phones:
                issues.append(f"Asl matnda yo'q telefon raqami: {p}")
        for p in orig_phones:
            if p not in {norm(x) for x in PHONE.findall(text)}:
                issues.append("Asl matndagi telefon raqami tushib qolgan")
        orig_urls = set(URL.findall(original))
        for u in URL.findall(text):
            if u not in orig_urls:
                issues.append(f"Asl matnda yo'q havola: {u}")
        for u in orig_urls:
            if u not in text:
                issues.append(f"Havola tushib qolgan: {u}")
        for tag in re.findall(r"#\w+", original):
            if tag not in text:
                issues.append(f"Hashteg tushib qolgan: {tag}")
    return issues


def review(draft, theme, style, original=None, hashtag=None):
    issues = rule_check(draft, original, hashtag)
    if issues:
        return {"ok": False, "score": 0, "issues": issues}
    ref = f"\nASL POST (faktlar shu bilan mos bo'lishi shart):\n{original}\n" if original else ""
    prompt = f"""Sen qattiq muharrirsan. Telegram postini tekshir. Mavzu: {theme}
Kutilgan stil:
{style}
{ref}
TEKSHIRILADIGAN POST:
{draft['post_text']}

AUDIO MATN:
{draft['audio_script']}

Bahola (1-10): faktik aniqlik (asl matnda yo'q va'da, narx, sana, kontakt qo'shilmaganmi),
o'zbek tili imlosi va grammatikasi, stilga moslik, o'quvchiga foyda, xavfsizlik.
Faqat JSON: {{"score": 0-10, "issues": ["..."]}}"""
    res = ask(prompt, json_out=True)
    score = float(res.get("score", 0))
    return {"ok": score >= 8, "score": score, "issues": res.get("issues", [])}
