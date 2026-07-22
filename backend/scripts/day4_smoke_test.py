"""Day-4 end-to-end smoke test — automated version of the manual browser checklist.

Walks the real student path against the RUNNING app (http://127.0.0.1:8000):
login → week plan → lesson done → quiz retake/XP-once → hint reveal →
ticket writeup + live AI grade → mentor flag/gate block/unblock → evidence caps.

Uses student5 (seeded test account) + admin X-Admin-Key. Read-only DB checks
via SessionLocal verify XP ledger and attempt history honestly.

Usage:
    python scripts/day4_smoke_test.py
"""
from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import load_env  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.quiz import QuizAttempt  # noqa: E402
from app.models.xp_ledger import XPLedger  # noqa: E402

load_env()

BASE = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000")
STUDENT_USER = os.getenv("SMOKE_STUDENT", "student5")
STUDENT_PASS = "nexus123"
ADMIN_KEY = (os.getenv("ADMIN_API_KEY") or os.getenv("ADMIN_SECRET_KEY") or "").strip()

QUIZ_TITLE = "Ticket Writing Fundamentals"
DNS_TICKET_MATCH = "dns"

# tiny valid 1x1 PNG
PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c626001000000ffff03000006000557bfabd40000000049454e44ae426082"
)

RESULTS: list[tuple[str, bool, str]] = []


def report(step: str, passed: bool, detail: str) -> None:
    RESULTS.append((step, passed, detail))
    print(f"[{'PASS' if passed else 'FAIL'}] {step}\n       {detail}\n")


def main() -> int:
    student = httpx.Client(base_url=BASE, timeout=180)
    admin = httpx.Client(base_url=BASE, timeout=60, headers={"X-Admin-Key": ADMIN_KEY})
    db = SessionLocal()

    # ---- 1. student login -------------------------------------------------
    r = student.post("/auth/login", json={"username": STUDENT_USER, "password": STUDENT_PASS})
    me = student.get("/auth/me")
    ok1 = r.status_code == 200 and me.status_code == 200 and me.json()["data"]["student_id"] > 0
    student_id = me.json()["data"]["student_id"] if ok1 else -1
    report("1. login", ok1, f"login={r.status_code} me={me.status_code} student_id={student_id} body={r.json()}")
    if not ok1:
        return finish()

    # ---- 2. week plan -----------------------------------------------------
    r = student.get("/api/students/me/week-plan", params={"week": 1})
    plan = r.json().get("data", {}) if r.status_code == 200 else {}
    lessons = plan.get("lessons", [])
    quizzes = plan.get("quizzes", [])
    tickets = plan.get("tickets", [])
    ok2 = r.status_code == 200 and lessons and quizzes and tickets
    report(
        "2. week-plan (week 1)",
        bool(ok2),
        f"status={r.status_code} lessons={len(lessons)} quizzes={len(quizzes)} "
        f"tickets={len(tickets)} labs={len(plan.get('labs', []))} cli_labs={len(plan.get('cli_labs', []))}",
    )
    if not ok2:
        return finish()

    # ---- 3. lesson notes flips lesson to done ------------------------------
    target_lesson = next((lesson for lesson in lessons if lesson["status"] != "done"), lessons[0])
    r = student.put(
        f"/api/lessons/{target_lesson['id']}/notes",
        json={"content": "Smoke test note: symptom vs root cause distinction, ticket structure."},
    )
    r2 = student.get("/api/students/me/week-plan", params={"week": 1})
    after = next(
        (lesson for lesson in r2.json()["data"]["lessons"] if lesson["id"] == target_lesson["id"]),
        {},
    )
    ok3 = r.status_code == 200 and after.get("status") == "done"
    report(
        "3. lesson → done",
        ok3,
        f"note_put={r.status_code} lesson={target_lesson['id']!r} \"{target_lesson['title']}\" "
        f"status_after={after.get('status')!r}",
    )

    # ---- 4. quiz retake: both attempts recorded, XP once --------------------
    quiz = next((q for q in quizzes if q["title"] == QUIZ_TITLE), None)
    ok4 = False
    if quiz is None:
        report("4. quiz retake", False, f"quiz titled {QUIZ_TITLE!r} not in week plan: {[q['title'] for q in quizzes]}")
    else:
        qd = student.get(f"/api/quizzes/{quiz['id']}").json()["data"]
        answers = {str(q["id"]): "A" for q in qd["questions"]}
        attempts_before = db.query(QuizAttempt).filter_by(student_id=student_id, quiz_id=quiz["id"]).count()
        s1 = student.post(f"/api/quizzes/{quiz['id']}/submit", json={"student_id": student_id, "answers": answers})
        s2 = student.post(f"/api/quizzes/{quiz['id']}/submit", json={"student_id": student_id, "answers": answers})
        db.expire_all()
        attempts_after = db.query(QuizAttempt).filter_by(student_id=student_id, quiz_id=quiz["id"]).count()
        attempt_ids = [
            a.id for a in db.query(QuizAttempt).filter_by(student_id=student_id, quiz_id=quiz["id"])
        ]
        # XPLedger.source_id is the ATTEMPT id for quizzes, not the quiz id
        xp_rows = (
            db.query(XPLedger)
            .filter(
                XPLedger.student_id == student_id,
                XPLedger.source_type == "quiz",
                XPLedger.source_id.in_(attempt_ids),
            )
            .all()
        )
        ok4 = (
            s1.status_code == 200
            and s2.status_code == 200
            and attempts_after - attempts_before == 2
            and len(xp_rows) <= 1
        )
        report(
            "4. quiz retake (attempts=2, XP once)",
            ok4,
            f"submit1={s1.status_code} score1={s1.json().get('data', {}).get('score')} "
            f"submit2={s2.status_code} score2={s2.json().get('data', {}).get('score')} "
            f"attempts {attempts_before}→{attempts_after} xp_ledger_rows={len(xp_rows)} "
            f"xp_amounts={[x.delta for x in xp_rows]}",
        )

    # ---- 5. DNS ticket hint: cost disclosed, values substituted -------------
    ticket = next((t for t in tickets if DNS_TICKET_MATCH in t["title"].lower()), None)
    ok5 = False
    if ticket is None:
        report("5. hint reveal", False, f"no DNS ticket in week plan: {[t['title'] for t in tickets]}")
    else:
        detail = student.get(f"/api/tickets/{ticket['id']}").json()["data"]
        pre_disclosure = detail.get("hints_total", 0) > 0  # ladder cost is fixed and shown pre-reveal
        h = student.post(f"/api/tickets/{ticket['id']}/hint")
        hd = h.json().get("data", {})
        hint_texts = hd.get("hints_revealed", [])
        no_placeholders = hint_texts and all("{{" not in t and "}}" not in t for t in hint_texts)
        ok5 = (
            h.status_code == 200
            and pre_disclosure
            and bool(no_placeholders)
            and hd.get("current_xp_multiplier") == 0.95
            and hd.get("next_hint_xp_penalty_percent") is not None
        )
        report(
            "5. hint reveal (cost before, values substituted)",
            ok5,
            f"hints_total={detail.get('hints_total')} reveal={h.status_code} "
            f"multiplier_after_1={hd.get('current_xp_multiplier')} next_cost%={hd.get('next_hint_xp_penalty_percent')} "
            f"hint1={hint_texts[0][:120] if hint_texts else None!r}",
        )

    # ---- 6. real writeup → live AI grade ------------------------------------
    submission_id = None
    ok6 = False
    if ticket is not None:
        payload = {
            "student_id": student_id,
            "symptom": "User reports no websites load; Teams stays connected, so IP connectivity is fine but name resolution fails.",
            "root_cause": "Workstation NIC has an incorrect static DNS server configured instead of the corporate DNS.",
            "resolution": "Compared ping by IP (works) vs hostname (fails), ran ipconfig /all and found the wrong static DNS entry, reset DNS to DHCP-assigned server, flushed the resolver cache. No other settings touched.",
            "verification": "nslookup resolves against the corporate DNS server and the user browsed three sites successfully; confirmed with the user before closing.",
            "commands_used": "ping 1.1.1.1; ping google.com; ipconfig /all; ipconfig /flushdns; nslookup google.com",
        }
        t0 = time.time()
        r = student.post(f"/api/tickets/{ticket['id']}/submit", json=payload)
        elapsed = time.time() - t0
        data = r.json().get("data", {}) if r.status_code == 200 else r.json()
        submission_id = data.get("submission_id")
        anchors = data.get("anchors")
        fb = data.get("feedback")
        feedback = fb.get("feedback") if isinstance(fb, dict) else fb
        score = data.get("final_score")
        ok6 = r.status_code == 200 and isinstance(anchors, dict) and bool(feedback) and isinstance(score, int) and 5 <= score <= 10
        report(
            "6. ticket submit → AI grade",
            ok6,
            f"status={r.status_code} in {elapsed:.1f}s submission_id={submission_id} final_score={score} "
            f"anchors={anchors} feedback={str(feedback)[:140]!r}",
        )

    # ---- 7. mentor flag blocks gate, resolve clears it ----------------------
    ok7 = False
    if submission_id:
        f = admin.put(f"/api/admin/submissions/{submission_id}/flag", json={"comment": "Smoke test flag: please re-check verification evidence."})
        ps_blocked = student.get(f"/api/students/{student_id}/promotion-status").json()

        def find_flag_req(obj):
            if isinstance(obj, dict):
                if obj.get("type") == "no_unresolved_flags":
                    return obj
                return next((r for v in obj.values() if (r := find_flag_req(v))), None)
            if isinstance(obj, list):
                return next((r for v in obj if (r := find_flag_req(v))), None)
            return None

        req_blocked = find_flag_req(ps_blocked)
        c = admin.put(f"/api/admin/submissions/{submission_id}/resolve-flag")
        req_cleared = find_flag_req(student.get(f"/api/students/{student_id}/promotion-status").json())
        ok7 = (
            f.status_code == 200
            and c.status_code == 200
            and req_blocked is not None and req_blocked.get("met") is False
            and req_cleared is not None and req_cleared.get("met") is True
        )
        report(
            "7. flag → gate blocked → resolve → cleared",
            ok7,
            f"flag={f.status_code} blocked_req={req_blocked} resolve={c.status_code} cleared_req={req_cleared}",
        )
    else:
        report("7. flag/gate", False, "skipped — no submission_id from step 6")

    # ---- 8. evidence upload caps --------------------------------------------
    if ticket is not None:
        big = io.BytesIO(PNG_1PX + b"\x00" * (10 * 1024 * 1024 + 1))
        r_big = student.post(
            "/api/evidence/upload",
            files={"file": ("big.png", big, "image/png")},
            data={"ticket_id": str(ticket["id"]), "artifact_type": "screenshot"},
        )
        r_ok = student.post(
            "/api/evidence/upload",
            files={"file": ("proof.png", io.BytesIO(PNG_1PX), "image/png")},
            data={"ticket_id": str(ticket["id"]), "artifact_type": "screenshot"},
        )
        ok8 = r_big.status_code == 413 and r_ok.status_code == 200
        report(
            "8. evidence upload (>10MB→413, normal→200)",
            ok8,
            f"oversize={r_big.status_code} (detail={r_big.json().get('detail')!r}) "
            f"normal={r_ok.status_code} artifact={r_ok.json().get('data', {}).get('artifact_id')} "
            f"validation={r_ok.json().get('data', {}).get('validation_status')!r}",
        )
    else:
        report("8. evidence upload", False, "skipped — no DNS ticket")

    return finish()


def finish() -> int:
    failed = [s for s, p, _ in RESULTS if not p]
    print("=" * 60)
    print(f"DAY-4 SMOKE: {len(RESULTS) - len(failed)}/{len(RESULTS)} steps passed")
    if failed:
        print("FAILED:", ", ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
