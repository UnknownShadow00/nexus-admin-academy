from app.services.question_validation import (
    QUESTION_TYPE_MULTI,
    QUESTION_TYPE_SINGLE,
    QUESTION_TYPE_TRUE_FALSE,
    validate_question,
)


def test_two_option_single_choice_is_valid():
    result = validate_question(
        {
            "question_text": "Is TCP connection-oriented?",
            "option_a": "True",
            "option_b": "False",
            "correct_answers": "A",
        }
    )
    assert result.valid
    assert result.question_type == QUESTION_TYPE_TRUE_FALSE


def test_four_option_single_choice_is_valid():
    result = validate_question(
        {
            "question_text": "What port does HTTPS use?",
            "option_a": "443",
            "option_b": "80",
            "option_c": "21",
            "option_d": "25",
            "correct_answers": "A",
        }
    )
    assert result.valid
    assert result.question_type == QUESTION_TYPE_SINGLE
    assert result.normalized_correct_answers == ["A"]


def test_select_2_multi_is_valid():
    result = validate_question(
        {
            "question_text": "Which two protocols are connectionless? (Select 2 answers)",
            "option_a": "UDP",
            "option_b": "TCP",
            "option_c": "ICMP",
            "correct_answers": "A,C",
        }
    )
    assert result.valid
    assert result.question_type == QUESTION_TYPE_MULTI


def test_select_3_multi_matches_reported_bug_question():
    result = validate_question(
        {
            "question_text": (
                "When creating a new help desk ticket, which basic information is "
                "typically required? (Select 3 answers)"
            ),
            "option_a": "User information",
            "option_b": "Expected resolution date",
            "option_c": "Device information",
            "option_d": "Escalation levels required",
            "option_e": "Problem description",
            "option_f": None,
            "option_g": None,
            "option_h": None,
            "correct_answers": "A,C,E",
        }
    )
    assert result.valid
    assert [o.label for o in result.normalized_options] == ["A", "B", "C", "D", "E"]
    assert result.normalized_correct_answers == ["A", "C", "E"]


def test_blank_options_are_dropped_and_reported_as_info():
    result = validate_question(
        {
            "question_text": "Pick one.",
            "option_a": "Yes",
            "option_b": "No",
            "option_f": "   ",
            "option_g": "",
            "correct_answers": "A",
        }
    )
    assert result.valid
    assert [o.label for o in result.normalized_options] == ["A", "B"]
    assert any("Option F is blank" in i.message for i in result.info)


def test_duplicate_option_text_is_a_warning_not_an_error():
    result = validate_question(
        {
            "question_text": "Pick one.",
            "option_a": "Router",
            "option_b": "Switch",
            "option_c": "Router",
            "option_d": "Hub",
            "correct_answers": "A",
        }
    )
    assert result.valid
    assert any("duplicate text" in w.message for w in result.warnings)


def test_invalid_answer_reference_is_rejected():
    result = validate_question(
        {
            "question_text": "Pick one.",
            "option_a": "Yes",
            "option_b": "No",
            "correct_answers": "H",
        }
    )
    assert not result.valid
    assert any("does not match a valid option" in e.message for e in result.errors)


def test_missing_answer_key_is_rejected():
    result = validate_question(
        {
            "question_text": "Pick one.",
            "option_a": "Yes",
            "option_b": "No",
        }
    )
    assert not result.valid
    assert any("No correct answer" in e.message for e in result.errors)


def test_select_n_mismatch_is_rejected():
    result = validate_question(
        {
            "question_text": "Which apply? (Select 3 answers)",
            "option_a": "A",
            "option_b": "B",
            "option_c": "C",
            "correct_answers": "A",
        }
    )
    assert not result.valid
    assert any("Select 3" in e.message and "1 correct answer" in e.message for e in result.errors)


def test_missing_question_text_is_rejected():
    result = validate_question({"option_a": "Yes", "option_b": "No", "correct_answers": "A"})
    assert not result.valid
    assert any(e.field == "question_text" for e in result.errors)


def test_unsupported_question_type_is_rejected():
    result = validate_question(
        {
            "question_text": "Pick one.",
            "option_a": "Yes",
            "option_b": "No",
            "correct_answers": "A",
            "question_type": "essay",
        }
    )
    assert not result.valid
    assert any(e.field == "question_type" for e in result.errors)


def test_multiple_correct_on_single_choice_is_rejected():
    result = validate_question(
        {
            "question_text": "Pick one.",
            "option_a": "Yes",
            "option_b": "No",
            "correct_answers": "A,B",
            "question_type": "single",
        }
    )
    assert not result.valid
    assert any("single-choice" in e.message for e in result.errors)


def test_fewer_than_two_correct_on_multi_is_rejected():
    result = validate_question(
        {
            "question_text": "Pick all that apply.",
            "option_a": "Yes",
            "option_b": "No",
            "option_c": "Maybe",
            "correct_answers": "A",
            "question_type": "multi",
        }
    )
    assert not result.valid
    assert any("at least two correct answers" in e.message for e in result.errors)


def test_duplicate_answer_keys_are_rejected():
    result = validate_question(
        {
            "question_text": "Pick all that apply. (Select 2 answers)",
            "option_a": "Yes",
            "option_b": "No",
            "option_c": "Maybe",
            "correct_answers": "A,A",
        }
    )
    assert not result.valid
    assert any("listed more than once" in e.message for e in result.errors)


def test_only_one_valid_option_is_rejected():
    result = validate_question(
        {
            "question_text": "Pick one.",
            "option_a": "Yes",
            "correct_answers": "A",
        }
    )
    assert not result.valid
    assert any("at least two valid options" in e.message for e in result.errors)


def test_no_valid_options_is_rejected():
    result = validate_question({"question_text": "Pick one.", "correct_answers": "A"})
    assert not result.valid
    assert any("no valid" in e.message for e in result.errors)


def test_missing_explanation_required_for_publishing():
    result = validate_question(
        {
            "question_text": "Pick one.",
            "option_a": "Yes",
            "option_b": "No",
            "correct_answers": "A",
        },
        require_explanation=True,
    )
    assert not result.valid
    assert any(e.field == "explanation" for e in result.errors)


def test_explanation_not_required_by_default():
    result = validate_question(
        {
            "question_text": "Pick one.",
            "option_a": "Yes",
            "option_b": "No",
            "correct_answers": "A",
        }
    )
    assert result.valid


def test_options_list_form_is_accepted():
    result = validate_question(
        {
            "question_text": "Pick one.",
            "options": ["Yes", "No", "", None],
            "correct_answers": ["A"],
        }
    )
    assert result.valid
    assert [o.label for o in result.normalized_options] == ["A", "B"]
