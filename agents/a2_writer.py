"""2-agent: postni berilgan stil va formatda yozadi."""
import re

from .common import ask

EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2190-\u21FF\u2B00-\u2BFF\uFE0F\u200D]")


def plain_audio_script(text, limit=1100):
    """Model ishlamasa: asl postdan ovoz uchun toza matn (emoji, hashteg, havolasiz)."""
    text = re.sub(r"https?://\S+|t\.me/\S+|#\w+", "", text)
    text = EMOJI.sub("", text.replace("→", ":"))
    lines = [ln.strip(" -:") for ln in text.splitlines() if ln.strip(" -:")]
    lines = [ln if ln[-1] in ".!?:" else ln + "." for ln in lines]
    out = ""
    for ln in lines:
        if len(out) + len(ln) > limit:
            break
        out += ln + " "
    return out.strip()

OUTPUT_SPEC = """Faqat JSON qaytar:
{{"post_text": "tayyor post, oddiy matn (HTML/Markdown yo'q), emoji bilan",
  "audio_script": "post mazmunini 60-90 soniyada ovoz chiqarib aytish uchun sodda, jonli matn; emoji, hashteg va havolalarsiz",
  "image_prompt": "rasm sahnasi uchun inglizcha 1-2 jumla: yorqin 3D Pixar uslubi; ko'zlari chaqnab turgan yoqimli robotlar, sxema yig'ayotgan baxtli o'zbek bolalari yoki zamonaviy robototexnika laboratoriyasi; abstrakt chiziqlar va yozuv bo'lmasin"}}"""


def write_plan_post(plan_post, mode, cycle, angles=None, feedback=None):
    fix = f"\nOldingi variant sifat nazoratidan o'tmadi. Tuzat: {feedback}\n" if feedback else ""
    if mode == "exact":
        task = """Post matnini O'ZGARTIRMA: post_text maydoniga asl matnni aynan o'zini qo'y.
Faqat audio_script va image_prompt ni tayyorla."""
    else:
        task = f"""Bu postning {cycle}-aylanishdagi YANGI variantini yoz.
- Mavzu, tuzilma, barcha faktlar (yosh guruhlari, kurs bloklari, Robo-Ball, sovg'alar, manzil, telefon, havolalar) asl matndagidek qolsin.
- Sarlavha, kirish qismi, misollar va jumlalarni yangicha yoz, takror o'qigan odam zerikmasin.
- Yangi narx, chegirma, va'da, sana yoki kontakt O'YLAB TOPMA.
- Hashteglarni saqla. Uzunligi asl matnga yaqin bo'lsin (maksimum 3500 belgi).
Yangi kirish uchun g'oyalar (ixtiyoriy): {(angles or {}).get('hooks', [])}
Manbali faktlar (faqat mos kelsa, bittadan ko'p emas): {(angles or {}).get('facts', [])}"""
    prompt = f"""Sen robototexnika kursi Telegram kanali muallifisan. Til: o'zbek (lotin).
Post mavzusi: {plan_post['theme']}

ASL POST:
{plan_post['text']}

{task}
{fix}
{OUTPUT_SPEC}"""
    if mode != "exact":
        return ask(prompt, json_out=True)
    try:
        draft = ask(prompt, json_out=True)
    except Exception as e:  # noqa: BLE001 - asl matn uchun model shart emas
        print(f"2-agent: model ishlamadi ({str(e)[:120]}), audio matni asl postdan olinadi", flush=True)
        draft = {"audio_script": plain_audio_script(plan_post["text"]), "image_prompt": ""}
    draft["post_text"] = plan_post["text"]
    return draft


def write_tip_post(topic, rubric, style, feedback=None):
    """"Claude maslahatlar" rubrikasi uchun post."""
    fix = f"\nOldingi variant sifat nazoratidan o'tmadi. Tuzat: {feedback}\n" if feedback else ""
    prompt = f"""Sen "{rubric['name']}" rubrikasi uchun Telegram post muallifisan.
Til: {rubric['language']}. Auditoriya: {rubric['audience']}.
Mavzu: {topic['topic']}
Kontekst: {topic.get('why', '')}
Manbalar: {topic.get('sources', [])}

Quyidagi stil va namunalarga amal qil:
{style}
{fix}
Talablar: faktlar aniq, uydirma funksiya yoki narx yo'q, 1500 belgigacha, oxirida {rubric['hashtag']} #robototexnika.
{OUTPUT_SPEC}"""
    return ask(prompt, json_out=True)
