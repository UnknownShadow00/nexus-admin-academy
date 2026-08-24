from app.services.network_linux_cloud_practical import NETWORK_LINUX_CLOUD_CASES


TARGET_IDENTITIES = {8: 2, 11: 10, 12: 11, 18: 16, 19: 17, 20: 18, 22: 20}


def _command(case: dict, command: str) -> dict:
    return next(
        item
        for item in case["workbench"].get("terminal_profile", {}).get("commands", [])
        if item["command"] == command
    )


def test_phase4c2_converts_exactly_seven_existing_lab_templates_in_place():
    assert {week: case["lab_id"] for week, case in NETWORK_LINUX_CLOUD_CASES.items()} == TARGET_IDENTITIES
    assert {week: case["role"] for week, case in NETWORK_LINUX_CLOUD_CASES.items()} == {
        8: "troubleshoot",
        11: "troubleshoot",
        12: "troubleshoot",
        18: "practice",
        19: "troubleshoot",
        20: "prove",
        22: "troubleshoot",
    }


def test_every_case_requires_evidence_safe_action_verification_and_documentation():
    for case in NETWORK_LINUX_CLOUD_CASES.values():
        workbench = case["workbench"]
        panel_ids = {panel["id"] for panel in workbench["panels"]}
        terminal_ids = {
            command.get("inspection_id")
            for command in workbench.get("terminal_profile", {}).get("commands", [])
            if command.get("inspection_id")
        }
        assert set(workbench["required_inspections"]) <= panel_ids | terminal_ids
        assert workbench["required_inspections"]
        assert workbench["documentation_required"] is True
        assert workbench["verification"]["fields"]
        assert len(case["questions"]) >= 3
        assert all(question["correct"] and question["explanation"] for question in case["questions"])
        assert "required_commands" not in workbench
        assert "root cause" not in case["title"].lower()


def test_guidance_fades_from_linux_fundamentals_to_production():
    week_18 = NETWORK_LINUX_CLOUD_CASES[18]["workbench"]
    week_19 = NETWORK_LINUX_CLOUD_CASES[19]["workbench"]
    week_20 = NETWORK_LINUX_CLOUD_CASES[20]["workbench"]

    assert week_18["guidance_level"] == "practice"
    assert week_18.get("guidance")
    assert week_19["guidance_level"] == "troubleshoot"
    assert "exact order" in week_19.get("guidance", "").lower()
    assert week_20["guidance_level"] == "prove"
    assert "guidance" not in week_20
    assert len(week_18["terminal_profile"]["help_topics"]) > len(week_20["terminal_profile"]["help_topics"])


def test_week_12_is_not_role_inflated_to_prove():
    case = NETWORK_LINUX_CLOUD_CASES[12]
    assert case["role"] == "troubleshoot"
    assert case["workbench"]["guidance_level"] == "troubleshoot"


def test_week_18_profile_does_not_claim_persistent_directory_state():
    commands = {item["command"] for item in NETWORK_LINUX_CLOUD_CASES[18]["workbench"]["terminal_profile"]["commands"]}
    assert "cd /var/log/nexus" not in commands
    assert "ls -ld /var/log/nexus" in commands


def test_client_network_terminal_is_incident_specific_and_layered():
    case = NETWORK_LINUX_CLOUD_CASES[8]
    profile = case["workbench"]["terminal_profile"]
    assert profile["id"] == "client-internal-resources-after-reconnect"
    assert "diagnos" not in case["workbench"]["complaint"].lower()
    assert "10.40.8.57" in "\n".join(_command(case, "ipconfig /all")["output"])
    assert "Reply from 1.1.1.1" in "\n".join(_command(case, "ping 1.1.1.1")["output"])
    assert "Non-existent domain" in "\n".join(_command(case, "nslookup intranet.nexus.internal")["output"])
    assert "10.40.8.1" in "\n".join(_command(case, "route print")["output"])
    assert any(item["command"] == "tracert intranet.nexus.internal" for item in profile["commands"])


def test_linux_profiles_are_coherent_per_case_and_never_false_healthy():
    fundamentals = NETWORK_LINUX_CLOUD_CASES[18]
    assert "permission denied" in "\n".join(_command(fundamentals, "cat /var/log/nexus/orders.log")["output"]).lower()
    assert "support" not in "\n".join(_command(fundamentals, "id samira")["output"]).split("groups=", 1)[-1]
    assert "-rw-r----- nexusapp support" in "\n".join(_command(fundamentals, "ls -l /var/log/nexus/orders.log")["output"])

    services = NETWORK_LINUX_CLOUD_CASES[19]
    assert "failed" in "\n".join(_command(services, "systemctl status nginx")["output"]).lower()
    assert "address already in use" in "\n".join(_command(services, "journalctl -u nginx -n 20")["output"]).lower()
    assert "0.0.0.0:80" in "\n".join(_command(services, "ss -lntp")["output"])

    production = NETWORK_LINUX_CLOUD_CASES[20]
    assert "100%" in "\n".join(_command(production, "df -h")["output"])
    assert "/var/log" in "\n".join(_command(production, "du -sh /var/*")["output"])
    assert "active (running)" in "\n".join(_command(production, "systemctl status nexus-web")["output"]).lower()
    assert "syntax is ok" in "\n".join(_command(production, "nginx -t")["output"])
    assert "allow" in "\n".join(_command(production, "ufw status")["output"]).lower()

    assert len({case["workbench"]["terminal_profile"]["id"] for case in (fundamentals, services, production)}) == 3


def test_unknown_commands_have_no_generic_fallback_contract():
    for week in (8, 18, 19, 20):
        profile = NETWORK_LINUX_CLOUD_CASES[week]["workbench"]["terminal_profile"]
        assert profile["unknown_command_message"] == (
            "That command is unavailable in this focused case. Use help to review tool categories."
        )
        assert all(item.get("output") for item in profile["commands"])


def test_cloud_case_separates_control_plane_guest_network_and_identity_layers():
    workbench = NETWORK_LINUX_CLOUD_CASES[22]["workbench"]
    assert workbench["domain"] == "azure"
    assert {panel["id"] for panel in workbench["panels"]} >= {"resource", "network", "health", "identity", "change"}
    labels = " ".join(field["label"] for panel in workbench["panels"] for field in panel["fields"]).lower()
    assert all(term in labels for term in ("subscription", "resource group", "region", "effective nsg", "boot diagnostics", "resource health", "role"))
    option_text = " ".join(
        option["label"]
        for question in NETWORK_LINUX_CLOUD_CASES[22]["questions"]
        for option in question["options"]
    ).lower()
    assert all(layer in option_text for layer in ("control plane", "guest os", "network", "identity"))


def test_service_desk_reuse_is_non_gating_metadata_only():
    links = {
        scenario["key"]
        for case in NETWORK_LINUX_CLOUD_CASES.values()
        for scenario in case["workbench"].get("reinforcement_scenarios", [])
    }
    assert links == {"inc2402", "inc2406", "inc2407", "inc2503", "inc2504"}


def test_week_11_reuses_existing_stateful_network_lab_without_gating_case():
    assert NETWORK_LINUX_CLOUD_CASES[11]["workbench"]["network_simulator_labs"] == [
        {
            "id": "dev-sw-act-23",
            "label": "Exam 2: Access Ports",
            "note": "Existing stateful access-port fault isolation. This optional reinforcement retains its own hints, grading, and progress.",
        }
    ]
