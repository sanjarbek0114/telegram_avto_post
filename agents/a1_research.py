"""1-agent: rubrika bo'yicha internetdan yangi mavzular izlaydi."""
from .common import ask, parse_json


def find_topics(rubric, history, n=5):
    used = [p["topic"] for p in history["posts"][-60:]]
    prompt = f"""Sen Telegram kanal uchun kontent tadqiqotchisisan.
Rubrika: {rubric['name']}
Auditoriya: {rubric['audience']}
Yo'nalish: {rubric['search_focus']}

Internetdan (so'nggi yangiliklar, Anthropic hujjatlari, bloglar, forumlar) qidirib,
{n} ta YANGI, amaliy va aniq post mavzusini top. Har biri bitta aniq maslahatga aylana olsin.
Avval ishlatilgan mavzularni takrorlama: {used}

Faqat JSON qaytar:
[{{"topic": "...", "why": "nega foydali", "sources": ["url", ...]}}]"""
    text = ask(prompt, search=True)
    topics = parse_json(text)
    return [t for t in topics if t.get("topic") and t["topic"] not in used]
