import { useState } from "react";
import {
  Bot,
  Copy,
  Loader2,
  MessageSquare,
  Send,
  User,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

import { apiPost } from "../api/client";
import SourceInfo from "../components/SourceInfo";

export default function Ask() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  async function sendMessage() {
    const question = input.trim();

    if (!question || loading) return;

    setInput("");

    setMessages((prev) => [
      ...prev,
      { role: "user", content: question },
    ]);

    setLoading(true);

    try {
      const data = await apiPost("/query", {
        query: question,
        thread_id: "default_user",
      });

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources || [],
          steps: data.steps || [],
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Something went wrong while processing your question.",
          error: error.message,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col">
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm text-violet-300">
          <MessageSquare className="h-4 w-4" />
          Ask
        </div>

        <h1 className="mt-3 text-3xl font-semibold">Ask your materials</h1>

        <p className="mt-2 text-sm text-zinc-600">
          Get answers grounded in your indexed study documents.
        </p>
      </div>

      {messages.length === 0 && (
        <div className="mb-8 grid gap-3 md:grid-cols-2">
          {[
            "What is natural language processing?",
            "Explain the main concepts from this material.",
            "Summarize the important topics.",
            "What should I revise from this chapter?",
          ].map((question) => (
            <button
              key={question}
              onClick={() => setInput(question)}
              className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-4 text-left text-sm text-zinc-500 transition hover:border-violet-400/20 hover:text-zinc-300"
            >
              {question}
            </button>
          ))}
        </div>
      )}

      <div className="space-y-6 pb-32">
        {messages.map((message, index) => (
          <Message key={index} message={message} />
        ))}

        {loading && (
          <div className="flex gap-3">
            <Avatar assistant />
            <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] px-5 py-4">
              <div className="flex items-center gap-2 text-sm text-zinc-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Searching your materials...
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="fixed bottom-6 left-[calc(50%+125px)] w-[min(800px,calc(100%-320px))] -translate-x-1/2">
        <div className="rounded-2xl border border-white/[0.10] bg-[#101117]/95 p-2 shadow-2xl shadow-black/30 backdrop-blur-xl">
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your study material..."
              rows={1}
              className="max-h-32 min-h-12 flex-1 resize-none bg-transparent px-3 py-3 text-sm text-zinc-200 outline-none placeholder:text-zinc-700"
            />

            <button
              onClick={sendMessage}
              disabled={!input.trim() || loading}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-500 text-white transition hover:bg-violet-400 disabled:cursor-not-allowed disabled:opacity-30"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Avatar({ assistant }) {
  return (
    <div
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
        assistant ? "bg-violet-500/10" : "bg-white/[0.05]"
      }`}
    >
      {assistant ? (
        <Bot className="h-4 w-4 text-violet-300" />
      ) : (
        <User className="h-4 w-4 text-zinc-400" />
      )}
    </div>
  );
}

function Message({ message }) {
  const assistant = message.role === "assistant";

  return (
    <div className="flex gap-3">
      <Avatar assistant={assistant} />

      <div className="min-w-0 flex-1">
        <div className="mb-2 text-xs font-medium text-zinc-600">
          {assistant ? "Learning Assistant" : "You"}
        </div>

        {assistant ? (
          <div className="answer-content text-sm leading-7 text-zinc-300">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeKatex]}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        ) : (
          <div className="whitespace-pre-wrap text-sm leading-7 text-zinc-300">
            {message.content}
          </div>
        )}

        {assistant && <SourceInfo sources={message.sources} />}

        {assistant && (
          <button
            onClick={() => navigator.clipboard.writeText(message.content)}
            className="mt-4 flex items-center gap-2 text-xs text-zinc-700 transition hover:text-zinc-400"
          >
            <Copy className="h-3.5 w-3.5" />
            Copy answer
          </button>
        )}
      </div>
    </div>
  );
}