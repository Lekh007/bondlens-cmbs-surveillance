import { useEffect, useRef, useState } from 'react';
import { X, Send, Sparkles } from 'lucide-react';
import { ChatBubble } from './ChatBubble';
import { matchCanned, SUGGESTED_PROMPTS } from './cannedResponses';
import type { ChatMessage } from '@/features/bondlens/types';

interface Props {
  open: boolean;
  onClose: () => void;
}

const INTRO_MESSAGE: ChatMessage = {
  id: 'intro',
  role: 'ai',
  text: "Hi — I'm **Bond Viewer AI**. I can answer questions about MSC 2019-L3's tranches, scenarios, geography, property types, leases, and servicer flags. Pick a suggestion below or ask anything.",
};

export function ChatPanel({ open, onClose }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([INTRO_MESSAGE]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isThinking]);

  const send = (text: string) => {
    if (!text.trim()) return;
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: 'user', text };
    setMessages(m => [...m, userMsg]);
    setInput('');
    setIsThinking(true);
    // Simulate model latency
    setTimeout(() => {
      const aiMsg = matchCanned(text);
      setMessages(m => [...m, aiMsg]);
      setIsThinking(false);
    }, 650);
  };

  if (!open) return null;

  return (
    <aside className="chat-panel animate-slide-in" role="dialog" aria-label="Bond Viewer AI">
      {/* Header */}
      <div className="chat-header">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-md flex items-center justify-center" style={{ background: 'rgba(255,255,255,0.15)' }}>
            <Sparkles size={16} strokeWidth={2} />
          </div>
          <div>
            <div className="text-[14px] font-semibold">Bond Viewer AI</div>
            <div className="text-[11px]" style={{ color: 'rgba(255,255,255,0.7)' }}>
              MSC 2019-L3 · structured data agent
            </div>
          </div>
        </div>
        <button className="card-action-btn" onClick={onClose} aria-label="Close">
          <X size={16} strokeWidth={1.8} />
        </button>
      </div>

      {/* Suggested prompts */}
      {messages.length <= 1 && (
        <div className="chat-suggested">
          {SUGGESTED_PROMPTS.map(p => (
            <button key={p} className="chat-suggest-chip" onClick={() => send(p)}>
              {p}
            </button>
          ))}
        </div>
      )}

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {messages.map(m => <ChatBubble key={m.id} message={m} />)}
        {isThinking && (
          <div className="chat-bubble-ai inline-flex items-center gap-1.5 self-start">
            <span className="text-text-md text-[12px]">Thinking</span>
            <span className="flex gap-0.5">
              <Dot delay={0} />
              <Dot delay={150} />
              <Dot delay={300} />
            </span>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="chat-input">
        <input
          type="text"
          placeholder="Ask about MSC 2019-L3..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') send(input);
          }}
        />
        <button
          className="btn"
          style={{ background: input.trim() ? '#1E3A8A' : '#CBD5E1', color: '#FFFFFF' }}
          onClick={() => send(input)}
          disabled={!input.trim()}
        >
          <Send size={13} strokeWidth={1.8} />
        </button>
      </div>
    </aside>
  );
}

function Dot({ delay }: { delay: number }) {
  return (
    <span
      className="inline-block w-1 h-1 rounded-full bg-text-md"
      style={{
        animation: `pulse 1.2s ease-in-out infinite`,
        animationDelay: `${delay}ms`,
      }}
    />
  );
}
