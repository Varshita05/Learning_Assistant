import {
  ArrowRight,
  BookOpen,
  Brain,
  FileText,
  Layers3,
  MessageSquare,
  Sparkles,
} from "lucide-react";

export default function Home({ setActivePage }) {
  return (
    <div>
      <div className="mb-10">
        <div className="mb-4 flex items-center gap-2 text-sm text-violet-300">
          <Sparkles className="h-4 w-4" />
          AI Learning Workspace
        </div>

        <h1 className="max-w-3xl text-4xl font-semibold tracking-tight md:text-5xl">
          Learn smarter from the material you already have.
        </h1>

        <p className="mt-5 max-w-2xl text-base leading-7 text-zinc-500">
          Ask questions, test yourself, revise with flashcards, and organize
          useful explanations in one workspace.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <ActionCard
          icon={MessageSquare}
          title="Ask your materials"
          description="Ask questions and receive answers grounded in your uploaded study material."
          action="Start asking"
          onClick={() => setActivePage("ask")}
        />

        <ActionCard
          icon={Brain}
          title="Take a quiz"
          description="Generate questions around a topic and test your understanding."
          action="Start quiz"
          onClick={() => setActivePage("quiz")}
        />

        <ActionCard
          icon={Layers3}
          title="Review flashcards"
          description="Use active recall to revise concepts quickly."
          action="Study cards"
          onClick={() => setActivePage("flashcards")}
        />

        <ActionCard
          icon={FileText}
          title="Your notes"
          description="Keep important explanations and study notes together."
          action="Open notes"
          onClick={() => setActivePage("notes")}
        />
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <Stat label="Documents" value="2" detail="Indexed study materials" />
        <Stat label="Learning modes" value="4" detail="Ask, Quiz, Cards, Notes" />
        <Stat label="AI pipeline" value="Ready" detail="RAG system connected" />
      </div>

      <div className="mt-6 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-6">
        <div className="flex items-start gap-4">
          <div className="rounded-xl bg-violet-500/10 p-3">
            <BookOpen className="h-5 w-5 text-violet-300" />
          </div>

          <div>
            <h2 className="text-sm font-semibold text-zinc-200">
              Study library
            </h2>
            <p className="mt-1 text-sm text-zinc-600">
              Your indexed documents are available to the RAG assistant.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ActionCard({ icon: Icon, title, description, action, onClick }) {
  return (
    <button
      onClick={onClick}
      className="group rounded-2xl border border-white/[0.07] bg-white/[0.025] p-6 text-left transition hover:-translate-y-0.5 hover:border-violet-400/20 hover:bg-violet-500/[0.04]"
    >
      <div className="flex items-start justify-between">
        <div className="rounded-xl bg-violet-500/10 p-3">
          <Icon className="h-5 w-5 text-violet-300" />
        </div>

        <ArrowRight className="h-4 w-4 text-zinc-700 transition group-hover:translate-x-1 group-hover:text-violet-300" />
      </div>

      <h2 className="mt-6 text-sm font-semibold text-zinc-100">{title}</h2>

      <p className="mt-2 max-w-md text-sm leading-6 text-zinc-600">
        {description}
      </p>

      <div className="mt-5 text-xs font-medium text-violet-300">{action}</div>
    </button>
  );
}

function Stat({ label, value, detail }) {
  return (
    <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-5">
      <div className="text-xs text-zinc-600">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
      <div className="mt-1 text-xs text-zinc-600">{detail}</div>
    </div>
  );
}