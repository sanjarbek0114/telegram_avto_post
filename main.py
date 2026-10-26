"""Kunlik pipeline: mavzu -> post -> rasm -> audio -> sifat nazorati -> 19:00 da chiqarish."""
import argparse
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from agents.a1_research import find_topics
from agents.a2_writer import write_post
from agents.a3_image import make_image
from agents.a4_audio import make_audio
from agents.a5_quality import review
from agents.a6_publish import notify_admin, publish
from agents.common import ROOT, load_history, load_rubric, load_style, save_history

TZ = ZoneInfo("Asia/Tashkent")
MAX_REWRITES = 3


def log(msg):
    print(f"[{datetime.now(TZ):%H:%M:%S}] {msg}", flush=True)


def wait_until(hhmm):
    h, m = map(int, hhmm.split(":"))
    now = datetime.now(TZ)
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if target < now - timedelta(hours=2):  # kecha uchun emas, bugun uchun
        target += timedelta(days=1)
    secs = (target - now).total_seconds()
    if secs > 0:
        log(f"{hhmm} gacha kutilmoqda ({int(secs)} s)")
        time.sleep(secs)


def build_post(rubric, style, history):
    topics = find_topics(rubric, history)
    log(f"1-agent: {len(topics)} ta mavzu topildi")
    for topic in topics:
        log(f"Mavzu: {topic['topic']}")
        feedback = None
        for attempt in range(1, MAX_REWRITES + 1):
            draft = write_post(topic, rubric, style, feedback)
            qc = review(draft, topic, rubric, style)
            log(f"5-agent: urinish {attempt}, ball {qc['score']}, muammolar: {qc['issues']}")
            if qc["ok"]:
                return topic, draft, qc
            feedback = "; ".join(qc["issues"])
    raise RuntimeError("Hech bir mavzu sifat nazoratidan o'tmadi")


def main():
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish-at", help="Asia/Tashkent vaqti, masalan 19:00")
    ap.add_argument("--dry-run", action="store_true", help="Kanalga chiqarmaydi")
    args = ap.parse_args()
    dry = args.dry_run or os.getenv("DRY_RUN") == "1"

    out = ROOT / "out" / datetime.now(TZ).strftime("%Y-%m-%d")
    out.mkdir(parents=True, exist_ok=True)
    rubric, style, history = load_rubric(), load_style(), load_history()

    try:
        topic, draft, qc = build_post(rubric, style, history)
        (out / "post.html").write_text(draft["post_html"], encoding="utf-8")
        image = make_image(draft["image_prompt"], out / "image.png")
        log("3-agent: rasm tayyor")
        audio = make_audio(draft["audio_script"], out / "audio.mp3")
        log("4-agent: audio tayyor")

        if dry:
            log(f"DRY RUN: natijalar {out} papkasida")
            return
        if args.publish_at:
            wait_until(args.publish_at)
        msg_id = publish(draft["post_html"], image, audio, topic["topic"][:60])
        log(f"6-agent: chiqarildi, message_id={msg_id}")
        history["posts"].append({
            "date": datetime.now(TZ).date().isoformat(),
            "topic": topic["topic"],
            "score": qc["score"],
            "message_id": msg_id,
        })
        save_history(history)
    except Exception as e:
        log(f"XATO: {e}")
        notify_admin(f"⚠️ Bugungi post chiqmadi: {e}")
        raise


if __name__ == "__main__":
    main()
