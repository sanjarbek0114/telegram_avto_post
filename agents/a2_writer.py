"""2-agent: mavzudan maslahat topib, berilgan stil va formatda post yozadi."""
from .common import ask


def write_post(topic, rubric, style, feedback=None):
    fix = f"\nOldingi variant sifat nazoratidan o'tmadi. Tuzat: {feedback}\n" if feedback else ""
    prompt = f"""Sen "{rubric['name']}" rubrikasi uchun Telegram post muallifisan.
Til: {rubric['language']}. Auditoriya: {rubric['audience']}.
Mavzu: {topic['topic']}
Kontekst: {topic.get('why', '')}
Manbalar: {topic.get('sources', [])}

Quyidagi stil va formatga QAT'IY amal qil:
{style}
{fix}
Talablar:
- Faktlar aniq bo'lsin, uydirma funksiya yoki narx yozma.
- Post matni {rubric['max_caption_chars']} belgidan oshmasin (Telegram rasm izohi chegarasi).
- Telegram HTML formatidan foydalan: <b>, <i>, <code>. Markdown ishlatma.

Faqat JSON qaytar:
{{"post_html": "...",
  "audio_script": "post mazmunini 40-70 soniyada ovoz chiqarib aytish uchun sodda matn, emoji va teglarsiz",
  "image_prompt": "rasm uchun inglizcha batafsil prompt, matnsiz, robototexnika + AI mavzusida"}}"""
    return ask(prompt, json_out=True)
