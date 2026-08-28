import { AlertTriangle, FileText } from 'lucide-react'
import type { Citation } from '@/features/bondlens/api'

export interface DisplayMessage {
  id: string
  role: 'user' | 'ai'
  text: string
  citations?: Citation[]
  verificationPassed?: boolean
  isError?: boolean
}

interface Props {
  message: DisplayMessage
  onCitationClick: (citation: Citation) => void
}

export function ChatBubble({ message, onCitationClick }: Props) {
  if (message.role === 'user') {
    return (
      <div className="flex flex-col gap-1 items-end animate-fade-up">
        <div className="chat-bubble-user">{message.text}</div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2 items-start animate-fade-up">
      <div className={`chat-bubble-ai ${message.isError ? 'border-loss' : ''}`}>
        {renderMarkdownLite(message.text)}
      </div>
      {message.verificationPassed === false && (
        <div className="flex items-center gap-1.5 text-[11px] text-warn max-w-[92%]">
          <AlertTriangle size={12} strokeWidth={1.8} />
          This answer did not pass automatic verification against the underlying data.
        </div>
      )}
      {message.citations && message.citations.length > 0 && (
        <div className="flex flex-wrap gap-1.5 max-w-[92%]">
          {message.citations.map((c, i) => (
            <button
              key={`${c.source_url}-${i}`}
              className="chat-suggest-chip inline-flex items-center gap-1"
              onClick={() => onCitationClick(c)}
            >
              <FileText size={11} strokeWidth={1.8} />
              {c.record_id ?? c.source_name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function renderMarkdownLite(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g)
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) {
      return (
        <strong key={i} className="font-semibold text-text-hi">
          {p.slice(2, -2)}
        </strong>
      )
    }
    if (p.startsWith('*') && p.endsWith('*')) {
      return (
        <em key={i} className="italic text-text-md">
          {p.slice(1, -1)}
        </em>
      )
    }
    return <span key={i}>{p}</span>
  })
}
