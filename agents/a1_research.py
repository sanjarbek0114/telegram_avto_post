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


def find_angles(plan_post, cycle):
    """Kontent-plan posti uchun yangi kirish g'oyalari va dolzarb, manbali faktlar."""
    prompt = f"""Robototexnika kursi Telegram kanali uchun post yangilanmoqda ({cycle}-aylanish).
Post mavzusi: {plan_post['theme']}

Internetdan qidirib top:
- 3 ta yangi "hook" (diqqat tortuvchi kirish g'oyasi) shu mavzuda, ota-onalar uchun;
- 0-2 ta dolzarb, tekshirilgan fakt yoki statistika (STEM, robototexnika, bolalar ta'limi), faqat ishonchli manbali.
Shubhali bo'lsa, faktni qo'shma.

Faqat JSON qaytar:
{{"hooks": ["..."], "facts": [{{"fact": "...", "source": "url"}}]}}"""
    try:
        return parse_json(ask(prompt, search=True))
    except Exception:
        return {"hooks": [], "facts": []}
