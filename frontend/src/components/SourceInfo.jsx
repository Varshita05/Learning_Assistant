import { ChevronDown, FileText } from "lucide-react";

export default function SourceInfo({ sources = [] }) {
  if (!Array.isArray(sources) || sources.length === 0) return null;

  return (
    <section className="mt-6" aria-label="Answer sources">
      <div className="mb-3 flex items-center gap-2">
        <FileText className="h-3.5 w-3.5 text-zinc-500" />
        <h2 className="text-xs font-medium text-zinc-500">
          Sources
        </h2>
        <span className="text-[11px] text-zinc-700">
          {sources.length}
        </span>
      </div>

      <div className="space-y-2">
        {sources.map((source, index) => {
          const filename = source.source || `Source ${index + 1}`;

          const page =
            source.page_start != null
              ? source.page_end != null &&
                source.page_end !== source.page_start
                ? `pp. ${source.page_start}–${source.page_end}`
                : `p. ${source.page_start}`
              : "Page unavailable";

          return (
            <details
              key={`${filename}-${source.page_start ?? index}-${index}`}
              className="group overflow-hidden rounded-xl border border-white/[0.07] bg-white/[0.02]"
            >
              <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3 marker:hidden">
                <FileText className="h-4 w-4 shrink-0 text-violet-300" />

                <div className="min-w-0 flex-1">
                  <div className="truncate text-xs font-medium text-zinc-300">
                    {source.heading || "Study material"}
                  </div>

                  <div className="mt-1 truncate text-[11px] text-zinc-600">
                    {filename} · {page}
                  </div>
                </div>

                <ChevronDown className="h-4 w-4 shrink-0 text-zinc-600 transition-transform group-open:rotate-180" />
              </summary>

              {source.content && (
                <div className="border-t border-white/[0.06] px-4 py-3">
                  <p className="text-xs leading-5 text-zinc-500">
                    {source.content}
                  </p>
                </div>
              )}
            </details>
          );
        })}
      </div>
    </section>
  );
}