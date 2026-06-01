import { useState, useRef, useEffect, useCallback } from "react";
import "./App.css";
import Sidebar from "./components/Sidebar";
import MessageBubble from "./components/MessageBubble";
import ChatInput from "./components/ChatInput";

const API_CHAT = "http://localhost:3001/api/chat";
const API_STATS = "http://localhost:3001/api/stats";

/* ── Empty State ─────────────────────────────────────────── */
function EmptyState({ onSuggestion }) {
  const chips = [
    "Berapa SKS maksimal per semester?",
    "Bagaimana cara pengajuan cuti akademik?",
    "Apa syarat kelulusan sarjana?",
    "Berapa IPK minimal untuk beasiswa?",
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full gap-5 px-8 text-center animate-fade-up">
      <div
        className="w-20 h-20 rounded-2xl flex items-center justify-center text-4xl"
        style={{
          background: "var(--gradient-accent)",
          boxShadow: "0 8px 32px rgba(99,102,241,0.4)",
        }}
      >
        📚
      </div>
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-text-primary tracking-tight">
          Chatbot Pedoman Akademik
        </h1>
        <p className="text-text-muted text-[14px] max-w-sm leading-relaxed">
          Tanyakan apa saja tentang aturan dan prosedur akademik kampus. Jawaban
          diambil langsung dari pedoman resmi.
        </p>
      </div>
      <div className="flex flex-wrap gap-2 justify-center max-w-lg mt-2">
        {chips.map((c, i) => (
          <button
            key={i}
            onClick={() => onSuggestion(c)}
            className="px-4 py-2 rounded-full text-[13px] text-text-secondary bg-bg-card border border-border hover:border-indigo-500/50 hover:text-indigo-300 hover:bg-indigo-500/8 transition-all duration-150 cursor-pointer"
          >
            {c}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ── App Root ────────────────────────────────────────────── */
export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [docCount, setDocCount] = useState(null);
  const bottomRef = useRef(null);

  /* Fetch stats untuk sidebar status */
  useEffect(() => {
    fetch(API_STATS)
      .then((r) => r.json())
      .then((d) => setDocCount(d.totalChunks))
      .catch(() => setDocCount(null));
  }, []);

  /* Auto-scroll ke bawah saat pesan baru */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /* Kirim pertanyaan ke RAG backend */
  const sendMessage = useCallback(
    async (question) => {
      const q = (question ?? input).trim();
      if (!q || loading) return;

      setInput("");
      setLoading(true);

      const userMsg = { id: Date.now(), role: "user", content: q };
      const loadMsg = {
        id: Date.now() + 1,
        role: "assistant",
        status: "loading",
        content: "",
      };
      setMessages((prev) => [...prev, userMsg, loadMsg]);

      try {
        const res = await fetch(API_CHAT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: q, topK: 5 }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Server error");

        const aiMsg = {
          id: Date.now() + 2,
          role: "assistant",
          status: "done",
          content: data.answer,
          sources: data.sources ?? [],
          stats: data.stats ?? null,
        };
        setMessages((prev) => [...prev.slice(0, -1), aiMsg]);
      } catch (err) {
        const errMsg = {
          id: Date.now() + 2,
          role: "assistant",
          status: "error",
          content:
            err.message ||
            "Gagal menghubungi server. Pastikan backend berjalan.",
        };
        setMessages((prev) => [...prev.slice(0, -1), errMsg]);
      } finally {
        setLoading(false);
      }
    },
    [input, loading],
  );

  const handleSuggestion = (text) => sendMessage(text);
  const handleNewChat = () => {
    setMessages([]);
    setInput("");
  };

  return (
    <div className="flex h-dvh overflow-hidden bg-bg-base">
      {/* Sidebar — hidden on mobile */}
      <div className="hidden md:flex">
        <Sidebar
          onSuggestion={handleSuggestion}
          onNewChat={handleNewChat}
          docCount={docCount}
        />
      </div>

      {/* Main chat */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-3.5 border-b border-border bg-bg-base shrink-0">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center text-lg shrink-0"
              style={{ background: "var(--gradient-accent)" }}
            >
              🎓
            </div>
            <div>
              <h2 className="text-[15px] font-semibold text-text-primary leading-tight">
                Pedoman Akademik
              </h2>
              <p className="text-[11px] text-text-muted">
                Asisten berbasis RAG + pgvector
              </p>
            </div>
          </div>

          {/* Clear chat */}
          {messages.length > 0 && (
            <button
              onClick={handleNewChat}
              title="Hapus percakapan"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-[12px] text-text-muted hover:border-red-500/40 hover:text-red-400 hover:bg-red-500/8 transition-all duration-150 cursor-pointer"
            >
              <svg
                className="w-3.5 h-3.5"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              Hapus
            </button>
          )}
        </header>

        {/* Messages */}
        <main className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <EmptyState onSuggestion={handleSuggestion} />
          ) : (
            <div className="max-w-190 mx-auto px-6 py-6 space-y-5">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </main>

        {/* Input */}
        <ChatInput
          value={input}
          onChange={setInput}
          onSend={() => sendMessage()}
          disabled={loading}
        />
      </div>
    </div>
  );
}
