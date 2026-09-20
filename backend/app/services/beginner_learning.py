"""Small, stable certification boundaries for the beginner rollout.

The underlying curriculum keeps its existing week, module, activity, and
progress identities.  These constants only describe how the first part of the
path is presented and when the existing networking practice becomes visible.
"""

A_PLUS_WEEKS = tuple(range(1, 9))
NETWORK_PLUS_WEEKS = (9, 10, 11, 12)
SWITCH_LABS_UNLOCK_WEEK = 11

HYBRID_LAB_SCENARIO_KEYS = frozenset({"inc2504"})
HYBRID_LABS_ENABLED = False

# A scenario can become visible only after the student has completed the
# non-ticket learning work in its topic week. Existing passed/in-progress work
# is handled separately so rollout changes never erase learner history.
SCENARIO_TOPIC_WEEKS = {
    "locked-user-account": 1,
    "inc2404": 2,
    "inc2408": 2,
    "inc2501": 3,
    "inc2403": 5,
    "inc2502": 5,
    "inc2509": 5,
    "password-reset": 6,
    "inc2401": 6,
    "inc2405": 6,
    "inc2505": 6,
    "inc2507": 6,
    "mfa-reset": 7,
    "inc2508": 7,
    "inc2407": 8,
    "inc2503": 9,
    "inc2402": 10,
    "inc2406": 11,
    "inc2506": 12,
    "inc2510": 14,
    "m365-entra-auth-method": 26,
    "m365-signin-conditional-access": 27,
    "bitlocker-recovery": 33,
    "offboarding-device-reassignment": 34,
}


def _completed_count(states_by_week: dict[int, dict], weeks: tuple[int, ...]) -> int:
    return sum(bool(states_by_week.get(week, {}).get("is_complete")) for week in weeks)


def build_learning_phase(week_states: list[dict], current_week: int | None) -> dict:
    """Return presentation metadata derived from existing completion states."""
    states_by_week = {int(state["week_number"]): state for state in week_states}
    active_a_plus_weeks = tuple(
        week for week in A_PLUS_WEEKS if week in states_by_week
    )
    active_network_weeks = tuple(
        week for week in NETWORK_PLUS_WEEKS if week in states_by_week
    )
    a_plus_completed = _completed_count(states_by_week, active_a_plus_weeks)
    network_completed = _completed_count(states_by_week, active_network_weeks)
    a_plus_total = len(active_a_plus_weeks)
    network_total = len(active_network_weeks)
    a_plus_complete = a_plus_completed == a_plus_total
    network_plus_locked = not a_plus_complete
    network_progress = (
        round(network_completed / network_total * 100)
        if network_total
        else 100
    )
    switch_labs_unlocked = a_plus_complete and network_progress >= 50

    if current_week in NETWORK_PLUS_WEEKS and a_plus_complete:
        key = "network_plus"
        label = "CompTIA Network+"
        progress_percent = network_progress
    elif current_week in A_PLUS_WEEKS or not a_plus_complete:
        key = "aplus"
        label = "CompTIA A+"
        progress_percent = (
            round(a_plus_completed / a_plus_total * 100)
            if a_plus_total
            else 100
        )
    else:
        key = "career_path"
        label = "Career Path"
        progress_percent = 100 if network_completed == network_total else network_progress

    return {
        "key": key,
        "label": label,
        "progress_percent": progress_percent,
        "a_plus_completed_modules": a_plus_completed,
        "a_plus_total_modules": a_plus_total,
        "a_plus_complete": a_plus_complete,
        "network_plus_locked": network_plus_locked,
        "network_plus_completed_modules": network_completed,
        "network_plus_total_modules": network_total,
        "network_plus_progress_percent": network_progress,
        "switch_labs_unlocked": switch_labs_unlocked,
        "switch_labs_unlock_percent": 50,
    }
