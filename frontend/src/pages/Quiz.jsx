import { useState } from "react";
import {
  Check,
  ChevronRight,
  Loader2,
  RotateCcw,
  Trophy,
  X,
} from "lucide-react";
import { apiPost } from "../api/client";
import { getStudyItems, isCorrectAnswer } from "../study.js";
import SourceInfo from "../components/SourceInfo";

export default function Quiz() {
  const [topic, setTopic] = useState("");
  const [count, setCount] = useState(5);
  const [quiz, setQuiz] = useState(null);
  const [current, setCurrent] = useState(0);
  const [selected, setSelected] = useState(null);
  const [checked, setChecked] = useState(false);
  const [score, setScore] = useState(0);
  const [loading, setLoading] = useState(false);

  async function generateQuiz() {
    if (!topic.trim()) return;

    setLoading(true);

    try {
      const data = await apiPost("/study/quiz", {
        topic: topic.trim(),
        n: count,
        thread_id: "default_user",
      });

      setQuiz({ ...data, items: getStudyItems(data) });
      setCurrent(0);
      setSelected(null);
      setChecked(false);
      setScore(0);
    } catch {
      alert("Unable to generate quiz.");
    } finally {
      setLoading(false);
    }
  }

  function checkAnswer() {
    if (selected === null || checked) return;

    const question = quiz.items[current];
    if (isCorrectAnswer(selected, question.answer_index)) {
      setScore((value) => value + 1);
    }

    setChecked(true);
  }

  function nextQuestion() {
    if (current === quiz.items.length - 1) return;

    setCurrent((value) => value + 1);
    setSelected(null);
    setChecked(false);
  }

  if (!quiz) {
    return (
      <div className="mx-auto max-w-2xl">
        <Header
          title="Quiz"
          description="Generate a quiz from your study material."
        />

        <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-7">
          <label className="text-xs font-medium text-zinc-500">Topic</label>
          <input
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder="e.g. Natural Language Processing"
            className="mt-2 w-full rounded-xl border border-white/[0.07] bg-black/20 px-4 py-3 text-sm text-zinc-200 outline-none transition focus:border-violet-400/30"
          />

          <label className="mt-6 block text-xs font-medium text-zinc-500">
            Number of questions
          </label>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {[4, 5, 6].map((value) => (
              <button
                key={value}
                onClick={() => setCount(value)}
                className={`rounded-xl border py-3 text-sm transition ${
                  count === value
                    ? "border-violet-400/30 bg-violet-500/10 text-violet-300"
                    : "border-white/[0.07] text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {value}
              </button>
            ))}
          </div>

          <button
            onClick={generateQuiz}
            disabled={!topic.trim() || loading}
            className="mt-7 flex w-full items-center justify-center gap-2 rounded-xl bg-violet-500 py-3 text-sm font-medium transition hover:bg-violet-400 disabled:opacity-30"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? "Generating..." : "Generate Quiz"}
          </button>
        </div>
      </div>
    );
  }

  if (!quiz.items.length) {
    return (
      <div className="mx-auto max-w-xl text-center">
        <h1 className="text-2xl font-semibold">No questions generated</h1>
        <button
          onClick={() => setQuiz(null)}
          className="mt-5 rounded-xl border border-white/[0.08] px-5 py-3 text-sm text-zinc-400"
        >
          Try another topic
        </button>
        <SourceInfo sources={quiz.sources} />
      </div>
    );
  }

  if (current >= quiz.items.length) {
    return (
      <div className="mx-auto max-w-xl text-center">
        <div className="flex justify-center">
          <div className="rounded-2xl bg-violet-500/10 p-5">
            <Trophy className="h-8 w-8 text-violet-300" />
          </div>
        </div>

        <h1 className="mt-6 text-3xl font-semibold">Quiz complete</h1>
        <p className="mt-3 text-sm text-zinc-600">
          You answered {score} out of {quiz.items.length} correctly.
        </p>
        <div className="my-8 text-6xl font-semibold text-violet-300">
          {Math.round((score / quiz.items.length) * 100)}%
        </div>
        <button
          onClick={() => setQuiz(null)}
          className="inline-flex items-center gap-2 rounded-xl border border-white/[0.08] px-5 py-3 text-sm text-zinc-300 hover:bg-white/[0.04]"
        >
          <RotateCcw className="h-4 w-4" />
          New quiz
        </button>
        <SourceInfo sources={quiz.sources} />
      </div>
    );
  }

  const question = quiz.items[current];
  const selectedIsCorrect = selected === question.answer_index;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <div className="text-xs text-zinc-600">Quiz</div>
          <h1 className="mt-2 text-2xl font-semibold">{topic}</h1>
        </div>
        <div className="text-sm text-zinc-600">
          {current + 1} / {quiz.items.length}
        </div>
      </div>

      <div className="mb-6 h-1 overflow-hidden rounded-full bg-white/[0.05]">
        <div
          className="h-full rounded-full bg-violet-500 transition-all"
          style={{ width: `${((current + 1) / quiz.items.length) * 100}%` }}
        />
      </div>

      <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-7">
        <h2 className="text-lg font-medium leading-8 text-zinc-100">
          {question.q}
        </h2>

        <div className="mt-7 space-y-3">
          {question.options.map((option, index) => {
            const isSelected = selected === index;
            const isCorrectOption = checked && index === question.answer_index;
            const isWrongSelection = checked && isSelected && !selectedIsCorrect;

            return (
              <button
                key={index}
                disabled={checked}
                onClick={() => setSelected(index)}
                className={`flex w-full items-center gap-4 rounded-xl border p-4 text-left text-sm transition ${
                  isCorrectOption
                    ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200"
                    : isWrongSelection
                      ? "border-red-400/30 bg-red-500/10 text-red-200"
                      : isSelected
                    ? "border-violet-400/30 bg-violet-500/10 text-violet-200"
                    : "border-white/[0.07] text-zinc-400 hover:bg-white/[0.03]"
                }`}
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/[0.05] text-xs">
                  {String.fromCharCode(65 + index)}
                </span>
                {option}
                {isCorrectOption && <Check className="ml-auto h-4 w-4 text-emerald-300" />}
                {isWrongSelection && <X className="ml-auto h-4 w-4 text-red-300" />}
                {!checked && isSelected && <Check className="ml-auto h-4 w-4 text-violet-300" />}
              </button>
            );
          })}
        </div>

        {checked && (
          <div
            role="status"
            aria-live="polite"
            className={`mt-6 rounded-xl border p-4 ${
              selectedIsCorrect
                ? "border-emerald-400/20 bg-emerald-400/[0.05]"
                : "border-red-400/20 bg-red-400/[0.05]"
            }`}
          >
            <div className={`text-sm font-medium ${selectedIsCorrect ? "text-emerald-300" : "text-red-300"}`}>
              {selectedIsCorrect
                ? "Correct!"
                : `Not quite. Correct answer: ${question.options[question.answer_index]}`}
            </div>
            <div className="mt-3 text-xs font-medium text-zinc-400">Explanation</div>
            <p className="mt-1 text-sm leading-6 text-zinc-400">{question.explain}</p>
          </div>
        )}

        <div className="mt-7 flex justify-end">
          {!checked ? (
            <button
              onClick={checkAnswer}
              disabled={selected === null}
              className="flex items-center gap-2 rounded-xl bg-violet-500 px-5 py-3 text-sm font-medium hover:bg-violet-400 disabled:opacity-30"
            >
              Check answer
              <Check className="h-4 w-4" />
            </button>
          ) : (
            <button
              onClick={nextQuestion}
              className="flex items-center gap-2 rounded-xl bg-violet-500 px-5 py-3 text-sm font-medium hover:bg-violet-400"
            >
              {current === quiz.items.length - 1 ? "Finish" : "Next question"}
              <ChevronRight className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
      <SourceInfo sources={quiz.sources} />
    </div>
  );
}

function Header({ title, description }) {
  return (
    <div className="mb-8">
      <div className="text-xs text-violet-300">Study mode</div>
      <h1 className="mt-2 text-3xl font-semibold">{title}</h1>
      <p className="mt-2 text-sm text-zinc-600">{description}</p>
    </div>
  );
}