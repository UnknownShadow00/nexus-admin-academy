from app.services.lesson_presentation import (
    LESSON_PRESENTATIONS,
    learner_outcomes,
    learner_summary,
    presentation_for_lesson,
)
from seed_phase_a import MODULES as MODULES_A, QUIZZES
from seed_phase_b import MODULES_B


SELECTED = {
    "Anatomy of a Good Ticket",
    "Storage: Symptoms Before Specs",
    "The Client-Side Network Triage Tree",
    "Startup Failures and Recovery Options",
    "Network Printing Without Tears",
    "Account Lifecycle Support",
    "Meet the Command Line",
}


def _lesson(title):
    for module in [*MODULES_A, *MODULES_B]:
        for lesson in module["lessons"]:
            if lesson["title"] == title:
                return lesson
    raise AssertionError(f"missing lesson {title}")


def test_selected_beginner_lessons_have_complete_presentation_contract():
    assert set(LESSON_PRESENTATIONS) == SELECTED
    for title in SELECTED:
        presentation = presentation_for_lesson(title)
        assert presentation["workplace_purpose"]
        assert len(presentation["mental_model"]) >= 4
        assert set(presentation["worked_example"]) == {
            "symptom",
            "check",
            "observation",
            "suggests",
            "does_not_prove",
            "next_check",
        }
        assert presentation["evidence_guidance"]
        assert presentation["understanding_prompt"]
        assert len(presentation["readiness"]) >= 3


def test_unknown_legacy_lesson_uses_graceful_fallback():
    assert presentation_for_lesson("An older lesson") == {}


def test_sfc_dism_lesson_question_answer_and_explanation_agree():
    lesson = _lesson("Command-Line Diagnostics")
    assert (
        "DISM /Online /Cleanup-Image /RestoreHealth then sfc /scannow"
        in lesson["summary"]
    )
    assert any("DISM → SFC" in outcome for outcome in lesson["outcomes"])

    quiz = next(
        item for item in QUIZZES if item["title"] == "Windows Command-Line Diagnostics"
    )
    question = next(
        item for item in quiz["questions"] if "repair order" in item["question_text"]
    )
    assert question["option_b"] == "Run DISM, then SFC"
    assert question["correct_answer"] == "B"
    assert "DISM repairs the component store" in question["explanation"]


def test_reviewed_network_content_does_not_claim_ping_or_apipa_proves_root_cause():
    summary = _lesson("The Client-Side Network Triage Tree")["summary"]
    assert "Fail = local network/switch port/cable" not in summary
    assert "169.254.x.x → DHCP FAILED" not in summary
    presentation = presentation_for_lesson("The Client-Side Network Triage Tree")
    assert "does not prove" in presentation["worked_example"]["does_not_prove"].lower()
    assert "ICMP may be blocked" in presentation["evidence_guidance"]


def test_existing_database_content_is_corrected_without_a_content_load():
    old = (
        "IP (169.254.x.x = DHCP failed). "
        "sfc /scannow then DISM /Online /Cleanup-Image /RestoreHealth → system file repair sequence "
        "(DISM repairs the store sfc repairs from)."
    )
    corrected = learner_summary("Command-Line Diagnostics", old)
    assert "normal DHCP configuration was not obtained" in corrected
    assert "DISM /Online /Cleanup-Image /RestoreHealth then sfc /scannow" in corrected
    assert "sfc /scannow then DISM" not in corrected
    assert learner_outcomes(
        "Command-Line Diagnostics", ["Execute the sfc → DISM repair sequence"]
    ) == ["Execute the DISM → SFC repair sequence"]


def test_learner_lesson_and_quiz_copy_does_not_leak_internal_grading_labels():
    learner_copy = []
    for module in [*MODULES_A, *MODULES_B]:
        for lesson in module["lessons"]:
            learner_copy.extend([lesson.get("summary", ""), *lesson.get("outcomes", [])])
    for quiz in QUIZZES:
        for question in quiz["questions"]:
            learner_copy.extend([question["question_text"], question.get("explanation", "")])
    combined = "\n".join(learner_copy).lower()
    for leak in ("grading anchor", "safe_fix", "root_cause"):
        assert leak not in combined
