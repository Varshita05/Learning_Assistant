import { useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Layers3,
  Loader2,
  RotateCcw,
} from "lucide-react";
import { apiPost } from "../api/client";
import { getStudyItems } from "../study.js";
import SourceInfo from "../components/SourceInfo";

export default function Flashcards() {
  const [topic, setTopic] = useState("");
  const [count, setCount] = useState(5);
  const [cards, setCards] = useState(null);
  const [sources, setSources] = useState([]);
  const [current, setCurrent] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [loading, setLoading] = useState(false);

  async function generateCards() {
    if (!topic.trim()) return;

    setLoading(true);

    try {
      const data = await apiPost("/study/flashcards", {
        topic: topic.trim(),
        n: count,
        thread_id: "default_user",
      });

      setCards(getStudyItems(data));
      setSources(data.sources || []);
      setCurrent(0);
      setFlipped(false);
    } catch {
      alert("Unable to generate flashcards.");
    } finally {
      setLoading(false);
    }
  }

  if (!cards) {
    return (
      <div className="mx-auto max-w-2xl">
        <div className="mb-8">
          <div className="flex items-center gap-2 text-sm text-violet-300">
            <Layers3 className="h-4 w-4" />
            Flashcards
          </div>

          <h1 className="mt-3 text-3xl font-semibold">
            Review with active recall
          </h1>

          <p className="mt-2 text-sm text-zinc-600">
            Generate cards from a topic in your study material.
          </p>
        </div>

        <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-7">
          <label className="text-xs font-medium text-zinc-500">Topic</label>

          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Compiler Design"
            className="mt-2 w-full rounded-xl border border-white/[0.07] bg-black/20 px-4 py-3 text-sm text-zinc-200 outline-none focus:border-violet-400/30"
          />

          <label className="mt-6 block text-xs font-medium text-zinc-500">
            Number of cards
          </label>

          <div className="mt-2 grid grid-cols-4 gap-2">
            {[4, 5, 8].map((value) => (
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
            onClick={generateCards}
            disabled={!topic.trim() || loading}
            className="mt-7 flex w-full items-center justify-center gap-2 rounded-xl bg-violet-500 py-3 text-sm font-medium hover:bg-violet-400 disabled:opacity-30"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? "Generating..." : "Generate Flashcards"}
          </button>
        </div>
      </div>
    );
  }

  if (!cards.length) {
    return (
      <div className="mx-auto max-w-xl text-center">
        <h1 className="text-2xl font-semibold">No cards generated</h1>

        <button
          onClick={() => setCards(null)}
          className="mt-5 rounded-xl border border-white/[0.08] px-5 py-3 text-sm text-zinc-400"
        >
          Try another topic
        </button>
        <SourceInfo sources={sources} />
      </div>
    );
  }

  const card = cards[current];

  const question = card.front;
  const answer = card.back;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <div className="text-xs text-violet-300">Flashcards</div>
          <h1 className="mt-2 text-2xl font-semibold">{topic}</h1>
        </div>

        <div className="text-sm text-zinc-600">
          {current + 1} / {cards.length}
        </div>
      </div>

      <div
        className="group cursor-pointer [perspective:1200px]"
        onClick={() => setFlipped(!flipped)}
      >
        <div
          className={`relative min-h-[420px] w-full transition-transform duration-500 [transform-style:preserve-3d] ${
            flipped ? "[transform:rotateY(180deg)]" : ""
          }`}
        >
          <CardFace
            label="QUESTION"
            content={question}
          />

          <div className="absolute inset-0 [backface-visibility:hidden] [transform:rotateY(180deg)]">
            <div className="flex h-full min-h-[420px] flex-col justify-center rounded-3xl border border-violet-400/20 bg-violet-500/[0.05] p-10 text-center shadow-2xl shadow-violet-950/10">
              <div className="mb-5 text-[10px] font-semibold tracking-[0.2em] text-violet-300">
                ANSWER
              </div>

              <div className="text-xl leading-9 text-zinc-200">
                {answer}
              </div>

              <div className="mt-8 text-xs text-zinc-700">
                Click to flip back
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 flex items-center justify-center gap-3">
        <button
          disabled={current === 0}
          onClick={() => {
            setCurrent((value) => value - 1);
            setFlipped(false);
          }}
          className="rounded-xl border border-white/[0.07] p-3 text-zinc-500 hover:text-white disabled:opacity-20"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>

        <button
          onClick={() => setFlipped(!flipped)}
          className="rounded-xl bg-violet-500 px-6 py-3 text-sm font-medium hover:bg-violet-400"
        >
          {flipped ? "Show question" : "Reveal answer"}
        </button>

        <button
          disabled={current === cards.length - 1}
          onClick={() => {
            setCurrent((value) => value + 1);
            setFlipped(false);
          }}
          className="rounded-xl border border-white/[0.07] p-3 text-zinc-500 hover:text-white disabled:opacity-20"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <button
        onClick={() => {
          setCurrent(0);
          setFlipped(false);
        }}
        className="mx-auto mt-5 flex items-center gap-2 text-xs text-zinc-700 hover:text-zinc-400"
      >
        <RotateCcw className="h-3.5 w-3.5" />
        Restart
      </button>
      <SourceInfo sources={sources} />
    </div>
  );
}

function CardFace({ label, content }) {
  return (
    <div className="absolute inset-0 [backface-visibility:hidden]">
      <div className="flex h-full min-h-[420px] flex-col justify-center rounded-3xl border border-white/[0.08] bg-white/[0.025] p-10 text-center shadow-2xl shadow-black/20">
        <div className="mb-5 text-[10px] font-semibold tracking-[0.2em] text-zinc-600">
          {label}
        </div>

        <div className="text-2xl font-medium leading-10 text-zinc-100">
          {content}
        </div>

        <div className="mt-8 text-xs text-zinc-700">
          Click anywhere to reveal the answer
        </div>
      </div>
    </div>
  );
}