/**
 * Sidebar — pertanyaan umum + branding + status
 * Tailwind v4: pakai token utilities langsung
 */
const SUGGESTIONS = [
  "Berapa SKS maks per semester?",
  "Cara pengajuan cuti akademik",
  "Syarat kelulusan sarjana",
  "IPK minimal beasiswa",
  "Prosedur KRS online",
];

export default function Sidebar({ onSuggestion, onNewChat, docCount }) {
  return (
    <aside className="w-75 min-w-75 flex flex-col bg-bg-surface border-r border-border overflow-hidden">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-border">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center text-xl shrink-0"
          style={{
            background: "var(--gradient-accent)",
            boxShadow: "0 0 16px rgba(99,102,241,0.35)",
          }}
        >
          🎓
        </div>
        <div>
          <h2 className="text-[13px] font-bold text-text-primary tracking-tight">
            Pedoman Akademik
          </h2>
          <p className="text-[11px] text-text-muted">RAG · STKI System</p>
        </div>
      </div>

      {/* New chat button */}
      <div className="px-4 pt-4">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-[13px] font-medium text-indigo-300 bg-indigo-500/10 border border-indigo-400/20 hover:bg-indigo-500/18 transition-all duration-150 cursor-pointer"
        >
          <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
              clipRule="evenodd"
            />
          </svg>
          Percakapan Baru
        </button>
      </div>

      {/* Quick suggestions */}
      <div className="px-4 mt-5">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-2.5">
          Pertanyaan Umum
        </p>
        <div className="space-y-1">
          {SUGGESTIONS.map((s, i) => (
            <button
              key={i}
              onClick={() => onSuggestion(s)}
              className="w-full text-left flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[13px] text-text-secondary hover:bg-bg-hover hover:text-text-primary transition-all duration-150 group cursor-pointer"
            >
              <span className="text-text-muted group-hover:text-indigo-400 transition-colors">
                <svg
                  className="w-3.5 h-3.5"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
                    clipRule="evenodd"
                  />
                </svg>
              </span>
              <span className="truncate">{s}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Backend status */}
      <div className="px-4 py-4 border-t border-border">
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-bg-card border border-border">
          <span className="w-2 h-2 rounded-full bg-emerald-400 shrink-0 animate-glow" />
          <div>
            <p className="text-[11px] text-text-secondary font-medium">
              Backend Aktif
            </p>
            <p className="text-[10px] text-text-muted">
              {docCount !== null
                ? `${docCount.toLocaleString()} chunks terindeks`
                : "Menghubungkan..."}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
