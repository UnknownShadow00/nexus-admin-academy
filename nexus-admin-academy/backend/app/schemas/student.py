from datetime import datetime

from pydantic import BaseModel


class StudentInfo(BaseModel):
    id: int
    name: str
    total_xp: int
    level: int
    level_name: str


class RecentActivity(BaseModel):
    type: str
    title: str
    score: int
    xp: int
    timestamp: datetime


class DashboardResponse(BaseModel):
    student: StudentInfo
    recent_activity: list[RecentActivity]


class LeaderboardEntry(BaseModel):
    rank: int
    student_id: int
    name: str
    total_xp: int
    level: int


class LeaderboardResponse(BaseModel):
    leaderboard: list[LeaderboardEntry]
