import { CheckCircle, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getDueFlashcards, rateFlashcard } from "../services/api";

const RATINGS = [
  { label: "Again", value: 1, className: "border-red-200 bg-red-50 text-red-700 hover:bg-red-100 dark:border-red-900/60 dark:bg-red-950/20 dark:text-red-300 dark:hover:bg-red-950/40" },
  { label: "Hard", value: 2, className: "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 dark:border-amber-900/60 dark:bg-amber-950/20 dark:text-amber-300 dark:hover:bg-amber-950/40" },
  { label: "Good", value: 3, className: "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:border-emerald-900/60 dark:bg-emerald-950/20 dark:text-emerald-300 dark:hover:bg-emerald-950/40" },
  { label: "Easy", value: 4, className: "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 dark:border-blue-900/60 dark:bg-blue-950/20 dark:text-blue-300 dark:hover:bg-blue-950/40" },
];

function normalizeCards(response) {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.data)) return response.data;
  return [];
}

function optionEntries(card) {
  return Object.entries(card?.options || {}).filter(([, value]) => String(value || "").trim());
}

function isCorrectOption(card, key) {
  const correctAnswers = Array.isArray(card?.correct_answers) && card.correct_answers.length
    ? card.correct_answers
    : String(card?.correct_answer || "").split(",");
  return correctAnswers.map((part) => String(part).trim().toUpperCase()).includes(key);
}

function studentPickedOptions(card) {
  return String(card?.last_wrong_answer || "")
    .split(",")
    .map((part) => part.trim().toUpperCase())
    .filter(Boolean);
}

export default function FlashcardReviewPanel() {
  const [cards, setCards] = useState([]);
  const [index, setIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [loading, setLoading] = useState(true);
  const [rating, setRating] = useState(null);

  useEffect(() => {
    let active = true;

    const loadCards = async () => {
      setLoading(true);
      try {
        const response = await getDueFlashcards({ suppressToast: true });
        if (active) {
          setCards(normalizeCards(response));
          setIndex(0);
          setShowAnswer(false);
        }
      } catch {
        if (active) setCards([]);
      } finally {
        if (active) setLoading(false);
      }
    };

    loadCards();

    return () => {
      active = false;
    };
  }, []);

  const card = cards[index];
  const options = useMemo(() => optionEntries(card), [card]);
  const studentPicked = useMemo(() => studentPickedOptions(card), [card]);
  const isSessionComplete = cards.length > 0 && index >= cards.length;

  const handleRating = async (value) => {
    if (!card || rating) return;
    setRating(value);
    try {
      await rateFlashcard(card.id, value, { suppressToast: true });
      setIndex((current) => current + 1);
      setShowAnswer(false);
    } finally {
      setRating(null);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-64 items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 text-slate-500 dark:border-slate-700 dark:bg-slate-950/30 dark:text-slate-400">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" aria-hidden="true" />
        Loading review cards...
      </div>
    );
  }

  if (!cards.length) {
    return (
      <div className="flex min-h-64 flex-col items-center justify-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 text-center dark:border-emerald-900/60 dark:bg-emerald-950/20">
        <CheckCircle className="h-10 w-10 text-emerald-600 dark:text-emerald-300" aria-hidden="true" />
        <p className="text-lg font-semibold text-emerald-800 dark:text-emerald-200">All caught up for today!</p>
      </div>
    );
  }

  if (isSessionComplete) {
    return (
      <div className="flex min-h-64 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-center dark:border-slate-700 dark:bg-slate-950/30">
        <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">Session complete! Come back tomorrow.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Card {index + 1} of {cards.length}</p>

      <div className="flex min-h-72 flex-col justify-center rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-950/40">
        {!showAnswer ? (
          <div className="flex min-h-56 flex-col items-center justify-center gap-6 text-center">
            <p className="text-xl font-semibold leading-relaxed text-slate-900 dark:text-slate-100">{card.question_text || "Review question"}</p>
            <button className="btn-primary" type="button" onClick={() => setShowAnswer(true)}>
              Show Answer
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">{card.question_text || "Review question"}</p>
            {card.is_multi_select ? (
              <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">Select all that apply</p>
            ) : null}
            <div className="space-y-2">
              {options.map(([key, value]) => {
                const correct = isCorrectOption(card, key);
                const picked = studentPicked.includes(key);
                const wrong = picked && !correct;
                return (
                  <div
                    key={key}
                    className={`flex gap-3 rounded-lg border p-3 text-sm ${
                      correct
                        ? "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-100"
                        : wrong
                          ? "border-red-300 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950/30 dark:text-red-100"
                          : "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                    }`}
                  >
                    <span className="font-semibold">{key}</span>
                    <span className="flex-1">{value}</span>
                    {correct ? <span className="text-xs font-bold uppercase">Correct</span> : null}
                    {wrong ? <span className="text-xs font-bold uppercase">Your answer</span> : null}
                  </div>
                );
              })}
            </div>
            {card.explanation ? (
              <p className="rounded bg-slate-50 p-2 text-sm italic text-slate-600 dark:bg-slate-800 dark:text-slate-300">{card.explanation}</p>
            ) : null}
            {card.quiz_title ? (
              <p className="text-xs text-slate-400 dark:text-slate-500">From: {card.quiz_title}</p>
            ) : null}
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {RATINGS.map((item) => (
                <button
                  key={item.value}
                  className={`rounded-lg border px-3 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${item.className}`}
                  type="button"
                  disabled={rating !== null}
                  onClick={() => handleRating(item.value)}
                >
                  {item.label} ({item.value})
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
