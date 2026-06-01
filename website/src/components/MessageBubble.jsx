import SourcesPanel from "./SourcesPanel";

/**
 * MessageBubble — satu pesan (user | assistant | loading | error)
 * Tailwind v4: pakai token utilities langsung
 */
export default function MessageBubble({ message }) {
  const { role, content, sources, stats, status } = message;
  const isUser = role === "user";

  /* ── Loading ── */
  if (status === "loading") {
    return (
      <div className="flex flex-col items-start gap-1 animate-fade-up">
        <span className="text-[11px] font-medium text-text-muted px-1">
          🎓 Asisten Akademik
        </span>
        <div className="rounded-tl-sm rounded-tr-2xl rounded-br-2xl rounded-bl-2xl border border-border bg-bg-card px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 dot-1" />
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 dot-2" />
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 dot-3" />
            <span className="ml-2 text-[12px] italic text-text-muted">
              Mencari di pedoman akademik...
            </span>
          </div>
        </div>
      </div>
    );
  }

  /* ── Error ── */
  if (status === "error") {
    return (
      <div className="flex flex-col items-start gap-1 animate-fade-up">
        <span className="text-[11px] font-medium text-text-muted px-1">
          🎓 Asisten Akademik
        </span>
        <div className="rounded-tl-sm rounded-tr-2xl rounded-br-2xl rounded-bl-2xl bg-red-500/10 border border-red-500/25 px-4 py-3 text-red-400 text-sm max-w-[82%]">
          ⚠️ {content}
        </div>
      </div>
    );
  }

  /* ── User bubble ── */
  if (isUser) {
    return (
      <div className="flex flex-col items-end gap-1 animate-fade-up">
        <span className="text-[11px] font-medium text-text-muted px-1">
          Kamu
        </span>
        <div
          className="rounded-tl-2xl rounded-tr-2xl rounded-bl-2xl rounded-br-sm px-4 py-3 text-white text-[14.5px] leading-relaxed max-w-[82%] whitespace-pre-wrap"
          style={{
            background: "var(--gradient-user)",
            boxShadow: "0 4px 18px rgba(79,70,229,0.35)",
          }}
        >
          {content}
        </div>
      </div>
    );
  }

  /* ── Assistant bubble ── */
  return (
    <div className="flex flex-col items-start gap-1 animate-fade-up">
      <span className="text-[11px] font-medium text-text-muted px-1">
        🎓 Asisten Akademik
      </span>
      <div className="rounded-tl-sm rounded-tr-2xl rounded-br-2xl rounded-bl-2xl border border-border bg-bg-card px-4 py-3 text-text-primary text-[14.5px] leading-relaxed max-w-[88%] whitespace-pre-wrap">
        {content}
      </div>
      {sources?.length > 0 && <SourcesPanel sources={sources} stats={stats} />}
    </div>
  );
}
