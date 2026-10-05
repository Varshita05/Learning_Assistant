import { useEffect, useState } from "react";
import { FileText, Plus, Save, Trash2, X } from "lucide-react";

const STORAGE_KEY = "learning-assistant-notes";

export default function Notes() {
  const [notes, setNotes] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    } catch {
      return [];
    }
  });

  const [selected, setSelected] = useState(null);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notes));
  }, [notes]);

  function createNote() {
    const note = {
      id: Date.now(),
      title: "Untitled note",
      content: "",
      created: new Date().toLocaleDateString(),
    };

    setNotes((prev) => [note, ...prev]);
    setSelected(note);
    setEditing(true);
  }

  function updateNote(field, value) {
    setNotes((prev) =>
      prev.map((note) =>
        note.id === selected.id ? { ...note, [field]: value } : note
      )
    );

    setSelected((prev) => ({ ...prev, [field]: value }));
  }

  function deleteNote(id) {
    setNotes((prev) => prev.filter((note) => note.id !== id));

    if (selected?.id === id) {
      setSelected(null);
      setEditing(false);
    }
  }

  return (
    <div>
      <div className="mb-8 flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-violet-300">
            <FileText className="h-4 w-4" />
            Notes
          </div>

          <h1 className="mt-3 text-3xl font-semibold">Your notes</h1>

          <p className="mt-2 text-sm text-zinc-600">
            Keep useful explanations and study notes in one place.
          </p>
        </div>

        <button
          onClick={createNote}
          className="flex items-center gap-2 rounded-xl bg-violet-500 px-4 py-2.5 text-sm font-medium hover:bg-violet-400"
        >
          <Plus className="h-4 w-4" />
          New note
        </button>
      </div>

      <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
        <div className="space-y-2">
          {notes.length === 0 && (
            <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-6 text-center text-xs text-zinc-700">
              No notes yet.
            </div>
          )}

          {notes.map((note) => (
            <button
              key={note.id}
              onClick={() => {
                setSelected(note);
                setEditing(false);
              }}
              className={`w-full rounded-xl border p-4 text-left transition ${
                selected?.id === note.id
                  ? "border-violet-400/20 bg-violet-500/[0.05]"
                  : "border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]"
              }`}
            >
              <div className="truncate text-sm font-medium text-zinc-300">
                {note.title || "Untitled note"}
              </div>

              <div className="mt-1 text-xs text-zinc-700">
                {note.created}
              </div>
            </button>
          ))}
        </div>

        <div className="min-h-[500px] rounded-2xl border border-white/[0.07] bg-white/[0.025]">
          {!selected ? (
            <div className="flex h-full min-h-[500px] flex-col items-center justify-center text-center">
              <div className="rounded-xl bg-white/[0.04] p-4">
                <FileText className="h-5 w-5 text-zinc-600" />
              </div>

              <p className="mt-4 text-sm text-zinc-600">
                Select a note or create a new one.
              </p>
            </div>
          ) : (
            <div className="p-7">
              <div className="flex items-center justify-between">
                {editing ? (
                  <input
                    value={selected.title}
                    onChange={(e) =>
                      updateNote("title", e.target.value)
                    }
                    className="flex-1 bg-transparent text-xl font-semibold text-zinc-100 outline-none"
                  />
                ) : (
                  <h2 className="text-xl font-semibold text-zinc-100">
                    {selected.title}
                  </h2>
                )}

                <div className="flex gap-2">
                  <button
                    onClick={() => setEditing(!editing)}
                    className="rounded-lg p-2 text-zinc-600 hover:bg-white/[0.04] hover:text-zinc-300"
                  >
                    {editing ? (
                      <X className="h-4 w-4" />
                    ) : (
                      <Save className="h-4 w-4" />
                    )}
                  </button>

                  <button
                    onClick={() => deleteNote(selected.id)}
                    className="rounded-lg p-2 text-zinc-600 hover:bg-red-400/10 hover:text-red-300"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {editing ? (
                <textarea
                  value={selected.content}
                  onChange={(e) =>
                    updateNote("content", e.target.value)
                  }
                  placeholder="Start writing..."
                  className="mt-8 min-h-[380px] w-full resize-none bg-transparent text-sm leading-7 text-zinc-300 outline-none placeholder:text-zinc-700"
                  autoFocus
                />
              ) : (
                <div className="mt-8 whitespace-pre-wrap text-sm leading-7 text-zinc-400">
                  {selected.content || "This note is empty."}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}