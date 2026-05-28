## Task: Quiz Timer + Speed Flagging

### Goal
Track how many seconds each question takes during a quiz attempt and flag attempts where the average is under 8 seconds per question. Store timing data on the backend and show a speed-flag badge in the admin quiz editor.

---

### Backend

#### 1. Add column to QuizAttempt model
File: backend/app/models/quiz.py

Add to QuizAttempt class after the completed_at column:
  time_per_question: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

This stores a dict like {"1": 12, "2": 5, "3": 8} mapping question_id (string) -> seconds taken.

#### 2. New Alembic migration
Run from backend/ directory:
  alembic revision --autogenerate -m "add_quiz_attempt_timing"
Verify the generated file adds time_per_question to quiz_attempts. Then run: alembic upgrade head

#### 3. Update QuizSubmitRequest schema
File: backend/app/schemas/quiz.py

Add optional field to QuizSubmitRequest:
  time_per_question: dict[str, int] | None = Field(default=None)

#### 4. Update submit endpoint
File: backend/app/routers/quizzes.py

In submit_quiz:
- Read payload.time_per_question (may be None)
- Compute avg_seconds: if time_per_question has entries, avg = sum(values) / len(values), else None
- When creating QuizAttempt (is_first_attempt branch), set time_per_question=payload.time_per_question
- When updating existing attempt (retake branch), also update: existing.time_per_question = payload.time_per_question

In the return dict, add:
  "avg_seconds_per_question": round(avg_seconds, 1) if avg_seconds is not None else None,
  "is_speed_flagged": avg_seconds is not None and avg_seconds < 8,

#### 5. Update review endpoint
File: backend/app/routers/quizzes.py

In get_quiz_review, compute avg_seconds from attempt.time_per_question if present and include in the response:
  "avg_seconds_per_question": ...,
  "is_speed_flagged": ...,

#### 6. Add admin endpoint for flagged attempts
File: backend/app/routers/admin_content.py

Add imports at top:
  from app.models.quiz import Quiz, QuizAttempt
  from app.models.student import Student

Add new route after the existing routes:
  @router.get("/quiz-attempts/flagged")
  def get_flagged_attempts(db: Session = Depends(get_db)):
      attempts = db.query(QuizAttempt).filter(QuizAttempt.time_per_question.isnot(None)).all()
      result = []
      for a in attempts:
          tpq = a.time_per_question or {}
          if not tpq:
              continue
          avg = sum(tpq.values()) / len(tpq)
          if avg >= 8:
              continue
          student = db.query(Student).filter(Student.id == a.student_id).first()
          quiz = db.query(Quiz).filter(Quiz.id == a.quiz_id).first()
          result.append({
              "attempt_id": a.id,
              "student_id": a.student_id,
              "student_name": student.full_name if student else "Unknown",
              "quiz_id": a.quiz_id,
              "quiz_title": quiz.title if quiz else "Unknown",
              "score": a.score,
              "avg_seconds_per_question": round(avg, 1),
              "completed_at": a.completed_at.isoformat() if a.completed_at else None,
          })
      result.sort(key=lambda x: x["avg_seconds_per_question"])
      return ok(result, total=len(result), page=1, per_page=len(result) or 1)

#### 7. Verify backend compiles
Run: python -m py_compile backend/app/models/quiz.py backend/app/routers/quizzes.py backend/app/routers/admin_content.py backend/app/schemas/quiz.py

---

### Frontend

#### 8. Update QuizTaker.jsx to track timing
File: frontend/src/components/QuizTaker.jsx

Add useRef to the React import. Add new state and ref after existing state declarations:
  const [timings, setTimings] = useState({});
  const questionStartRef = useRef(Date.now());

Add useEffect that resets the timer when currentIndex changes:
  useEffect(() => {
    questionStartRef.current = Date.now();
  }, [currentIndex]);

In onSubmit, compute final timings before building submittableAnswers (to capture the last question time without relying on async state update):
  const lastElapsed = Math.round((Date.now() - questionStartRef.current) / 1000);
  const finalTimings = shuffledQ
    ? { ...timings, [String(shuffledQ.id)]: (timings[String(shuffledQ.id)] || 0) + lastElapsed }
    : { ...timings };

When calling submitQuiz, add time_per_question to the payload:
  const res = await submitQuiz(quizId, {
    student_id: studentId,
    answers: submittableAnswers,
    time_per_question: finalTimings,
  });

For navigation buttons, record elapsed time for the current question before navigating.
Change Next button onClick to:
  () => {
    const elapsed = Math.round((Date.now() - questionStartRef.current) / 1000);
    setTimings((prev) => ({ ...prev, [String(shuffledQ.id)]: (prev[String(shuffledQ.id)] || 0) + elapsed }));
    setCurrentIndex((i) => i + 1);
  }

Change Previous button onClick to:
  () => {
    const elapsed = Math.round((Date.now() - questionStartRef.current) / 1000);
    setTimings((prev) => ({ ...prev, [String(shuffledQ.id)]: (prev[String(shuffledQ.id)] || 0) + elapsed }));
    setCurrentIndex((i) => i - 1);
  }

Change jump grid button onClick to:
  () => {
    const elapsed = Math.round((Date.now() - questionStartRef.current) / 1000);
    setTimings((prev) => ({ ...prev, [String(shuffledQ.id)]: (prev[String(shuffledQ.id)] || 0) + elapsed }));
    setCurrentIndex(idx);
  }

#### 9. Add API helper
File: frontend/src/services/api.js

Add at the end of the file:
  export const getAdminFlaggedAttempts = (requestOptions) => request(() => api.get("/api/admin/quiz-attempts/flagged"), requestOptions);

#### 10. Add speed flag section in admin QuizEditorPage
File: frontend/src/pages/admin/QuizEditorPage.jsx

Add import at the top: import { getAdminFlaggedAttempts } from "../../services/api";

Add state near the top of the component: const [flaggedAttempts, setFlaggedAttempts] = useState([]);

In the existing useEffect that loads quiz data, add a call to fetch flagged attempts after loading the quiz:
  getAdminFlaggedAttempts({ suppressToast: true })
    .then((res) => {
      const data = Array.isArray(res?.data) ? res.data : (Array.isArray(res) ? res : []);
      setFlaggedAttempts(data.filter((a) => a.quiz_id === Number(quizId)));
    })
    .catch(() => {});

At the bottom of the returned JSX (before the final closing tag of the component return), add:
  {flaggedAttempts.length > 0 && (
    <section className="mt-8">
      <h2 className="mb-3 text-base font-semibold text-slate-800 dark:text-slate-200">Speed-Flagged Attempts</h2>
      <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 dark:bg-slate-800">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-slate-600 dark:text-slate-300">Student</th>
              <th className="px-4 py-2 text-left font-medium text-slate-600 dark:text-slate-300">Score</th>
              <th className="px-4 py-2 text-left font-medium text-slate-600 dark:text-slate-300">Avg Time/Q</th>
              <th className="px-4 py-2 text-left font-medium text-slate-600 dark:text-slate-300">Date</th>
            </tr>
          </thead>
          <tbody>
            {flaggedAttempts.map((a) => (
              <tr key={a.attempt_id} className="border-t border-slate-100 dark:border-slate-700">
                <td className="px-4 py-2 text-slate-800 dark:text-slate-200">{a.student_name}</td>
                <td className="px-4 py-2 text-slate-800 dark:text-slate-200">{a.score}</td>
                <td className="px-4 py-2">
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
                    {a.avg_seconds_per_question}s avg
                  </span>
                </td>
                <td className="px-4 py-2 text-slate-500 dark:text-slate-400">
                  {a.completed_at ? new Date(a.completed_at).toLocaleDateString() : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )}

#### 11. Build verification
Run from the project root: cd frontend && npm run build

If build fails with "spawn EPERM" that is a known Windows sandbox limitation -- note it and stop.

---

### Acceptance Criteria
- backend/app/models/quiz.py has time_per_question JSON column on QuizAttempt
- Alembic migration created and applied successfully
- QuizSubmitRequest accepts optional time_per_question field
- Submit endpoint stores timing, computes avg, returns is_speed_flagged in response
- GET /api/admin/quiz-attempts/flagged returns attempts with avg < 8s
- QuizTaker.jsx tracks per-question time and submits it
- QuizEditorPage.jsx shows speed-flagged attempts table for current quiz
- api.js has getAdminFlaggedAttempts export
- python -m py_compile passes on all changed backend files
- npm run build passes (or note EPERM)

After completing all changes, append to tasks/loop-log.md:
## [2026-05-17] Quiz timer + speed flagging
- Task: Track seconds per question, flag avg < 8s in admin view
- Files changed: backend/app/models/quiz.py, backend/app/routers/quizzes.py, backend/app/routers/admin_content.py, backend/app/schemas/quiz.py, alembic migration, frontend/src/components/QuizTaker.jsx, frontend/src/pages/admin/QuizEditorPage.jsx, frontend/src/services/api.js
- Result: pass
- Next: P3 Proxmox VM integration
