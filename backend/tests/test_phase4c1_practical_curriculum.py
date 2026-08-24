from app.services.windows_ad_server_practical import WINDOWS_AD_SERVER_CASES


def test_phase4c1_converts_exactly_nine_existing_labs_without_new_identity():
    assert set(WINDOWS_AD_SERVER_CASES) == {3, 5, 6, 7, 13, 14, 15, 16, 17}
    assert {week: case["lab_id"] for week, case in WINDOWS_AD_SERVER_CASES.items()} == {
        3: 3,
        5: 7,
        6: 8,
        7: 9,
        13: 12,
        14: 13,
        15: 5,
        16: 14,
        17: 15,
    }
    assert [case["role"] for case in WINDOWS_AD_SERVER_CASES.values()].count("practice") == 1
    assert [case["role"] for case in WINDOWS_AD_SERVER_CASES.values()].count("troubleshoot") == 7
    assert [case["role"] for case in WINDOWS_AD_SERVER_CASES.values()].count("prove") == 1


def test_every_case_requires_inspection_server_verification_and_documentation():
    for case in WINDOWS_AD_SERVER_CASES.values():
        workbench = case["workbench"]
        panel_ids = {panel["id"] for panel in workbench["panels"]}
        required = set(workbench["required_inspections"])
        terminal_ids = {
            command.get("inspection_id")
            for command in workbench.get("terminal_profile", {}).get("commands", [])
            if command.get("inspection_id")
        }
        assert required
        assert required <= panel_ids | terminal_ids
        assert workbench["documentation_required"] is True
        assert workbench["verification"]["fields"]
        assert len(case["questions"]) >= 3
        assert all(question["correct"] and question["explanation"] for question in case["questions"])
        assert "required_commands" not in workbench


def test_case_answer_positions_do_not_expose_a_first_option_pattern():
    positions = []
    for case in WINDOWS_AD_SERVER_CASES.values():
        case_positions = []
        for question in case["questions"]:
            option_ids = [option["id"] for option in question["options"]]
            position = option_ids.index(question["correct"][0])
            positions.append(position)
            case_positions.append(position)
        assert case_positions != [0] * len(case_positions)

    assert set(positions) == {0, 1, 2, 3}


def test_case_terminal_profiles_expose_faulty_incident_state_not_global_health():
    gpo = WINDOWS_AD_SERVER_CASES[15]["workbench"]["terminal_profile"]
    gpo_result = next(command for command in gpo["commands"] if command["command"] == "gpresult /r")
    assert "Denied (Security)" in "\n".join(gpo_result["output"])
    refresh = next(command for command in gpo["commands"] if command["command"] == "gpupdate /force")
    assert "remains filtered" in "\n".join(refresh["output"])

    powershell = WINDOWS_AD_SERVER_CASES[16]["workbench"]["terminal_profile"]
    dns = next(command for command in powershell["commands"] if command["command"].startswith("Resolve-DnsName"))
    dns_output = "\n".join(dns["output"])
    assert "10.20.99.10" in dns_output
    assert "timeout period expired" in dns_output
    assert "does not exist" not in dns_output

    server = WINDOWS_AD_SERVER_CASES[17]["workbench"]["terminal_profile"]
    service = next(command for command in server["commands"] if command["command"].startswith("Get-Service"))
    event = next(command for command in server["commands"] if command["command"].startswith("Get-WinEvent"))
    assert "Stopped" in "\n".join(service["output"])
    assert "password is incorrect" in "\n".join(event["output"])


def test_unsafe_security_shortcut_is_present_only_as_an_incorrect_path():
    endpoint = WINDOWS_AD_SERVER_CASES[7]
    unsafe = next(question for question in endpoint["questions"] if question["id"] == "unsafe")
    assert unsafe["correct"] == ["disable-all"]
    safe_action = next(question for question in endpoint["questions"] if question["id"] == "action")
    assert safe_action["correct"] == ["enable-scoped"]


def test_gpo_membership_fix_requires_a_fresh_user_token_before_policy_proof():
    gpo = WINDOWS_AD_SERVER_CASES[15]
    action = next(question for question in gpo["questions"] if question["id"] == "action")
    supported = next(option for option in action["options"] if option["id"] == action["correct"][0])
    verification = gpo["workbench"]["verification"]

    assert "fresh sign-in token" in supported["label"]
    assert any(
        field["label"] == "User session" and "Fresh sign-in token" in field["value"]
        for field in verification["fields"]
    )


def test_service_desk_reuse_is_non_gating_metadata_only():
    linked = {
        scenario["key"]
        for case in WINDOWS_AD_SERVER_CASES.values()
        for scenario in case["workbench"].get("reinforcement_scenarios", [])
    }
    assert linked == {"inc2408", "inc2501", "inc2505", "inc2507", "inc2509", "inc2510"}
