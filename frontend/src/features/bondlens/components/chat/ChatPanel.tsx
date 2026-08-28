import { useEffect, useRef, useState } from 'react'
import { X, Send, Sparkles } from 'lucide-react'
import { ChatBubble, type DisplayMessage } from './ChatBubble'
import { ApiError } from '@/api/client'
import type { Citation } from '@/features/bondlens/api'
import { useChat } from '@/features/bondlens/hooks'
import { EvidenceDrawer } from '@/features/bondlens/components/EvidenceDrawer'

interface Props {
  open: boolean
  onClose: () => void
  dealId: string | null
  dealName: string
}

const SUGGESTED_PROMPTS = [
  'What changed for this deal between the last two reporting periods?',
  'Which loans have the largest balance drift?',
  'Which properties deteriorated most between May and July?',
]

const INTRO_MESSAGE: DisplayMessage = {
  id: 'intro',
  role: 'ai',
  text: "Hi — I'm the **BondLens** analyst. Ask about payment status changes, balance drift, or property/loan data for this deal. Every answer is grounded in the ingested SEC filings and cites its sources.",
}

export function ChatPanel({ open, onClose, dealId, dealName }: Props) {
  const [messages, setMessages] = useState<DisplayMessage[]>([INTRO_MESSAGE])
  const [input, setInput] = useState('')
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null)
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const chat = useChat(dealId ?? '')

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, chat.isPending])

  const send = async (text: string) => {
    if (!text.trim() || !dealId) return
    const userMsg: DisplayMessage = { id: crypto.randomUUID(), role: 'user', text }
    setMessages((m) => [...m, userMsg])
    setInput('')

    try {
      const result = await chat.mutateAsync(text)
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: 'ai',
          text: result.answer,
          citations: result.citations,
          verificationPassed: result.verification_passed,
        },
      ])
    } catch (error) {
      const isModelUnavailable = error instanceof ApiError && error.status === 503
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: 'ai',
          isError: true,
          text: isModelUnavailable
            ? 'The BondLens model is currently unavailable. Try again once it is running.'
            : error instanceof ApiError
              ? error.message
              : 'Something went wrong answering that question.',
        },
      ])
    }
  }

  if (!open) return null

  return (
    <>
      <aside className="chat-panel animate-slide-in" role="dialog" aria-label="BondLens analyst">
        <div className="chat-header">
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-md flex items-center justify-center"
              style={{ background: 'rgba(255,255,255,0.15)' }}
            >
              <Sparkles size={16} strokeWidth={2} />
            </div>
            <div>
              <div className="text-[14px] font-semibold">BondLens Analyst</div>
              <div className="text-[11px]" style={{ color: 'rgba(255,255,255,0.7)' }}>
                {dealName || 'No deal selected'}
              </div>
            </div>
          </div>
          <button className="card-action-btn" onClick={onClose} aria-label="Close">
            <X size={16} strokeWidth={1.8} />
          </button>
        </div>

        {!dealId && (
          <div className="p-4 text-[12px] text-text-md border-b border-border-l">
            Select or ingest a deal before asking a question.
          </div>
        )}

        {messages.length <= 1 && dealId && (
          <div className="chat-suggested">
            {SUGGESTED_PROMPTS.map((p) => (
              <button key={p} className="chat-suggest-chip" onClick={() => void send(p)}>
                {p}
              </button>
            ))}
          </div>
        )}

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          {messages.map((m) => (
            <ChatBubble key={m.id} message={m} onCitationClick={setSelectedCitation} />
          ))}
          {chat.isPending && (
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

        <div className="chat-input">
          <input
            type="text"
            placeholder={dealId ? `Ask about ${dealName}...` : 'Select a deal first'}
            value={input}
            disabled={!dealId}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void send(input)
            }}
          />
          <button
            className="btn"
            style={{ background: input.trim() && dealId ? '#1E3A8A' : '#CBD5E1', color: '#FFFFFF' }}
            onClick={() => void send(input)}
            disabled={!input.trim() || !dealId}
          >
            <Send size={13} strokeWidth={1.8} />
          </button>
        </div>
      </aside>
      <EvidenceDrawer citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
    </>
  )
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
  )
}
