"""5-agent: sifat nazorati (qoidalar + model tekshiruvi)."""
import re

from .common import ask

ALLOWED_TAGS = {"b", "i", "u", "s", "code", "pre", "a", "blockquote", "tg-spoiler"}


def rule_check(draft, rubric):
    issues = []
    html = draft.get("post_html", "")
    plain = re.sub(r"<[^>]+>", "", html)
    if len(plain) > 1024:
        issues.append(f"Matn {len(plain)} belgi, 1024 dan oshmasin")
    if len(plain) < 200:
        issues.append("Matn juda qisqa")
    for tag in re.findall(r"</?([a-zA-Z-]+)", html):
        if tag.lower() not in ALLOWED_TAGS:
            issues.append(f"Telegram qo'llamaydigan teg: <{tag}>")
    for tag in ("b", "i", "code"):
        if html.count(f"<{tag}>") != html.count(f"</{tag}>"):
            issues.append(f"<{tag}> yopilmagan")
    if rubric["hashtag"].lower() not in html.lower():
        issues.append(f"{rubric['hashtag']} hashtegi yo'q")
    if len(draft.get("audio_script", "")) < 100:
        issues.append("Audio matni juda qisqa")
    return issues


def review(draft, topic, rubric, style):
    issues = rule_check(draft, rubric)
    if issues:
        return {"ok": False, "score": 0, "issues": issues}
    prompt = f"""Sen qattiq muharrirsan. Quyidagi Telegram postini tekshir.
Rubrika: {rubric['name']}. Til: {rubric['language']}. Mavzu: {topic['topic']}
Kutilgan stil:
{style}

POST:
{draft['post_html']}

AUDIO MATN:
{draft['audio_script']}

Bahola (1-10): faktik aniqlik (uydirma yo'qmi), o'zbek tili imlosi va grammatikasi,
stilga moslik, amaliy foyda, xavfsizlik (zararli maslahat yo'q).
Faqat JSON: {{"score": 0-10, "issues": ["..."]}}"""
    res = ask(prompt, json_out=True)
    score = float(res.get("score", 0))
    return {"ok": score >= 8, "score": score, "issues": res.get("issues", [])}
