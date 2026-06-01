import { useRef, useEffect } from "react";

/**
 * ChatInput — textarea auto-resize + send button
 * Tailwind v4: pakai token utilities (bg-bg-card, border-border, dll)
 */
export default function ChatInput({ value, onChange, onSend, disabled }) {
  const textareaRef = useRef(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }, [value]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const canSend = value.trim().length > 0 && !disabled;

  return (
    <div className="border-t border-border bg-bg-base px-6 py-4 pb-5 shrink-0">
      <div className="max-w-190 mx-auto">
        {/* Input wrapper */}
        <div
          className={[
            "flex items-end gap-3 rounded-2xl px-4 py-2.5",
            "bg-bg-card border transition-all duration-200",
            disabled
              ? "border-border opacity-60"
              : "border-border focus-within:border-indigo-500 focus-within:shadow-[0_0_0_3px_rgba(99,102,241,0.2)]",
          ].join(" ")}
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={
              disabled
                ? "Mencari jawaban..."
                : "Tanyakan tentang pedoman akademik... (Enter untuk kirim)"
            }
            rows={1}
            className="flex-1 bg-transparent border-none outline-none resize-none text-text-primary text-[14.5px] leading-relaxed placeholder:text-text-muted min-h-6 max-h-40 overflow-y-auto"
            style={{ fontFamily: "inherit" }}
          />

          {/* Send button */}
          <button
            onClick={onSend}
            disabled={!canSend}
            className={[
              "w-9 h-9 rounded-xl flex items-center justify-center shrink-0",
              "transition-all duration-200",
              canSend
                ? "bg-gradient-accent text-white shadow-[0_4px_14px_rgba(99,102,241,0.4)] hover:scale-105 hover:shadow-[0_6px_20px_rgba(99,102,241,0.5)] cursor-pointer"
                : "bg-bg-hover text-text-muted cursor-not-allowed",
            ].join(" ")}
          >
            {disabled ? (
              <svg
                className="w-4 h-4 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            ) : (
              <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
              </svg>
            )}
          </button>
        </div>

        {/* Hint */}
        <p className="text-center text-[11px] text-text-muted mt-2.5">
          Jawaban didasarkan pada pedoman akademik yang sudah diupload ·
          Shift+Enter untuk baris baru
        </p>
      </div>
    </div>
  );
}
