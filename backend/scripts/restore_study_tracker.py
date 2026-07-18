#!/usr/bin/env python3
"""Transactionally restore the legacy Study Tracker dataset.

The source database is always opened read-only. Quiz and question surrogate IDs
are regenerated in the target, while stable quiz titles and video keys make the
operation conflict-detecting and idempotent.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable


QUIZ_COLUMNS = (
    "title",
    "source_url",
    "week_number",
    "created_at",
    "domain_id",
    "lesson_id",
    "source_urls",
    "question_count",
    "status",
)
QUESTION_COLUMNS = (
    "question_text",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "option_e",
    "option_f",
    "option_g",
    "option_h",
    "correct_answer",
    "explanation",
    "correct_answers",
)
CURRICULUM_COLUMNS = (
    "video_key",
    "section",
    "section_order",
    "title",
    "duration",
    "url",
    "quiz_title",
    "video_order",
    "active",
    "job_relevance",
    "exam_code",
)


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _read_only_uri(path: Path) -> str:
    return f"file:{path.resolve().as_posix()}?mode=ro"


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({_quote_identifier(table)})")}


def _require_columns(
    connection: sqlite3.Connection, table: str, required: Iterable[str], label: str
) -> None:
    missing = set(required) - _columns(connection, table)
    if missing:
        raise RuntimeError(f"{label} {table} is missing columns: {sorted(missing)}")


def _fetch_dicts(
    connection: sqlite3.Connection, sql: str, parameters: tuple[Any, ...] = ()
) -> list[dict[str, Any]]:
    cursor = connection.execute(sql, parameters)
    names = [description[0] for description in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _equivalent(left: dict[str, Any], right: dict[str, Any], columns: Iterable[str]) -> bool:
    return all(left.get(column) == right.get(column) for column in columns)


def _insert_row(
    connection: sqlite3.Connection, table: str, columns: tuple[str, ...], row: dict[str, Any]
) -> int:
    quoted_columns = ", ".join(_quote_identifier(column) for column in columns)
    placeholders = ", ".join("?" for _ in columns)
    cursor = connection.execute(
        f"INSERT INTO {_quote_identifier(table)} ({quoted_columns}) VALUES ({placeholders})",
        tuple(row.get(column) for column in columns),
    )
    return int(cursor.lastrowid)


def restore(source_path: Path, target_path: Path, dry_run: bool = False) -> dict[str, Any]:
    if not source_path.is_file():
        raise FileNotFoundError(f"source database not found: {source_path}")
    if not target_path.is_file():
        raise FileNotFoundError(f"target database not found: {target_path}")
    if source_path.resolve() == target_path.resolve():
        raise ValueError("source and target databases must be different files")

    source = sqlite3.connect(_read_only_uri(source_path), uri=True)
    target = sqlite3.connect(target_path)
    try:
        source.execute("PRAGMA query_only = ON")
        target.execute("PRAGMA foreign_keys = ON")

        for table, columns in (
            ("quizzes", QUIZ_COLUMNS),
            ("questions", ("quiz_id",) + QUESTION_COLUMNS),
            ("curriculum_videos", CURRICULUM_COLUMNS),
        ):
            _require_columns(source, table, columns, "source")
            _require_columns(target, table, columns, "target")

        source_quizzes = _fetch_dicts(
            source,
            f"SELECT id, {', '.join(QUIZ_COLUMNS)} FROM quizzes ORDER BY id",
        )
        source_questions = _fetch_dicts(
            source,
            f"SELECT id, quiz_id, {', '.join(QUESTION_COLUMNS)} "
            "FROM questions ORDER BY quiz_id, id",
        )
        source_videos = _fetch_dicts(
            source,
            f"SELECT id, {', '.join(CURRICULUM_COLUMNS)} "
            "FROM curriculum_videos ORDER BY id",
        )

        referenced_titles = {
            row["quiz_title"] for row in source_videos if row.get("quiz_title") is not None
        }
        quizzes_by_title = {row["title"]: row for row in source_quizzes}
        if len(quizzes_by_title) != len(source_quizzes):
            raise RuntimeError("source contains duplicate quiz titles")
        missing_quizzes = referenced_titles - quizzes_by_title.keys()
        if missing_quizzes:
            raise RuntimeError(
                f"source curriculum references missing quizzes: {sorted(missing_quizzes)}"
            )

        questions_by_quiz: dict[int, list[dict[str, Any]]] = {}
        for question in source_questions:
            questions_by_quiz.setdefault(question["quiz_id"], []).append(question)
        for quiz in source_quizzes:
            actual = len(questions_by_quiz.get(quiz["id"], []))
            if quiz["question_count"] != actual:
                raise RuntimeError(
                    f"source quiz {quiz['title']!r} declares {quiz['question_count']} "
                    f"questions but has {actual}"
                )

        before_fk_errors = target.execute("PRAGMA foreign_key_check").fetchall()
        result: dict[str, Any] = {
            "dry_run": dry_run,
            "source": str(source_path.resolve()),
            "target": str(target_path.resolve()),
            "curriculum_videos_inserted": 0,
            "curriculum_videos_skipped": 0,
            "quizzes_inserted": 0,
            "quizzes_skipped": 0,
            "questions_inserted": 0,
            "foreign_key_violations_before": len(before_fk_errors),
        }

        target.execute("BEGIN IMMEDIATE")
        try:
            for source_quiz in source_quizzes:
                existing = _fetch_dicts(
                    target,
                    f"SELECT id, {', '.join(QUIZ_COLUMNS)} FROM quizzes WHERE title = ?",
                    (source_quiz["title"],),
                )
                source_children = questions_by_quiz.get(source_quiz["id"], [])
                if existing:
                    if len(existing) != 1 or not _equivalent(
                        source_quiz, existing[0], QUIZ_COLUMNS
                    ):
                        raise RuntimeError(
                            f"conflicting target quiz title: {source_quiz['title']!r}"
                        )
                    target_children = _fetch_dicts(
                        target,
                        f"SELECT {', '.join(QUESTION_COLUMNS)} FROM questions "
                        "WHERE quiz_id = ? ORDER BY id",
                        (existing[0]["id"],),
                    )
                    if len(source_children) != len(target_children) or any(
                        not _equivalent(source_child, target_child, QUESTION_COLUMNS)
                        for source_child, target_child in zip(source_children, target_children)
                    ):
                        raise RuntimeError(
                            f"target quiz questions conflict: {source_quiz['title']!r}"
                        )
                    result["quizzes_skipped"] += 1
                    continue

                target_quiz_id = _insert_row(target, "quizzes", QUIZ_COLUMNS, source_quiz)
                result["quizzes_inserted"] += 1
                for source_question in source_children:
                    question = dict(source_question)
                    question["quiz_id"] = target_quiz_id
                    _insert_row(target, "questions", ("quiz_id",) + QUESTION_COLUMNS, question)
                    result["questions_inserted"] += 1

            for source_video in source_videos:
                existing = _fetch_dicts(
                    target,
                    f"SELECT {', '.join(CURRICULUM_COLUMNS)} "
                    "FROM curriculum_videos WHERE video_key = ?",
                    (source_video["video_key"],),
                )
                if existing:
                    if len(existing) != 1 or not _equivalent(
                        source_video, existing[0], CURRICULUM_COLUMNS
                    ):
                        raise RuntimeError(
                            f"conflicting target video key: {source_video['video_key']!r}"
                        )
                    result["curriculum_videos_skipped"] += 1
                    continue
                _insert_row(target, "curriculum_videos", CURRICULUM_COLUMNS, source_video)
                result["curriculum_videos_inserted"] += 1

            after_fk_errors = target.execute("PRAGMA foreign_key_check").fetchall()
            result["foreign_key_violations_after"] = len(after_fk_errors)
            if after_fk_errors != before_fk_errors:
                raise RuntimeError(
                    "import changed the target foreign-key violation set: "
                    f"before={before_fk_errors!r}, after={after_fk_errors!r}"
                )

            if dry_run:
                target.rollback()
            else:
                target.commit()
        except Exception:
            target.rollback()
            raise

        return result
    finally:
        source.close()
        target.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="read-only legacy database")
    parser.add_argument("--target", type=Path, required=True, help="database to update")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="perform every validation and insert, then roll back",
    )
    arguments = parser.parse_args()
    result = restore(arguments.source, arguments.target, arguments.dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
