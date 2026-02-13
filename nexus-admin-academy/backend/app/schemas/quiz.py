from pydantic import BaseModel, Field, HttpUrl, field_validator


class QuizGenerateRequest(BaseModel):
    source_url: HttpUrl
    week_number: int = Field(ge=1)
    title: str = Field(min_length=3, max_length=200)


class QuizQuestionOut(BaseModel):
    id: int | None = None
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str | None = None
    explanation: str | None = None


class QuizGenerateResponse(BaseModel):
    quiz_id: int
    questions: list[QuizQuestionOut]


class QuizListItem(BaseModel):
    id: int
    title: str
    week_number: int
    question_count: int


class QuizListResponse(BaseModel):
    quizzes: list[QuizListItem]


class QuizDetailResponse(BaseModel):
    id: int
    title: str
    questions: list[QuizQuestionOut]


class QuizSubmitRequest(BaseModel):
    student_id: int = Field(ge=1)
    answers: dict[str, str]

    @field_validator("answers")
    @classmethod
    def answers_must_be_abcd(cls, value: dict[str, str]) -> dict[str, str]:
        valid = {"A", "B", "C", "D"}
        for answer in value.values():
            if answer not in valid:
                raise ValueError("Quiz answers must be A/B/C/D only")
        return value


class QuizResultItem(BaseModel):
    question_id: int
    correct: bool
    correct_answer: str
    explanation: str | None = None


class QuizSubmitResponse(BaseModel):
    score: int
    total: int
    xp_awarded: int
    results: list[QuizResultItem]
