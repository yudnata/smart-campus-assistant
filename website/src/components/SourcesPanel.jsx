import { useState } from "react";

/**
 * SourcesPanel — Tampilkan chunks hasil retrieval pgvector
 * Tailwind v4: pakai token utilities langsung
 */
export default function SourcesPanel({ sources, stats }) {
  const [open, setOpen] = useState(false);

  if (!sources?.length) return null;

  const badge = (sim) => {
    if (sim >= 0.85)
      return {
        label: `${(sim * 100).toFixed(0)}% — Sangat Relevan`,
        cls: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/25",
      };
    if (sim >= 0.65)
      return {
        label: `${(sim * 100).toFixed(0)}% — Relevan`,
        cls: "bg-indigo-500/10 text-indigo-300 border border-indigo-400/25",
      };
    return {
      label: `${(sim * 100).toFixed(0)}% — Cukup Relevan`,
      cls: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
    };
  };

  return (
    <div className="mt-2 space-y-2">
      {/* Retrieval stats — STKI evaluation metrics */}
      {stats && (
        <div className="flex items-center gap-3 px-3 py-1.5 rounded-lg bg-bg-surface border border-border text-[11px] text-text-muted">
          <span>
            ⏱{" "}
            <strong className="text-indigo-400">
              {stats.retrievalTimeMs}ms
            </strong>
          </span>
          <span className="text-border">|</span>
          <span>
            📄 <strong className="text-indigo-400">{stats.chunksFound}</strong>{" "}
            chunks
          </span>
          <span className="text-border">|</span>
          <span>
            🎯 top:{" "}
            <strong className="text-indigo-400">
              {(stats.topSimilarity * 100).toFixed(0)}%
            </strong>
          </span>
        </div>
      )}

      {/* Toggle button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[12px] font-medium text-indigo-300 bg-indigo-500/10 border border-indigo-400/20 hover:bg-indigo-500/18 transition-all duration-150 cursor-pointer"
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
          <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" />
        </svg>
        {sources.length} sumber referensi
        <svg
          className={`w-3.5 h-3.5 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {/* Source cards */}
      {open && (
        <div className="space-y-2 animate-fade-up max-w-140">
          {sources.map((src, i) => {
            const b = badge(src.similarity);
            return (
              <div
                key={i}
                className="rounded-xl border border-border bg-bg-base p-3"
              >
                <div className="flex items-center gap-2 mb-2">
                  {/* Index badge */}
                  <span className="w-5 h-5 rounded-full bg-indigo-500/15 text-indigo-300 text-[10px] font-bold flex items-center justify-center shrink-0">
                    {i + 1}
                  </span>
                  {/* Page number */}
                  <span className="flex items-center gap-1 text-[11px] text-text-secondary font-medium">
                    <svg
                      className="w-3 h-3"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                        clipRule="evenodd"
                      />
                    </svg>
                    Halaman {src.page}
                  </span>
                  {/* Similarity badge */}
                  <span
                    className={`ml-auto text-[10px] font-semibold px-2 py-0.5 rounded-full ${b.cls}`}
                  >
                    {b.label}
                  </span>
                </div>
                {/* Preview */}
                <p className="text-[12px] text-text-muted leading-relaxed line-clamp-2">
                  {src.preview}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
