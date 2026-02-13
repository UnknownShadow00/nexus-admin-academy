LEVELS = [
    (0, "Trainee"),
    (500, "Help Desk I"),
    (1000, "Help Desk II"),
    (2000, "Junior SysAdmin"),
    (3500, "SysAdmin"),
]


def quiz_xp(score: int) -> int:
    return max(score, 0) * 10


def ticket_xp(score: int) -> int:
    return max(score, 0) * 10


def level_from_xp(total_xp: int) -> tuple[int, str]:
    level = 1
    level_name = LEVELS[0][1]
    for idx, (threshold, name) in enumerate(LEVELS, start=1):
        if total_xp >= threshold:
            level = idx
            level_name = name
    return level, level_name
