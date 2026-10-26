"""Kunlik pipeline: mavzu -> post -> rasm -> audio -> sifat nazorati -> 19:00 da chiqarish."""
import argparse
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from agents.a1_research import find_angles, find_topics
from agents.a2_writer import write_plan_post, write_tip_post
import shutil

from agents.a3_image import make_image, prepared_path
from agents.a4_audio import make_audio
from agents.a5_quality import review, rule_check
from agents.a6_publish import notify_admin, publish
from agents.common import (ROOT, load_history, load_plan, load_rubric, load_settings, load_style,
                           save_history)

TZ = ZoneInfo("Asia/Tashkent")
MAX_REWRITES = 3


def log(msg):
    print(f"[{datetime.now(TZ):%H:%M:%S}] {msg}", flush=True)


def wait_until(hhmm):
    h, m = map(int, hhmm.split(":"))
    now = datetime.now(TZ)
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    secs = (target - now).total_seconds()
    if secs > 0:
        log(f"{hhmm} gacha kutilmoqda ({int(secs)} s)")
        time.sleep(secs)


def next_kind(settings, history):
    if not settings.get("alternate_with_claude_tips"):
        return "plan"
    last = history["posts"][-1]["kind"] if history["posts"] else "tip"
    return "tip" if last == "plan" else "plan"


def build_plan_post(settings, style, history):
    plan = load_plan()
    done = sum(1 for p in history["posts"] if p.get("kind", "plan") == "plan")
    post = plan[done % len(plan)]
    cycle = done // len(plan) + 1
    mode = settings.get("mode", "rewrite")
    if cycle == 1 and mode == "rewrite":
        mode = "exact"  # birinchi aylanishda asl matn chiqadi
    log(f"Kontent-plan: {post['n']}-post ({post['theme']}), {cycle}-aylanish, rejim: {mode}")
    angles = find_angles(post, cycle) if mode == "rewrite" else None
    if angles:
        log(f"1-agent: {len(angles.get('hooks', []))} ta g'oya, {len(angles.get('facts', []))} ta fakt")
    feedback = None
    for attempt in range(1, MAX_REWRITES + 1):
        draft = write_plan_post(post, mode, cycle, angles, feedback)
        if mode == "exact":  # asl matn muallifniki: faqat qoidalar bilan tekshiramiz
            issues = rule_check(draft, post["text"])
            qc = {"ok": not issues, "score": None, "issues": issues}
        else:
            qc = review(draft, post["theme"], style, original=post["text"])
        log(f"5-agent: urinish {attempt}, ball {qc['score']}, muammolar: {qc['issues']}")
        if qc["ok"]:
            meta = {"kind": "plan", "plan_n": post["n"], "cycle": cycle, "topic": post["theme"]}
            return meta, draft, qc
        feedback = "; ".join(qc["issues"])
    if mode != "exact":
        log("Yangi variant o'tmadi, asl matn bilan chiqariladi")
        draft = write_plan_post(post, "exact", cycle)
        if not rule_check(draft, post["text"]):
            qc = {"ok": True, "score": None, "issues": ["asl matn"]}
            meta = {"kind": "plan", "plan_n": post["n"], "cycle": cycle, "topic": post["theme"]}
            return meta, draft, qc
    raise RuntimeError(f"{post['n']}-post sifat nazoratidan o'tmadi: {feedback}")


def build_tip_post(style, history):
    rubric = load_rubric()
    topics = find_topics(rubric, history)
    log(f"1-agent: {len(topics)} ta mavzu topildi")
    for topic in topics:
        log(f"Mavzu: {topic['topic']}")
        feedback = None
        for attempt in range(1, MAX_REWRITES + 1):
            draft = write_tip_post(topic, rubric, style, feedback)
            qc = review(draft, topic["topic"], style, hashtag=rubric["hashtag"])
            log(f"5-agent: urinish {attempt}, ball {qc['score']}, muammolar: {qc['issues']}")
            if qc["ok"]:
                return {"kind": "tip", "topic": topic["topic"]}, draft, qc
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
    settings, style, history = load_settings(), load_style(), load_history()

    today = datetime.now(TZ).date().isoformat()
    if not dry and any(p.get("date") == today for p in history["posts"]):
        log("Bugungi post allaqachon chiqqan, o'tkazib yuborildi")
        return

    try:
        if next_kind(settings, history) == "plan":
            meta, draft, qc = build_plan_post(settings, style, history)
        else:
            meta, draft, qc = build_tip_post(style, history)
        (out / "post.txt").write_text(draft["post_text"], encoding="utf-8")
        (out / "audio_script.txt").write_text(draft["audio_script"], encoding="utf-8")
        image, source = make_image(draft["image_prompt"], out / "image.png", meta.get("plan_n"),
                                   meta.get("cycle"), keep_prepared=dry)
        log(f"3-agent: rasm {'tayyor (' + source + ')' if image else 'yoq'}")
        try:
            audio = make_audio(draft["audio_script"], out / "audio.mp3")
            log("4-agent: audio tayyor")
        except Exception as e:  # audio bo'lmasa ham post chiqsin
            audio = None
            log(f"4-agent: audio tayyorlanmadi ({e}), post audiosiz chiqadi")
            notify_admin(f"⚠️ Audio tayyorlanmadi, post audiosiz chiqadi: {e}")

        if dry:
            log(f"DRY RUN: natijalar {out} papkasida")
            if image and source not in ("tayyorlangan", "galereya") and meta.get("plan_n"):
                ready = prepared_path(meta["plan_n"], meta["cycle"])
                ready.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(image, ready)
                log(f"Rasm keyingi haqiqiy post uchun saqlandi: {ready.name}")
            admin = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
            if admin:
                try:
                    notify_admin(f"🧪 Sinov (dry run): keyingi post ko'rinishi. Rasm manbasi: {source}, "
                                 f"audio: {'bor' if audio else 'yoq'}")
                    publish(draft["post_text"], image, audio, meta["topic"][:60], chat=admin)
                    log("Sinov posti admin chatga yuborildi")
                except Exception as e:  # noqa: BLE001
                    log(f"Admin chatga yuborilmadi: {e}")
            return
        if args.publish_at:
            wait_until(args.publish_at)
        msg_id = publish(draft["post_text"], image, audio, meta["topic"][:60])
        log(f"6-agent: chiqarildi, message_id={msg_id}")
        history["posts"].append({
            "date": datetime.now(TZ).date().isoformat(),
            **meta,
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
