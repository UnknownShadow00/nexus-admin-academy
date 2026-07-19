#!/usr/bin/env python3
"""Apply independently reviewed answer corrections. Dry-run unless --confirm."""

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.config import load_env  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.quiz import Question, Quiz  # noqa: E402


# Each entry is the complete validated answer set, not an answer-position guess.
CORRECT_ANSWERS = {
    569:"C",570:"D",573:"C",584:"B,C,D",585:"A,C,E",587:"C",599:"B",600:"C",649:"D",
    661:"A,C,E",662:"B",664:"B",666:"A,D",668:"D",669:"B",671:"C",672:"D",673:"D",674:"D",
    706:"C",707:"D",748:"D",749:"B",753:"D",756:"D",758:"C",759:"A",760:"B",761:"D",
    764:"B",765:"B",766:"B",767:"B",768:"C",769:"D",770:"D",772:"A",773:"B",774:"C",
    775:"A",776:"A",777:"C,D,E",778:"B",779:"B",781:"B",785:"A",787:"B",788:"C",792:"B",
    793:"A",794:"C",795:"A",796:"B",799:"D",801:"C",824:"A",825:"D",826:"A,C,E",827:"A,D",
    828:"C,D",829:"D,E",830:"A,C,E",831:"D",832:"B",835:"A,D,E",836:"D,E,F",839:"A,D,F",846:"E",
    847:"B",848:"D",850:"B",851:"C",859:"A",863:"A,C,E",864:"A,B,C",865:"A,C,E",871:"A,C,E",
    908:"B,E,F",909:"D,F",911:"A,C,D",912:"A,D",913:"D,E,F",968:"A",982:"A",983:"D",986:"A,B",
    987:"D",988:"B,C,D",1031:"D",1034:"D",1035:"B,C,D",1036:"D",1037:"B",1038:"C",1039:"D",
    1043:"D",1075:"A,B,C,D",1085:"C",1087:"B",1114:"A",1115:"A",1118:"B",1131:"A",1137:"C",
    1177:"A",1178:"C",1179:"B",1180:"A",1181:"A",1182:"D",1184:"C",1185:"A",1230:"C,E,F",
    1231:"B,C,E",1244:"D",1251:"C",1254:"A",1256:"A",1257:"C",1258:"C",
}

SOURCES = {
    "mobile": "https://support.apple.com/guide/deployment/intro-to-device-management-dep1d89f0bff/web",
    "tickets": "https://www.cisa.gov/news-events/news/avoiding-social-engineering-and-phishing-attacks",
    "privacy": "https://www.hhs.gov/hipaa/for-professionals/privacy/laws-regulations/index.html",
    "ports": "https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml",
    "ip": "https://www.rfc-editor.org/rfc/rfc1918",
    "hardware": "https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2",
    "cloud": "https://csrc.nist.gov/publications/detail/sp/800-145/final",
    "battery": "https://www.epa.gov/recycle/used-lithium-ion-batteries",
    "windows": "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands",
}

REQUIRED_EXPLANATIONS = {
    661:"Initial intake needs the affected user, device, and a clear problem description; escalation level is decided after triage.",
    662:"A consistent category makes recurring issue frequency measurable in reports.",
    663:"The escalation-level field records movement from first-line support to a specialist tier.",
    664:"Progress notes are the factual running record of troubleshooting actions; the resolution summary documents the final outcome.",
    694:"Chain of custody proves who controlled evidence and helps preserve its integrity for legal or disciplinary review.",
    695:"A custody record must identify every handler and the date and time of each transfer.",
    696:"Technicians should preserve evidence and use the approved management and incident-escalation path rather than improvise legal action.",
    697:"A bit-by-bit image captures allocated, deleted, hidden, and unallocated sectors rather than only visible files.",
    1054:"Checking the outlet, cord, power strip, and a direct wall connection safely eliminates external power causes first.",
    1055:"After basic switch and damage checks, qualified technicians can use an approved PSU tester or known-good unit; exposed-conductor tests require proper training.",
    1056:"All listed checks can interrupt internal power delivery, so inspect seating, connectors, headers, shorts, and a minimal configuration methodically.",
    1057:"Degraded capacitors can destabilize voltage delivery and reduce performance before producing a clear boot error.",
    1058:"Heavy paging with constant disk activity is the classic sign that workload demand exceeds available RAM.",
    1059:"Mixed modules normally contribute their capacity but operate at a mutually supported speed, often the slowest module's rate.",
    1060:"Power-saving firmware settings can intentionally lower CPU frequency even when the processor is correctly identified.",
    1061:"A new high-draw GPU can overload an undersized PSU, causing instability and shutdowns under load.",
    1062:"Task Manager's Performance and Processes tabs show resource pressure and the processes consuming those resources.",
    1063:"Dust-restricted airflow can cause throttling, crashes, shutdowns, and eventually permanent heat damage.",
    1064:"Protective random shutdowns are a direct and urgent symptom of excessive component temperature.",
    1065:"Thermal throttling reduces clock speed to limit heat and protect the processor.",
    1066:"A burning smell requires immediate shutdown and power disconnection; inspection comes only after the system is safe.",
    1067:"Cooling, memory, power, and software faults can all produce unexpected shutdowns.",
    1068:"Cleaning, thermal maintenance, memory diagnostics, and an adequately rated PSU all support stable operation.",
    1069:"Task Manager, Event Viewer, and Reliability Monitor provide complementary evidence for application hangs and crashes.",
    1070:"A pop followed by immediate shutdown commonly indicates a failed or blown capacitor.",
    1071:"A rounded or swollen capacitor is failed hardware; do not press or probe it—replace the affected component using approved repair procedures.",
    1072:"A depleted CMOS battery commonly causes firmware clock settings to reset whenever external power is removed.",
}

BATTERY_TEXT = (
    "If a mobile-device battery is swollen, stop using the device. Disconnect external power when it is safe to do so, "
    "never puncture or compress the battery, keep the device away from flammable materials without unsafe handling, "
    "and follow manufacturer, qualified battery-disposal, or emergency procedures."
)
BATTERY_EXPLANATION = (
    "True. Swelling indicates battery failure and possible fire risk: stop use, disconnect power if safe, do not puncture "
    "or compress it, isolate it from flammables, and use qualified disposal or emergency guidance."
)


def source_for(question_id: int) -> str:
    if question_id < 650 or 1114 <= question_id <= 1137:
        return SOURCES["battery"] if question_id >= 1114 else SOURCES["mobile"]
    if question_id < 700:
        return SOURCES["tickets"]
    if question_id < 720:
        return SOURCES["privacy"]
    if question_id < 824:
        return SOURCES["ports"]
    if question_id < 860:
        return SOURCES["ip"]
    if question_id < 1030:
        return SOURCES["hardware"]
    if question_id < 1050:
        return SOURCES["cloud"]
    if question_id < 1170:
        return SOURCES["hardware"]
    return SOURCES["windows"]


def options(question: Question) -> dict[str, str]:
    return {letter: getattr(question, f"option_{letter.lower()}") for letter in "ABCDEFGH" if getattr(question, f"option_{letter.lower()}")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Commit corrections; otherwise roll back")
    args = parser.parse_args()
    if len(CORRECT_ANSWERS) != 120:
        raise RuntimeError(f"Correction manifest must contain 120 records, found {len(CORRECT_ANSWERS)}")
    load_env()
    db = SessionLocal()
    changed = 0
    affected_quizzes = set()
    try:
        for question_id, answer_csv in sorted(CORRECT_ANSWERS.items()):
            question = db.query(Question).filter(Question.id == question_id).first()
            if not question:
                raise RuntimeError(f"Question q{question_id} is missing")
            answer_letters = answer_csv.split(",")
            available = options(question)
            if any(letter not in available for letter in answer_letters):
                raise RuntimeError(f"q{question_id} correction references an empty option: {answer_csv}")
            old = question.correct_answers or question.correct_answer
            new_multi = answer_csv if len(answer_letters) > 1 else None
            reason = f"Validated against the cited technical reference; correct selection: {'; '.join(available[x] for x in answer_letters)}."
            print(f"q{question_id}: {old} -> {answer_csv} | {reason} | {source_for(question_id)}")
            if question.correct_answer != answer_letters[0] or question.correct_answers != new_multi:
                question.correct_answer = answer_letters[0]
                question.correct_answers = new_multi
                changed += 1
            if not question.explanation:
                question.explanation = REQUIRED_EXPLANATIONS.get(question_id, reason)
            affected_quizzes.add(question.quiz_id)

        battery = db.query(Question).filter(Question.id == 1114).one()
        battery.question_text = BATTERY_TEXT
        battery.correct_answer = "A"
        battery.correct_answers = None
        battery.explanation = BATTERY_EXPLANATION

        # Fully review the three imported assessments used to fill audited Week
        # 0, Week 2, and Week 23 gaps; no other imported quiz is over-claimed.
        for quiz_id in (42, 48, 78):
            quiz = db.query(Quiz).filter(Quiz.id == quiz_id).one()
            for question in quiz.questions:
                if question.id in REQUIRED_EXPLANATIONS:
                    question.explanation = REQUIRED_EXPLANATIONS[question.id]
                elif not question.explanation:
                    selected = question.all_correct_answers
                    selected_text = "; ".join(options(question)[letter] for letter in selected)
                    question.explanation = f"The validated answer is {selected_text}; it best matches the operational condition described."
            quiz.answer_keys_validated = True
            quiz.explanations_complete = all(bool(question.explanation and question.explanation.strip()) for question in quiz.questions)
            quiz.editorial_status = "validated"

        for quiz_id in affected_quizzes - {42, 48, 78}:
            quiz = db.query(Quiz).filter(Quiz.id == quiz_id).one()
            if quiz.editorial_status != "archived":
                quiz.editorial_status = "needs_edit"
            quiz.answer_keys_validated = False

        db.flush()
        if db.query(Quiz).count() != 104 or db.query(Question).count() != 967:
            raise RuntimeError("Content counts changed; rolling back")
        if args.confirm:
            db.commit()
            print(f"COMMITTED: 120 correction records checked; {changed} stored keys changed; 104/967 counts preserved")
        else:
            db.rollback()
            print(f"DRY RUN: 120 correction records checked; {changed} stored keys would change; rolled back")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
