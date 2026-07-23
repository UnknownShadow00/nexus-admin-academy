"""Finalize reviewed video quiz mappings and beginner workload.

Revision ID: 0033_finalize_training_quiz_mappings
Revises: 0032_my_training
Create Date: 2026-07-23
"""

import json

import sqlalchemy as sa
from alembic import op


revision = "0033_finalize_training_quiz_mappings"
down_revision = "0032_my_training"
branch_labels = None
depends_on = None


VIDEO_TO_QUIZ = {}


def _assign(video_ids, quiz_id):
    for video_id in video_ids:
        VIDEO_TO_QUIZ[video_id] = quiz_id


_assign([166, 168, 182], 42)
_assign([167, 176, 177], 1)
_assign(list(range(19, 21)) + list(range(30, 45)), 78)
_assign([114, 115, 116, 108, 109, 110, 111, 112, 113, 119, 120, 131], 3)
_assign([117, 118], 4)
_assign([1], 78)
_assign([2, 4], 9)
_assign([3, 5, 45, 46, 47, 48, 49, 50, 51, 52, 62, 169, 175, 180, 181], 5)
_assign([57, 58, 59, 60], 78)
_assign([125, 126, 127, 162, 163], 6)
_assign([164, 165, 133, 134, 137, 138, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 161], 8)
_assign([139], 7)
_assign([6, 7, 8, 16, 17, 18, 61, 121, 122, 123, 124], 9)
_assign([14, 15], 10)
_assign(list(range(12, 14)) + list(range(21, 30)), 12)
_assign([9, 10, 11], 13)
_assign([141, 142, 160], 14)
_assign([135, 136, 140], 15)
_assign([178, 179], 18)
_assign([170], 19)
_assign([128, 129, 130], 20)
_assign([159, 174], 48)
_assign([53, 54, 55, 56, 132], 23)
_assign([171, 172, 173], 25)

EXACT_IDS = {43, 57, 166, 168, 174}
FALLBACK_IDS = {
    3, 5, 19, 20, 45, 46, 47, 48, 49, 50, 51, 52, 62, 108, 109, 110,
    111, 112, 113, 119, 120, 125, 126, 127, 131, 167, 171, 172, 173, 181,
    182, *range(21, 30),
}

BEGINNER_REQUIRED = {
    3: {110, 114, 117, 118},
    4: {46, 47, 62, 169, 180},
    7: {137, 138, 143, 156, 157},
    8: {6, 7, 18, 61, 123},
    20: {145, 149, 153, 155, 161},
}

MAPPING_KEYS = {
    "quiz_id",
    "quiz_mapping_basis",
    "quiz_mapping_confidence",
    "quiz_mapping_evidence",
}


def _mapping_metadata(video_id):
    if video_id in EXACT_IDS:
        basis = "exact"
        confidence = "Exact"
        evidence = "Existing approved title-exact database relationship."
    elif video_id in FALLBACK_IDS:
        basis = "week_fallback"
        confidence = "Week-level fallback"
        evidence = "Reviewed weekly fallback; no narrower approved quiz exists."
    else:
        basis = "topic_group"
        confidence = "Strong topical"
        evidence = "Reviewed against quiz questions, lesson/module relationships, and video topic."
    return {
        "quiz_id": VIDEO_TO_QUIZ[video_id],
        "quiz_mapping_basis": basis,
        "quiz_mapping_confidence": confidence,
        "quiz_mapping_evidence": evidence,
    }


def _metadata_dict(value):
    if not value:
        return {}
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT a.id, a.content_ref, a.metadata_json, w.week_number "
            "FROM training_week_activities a JOIN training_weeks w ON w.id=a.training_week_id "
            "WHERE a.activity_type='video'"
        )
    ).mappings()
    for row in rows:
        video_id = int(row["content_ref"])
        if video_id not in VIDEO_TO_QUIZ:
            continue
        metadata = _metadata_dict(row["metadata_json"])
        metadata.update(_mapping_metadata(video_id))
        values = {"metadata": metadata}
        required = BEGINNER_REQUIRED.get(int(row["week_number"]))
        if required is not None:
            values["required"] = video_id in required
            statement = sa.text(
                "UPDATE training_week_activities SET metadata_json=:metadata, is_required=:required WHERE id=:id"
            ).bindparams(sa.bindparam("metadata", type_=sa.JSON()))
            bind.execute(
                statement,
                {**values, "id": row["id"]},
            )
        else:
            statement = sa.text(
                "UPDATE training_week_activities SET metadata_json=:metadata WHERE id=:id"
            ).bindparams(sa.bindparam("metadata", type_=sa.JSON()))
            bind.execute(
                statement,
                {"metadata": metadata, "id": row["id"]},
            )

    # Windows Update/Defender is retained for review in Week 3 but no longer
    # gates progression because the material is taught coherently in Week 7.
    bind.execute(
        sa.text("UPDATE training_week_activities SET is_required=:required WHERE activity_type='lesson' AND content_ref='10'"),
        {"required": False},
    )


def downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT a.id, a.content_ref, a.metadata_json, v.job_relevance "
            "FROM training_week_activities a LEFT JOIN curriculum_videos v ON CAST(a.content_ref AS INTEGER)=v.id "
            "WHERE a.activity_type='video'"
        )
    ).mappings()
    for row in rows:
        metadata = {key: value for key, value in _metadata_dict(row["metadata_json"]).items() if key not in MAPPING_KEYS}
        statement = sa.text(
            "UPDATE training_week_activities SET metadata_json=:metadata, is_required=:required WHERE id=:id"
        ).bindparams(sa.bindparam("metadata", type_=sa.JSON()))
        bind.execute(
            statement,
            {"metadata": metadata, "required": row["job_relevance"] == "job_critical", "id": row["id"]},
        )
    bind.execute(
        sa.text("UPDATE training_week_activities SET is_required=:required WHERE activity_type='lesson' AND content_ref='10'"),
        {"required": True},
    )
