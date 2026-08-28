import { ExternalLink, X } from 'lucide-react'
import type { Citation } from '@/features/bondlens/api'

interface Props {
  citation: Citation | null
  onClose: () => void
}

export function EvidenceDrawer({ citation, onClose }: Props) {
  if (!citation) return null

  return (
    <aside className="chat-panel" role="dialog" aria-label="Evidence">
      <div className="chat-header">
        <div className="text-[14px] font-semibold">Evidence</div>
        <button className="card-action-btn" onClick={onClose} aria-label="Close evidence">
          <X size={16} strokeWidth={1.8} />
        </button>
      </div>
      <div className="p-4 flex flex-col gap-3 text-[13px]">
        <div>
          <div className="text-2xs uppercase tracking-wider text-text-md font-semibold mb-1">
            Source
          </div>
          <div className="text-text-hi">{citation.source_name}</div>
        </div>
        {citation.record_id && (
          <div>
            <div className="text-2xs uppercase tracking-wider text-text-md font-semibold mb-1">
              Record
            </div>
            <div className="text-text-hi num">{citation.record_id}</div>
          </div>
        )}
        {citation.field_path && (
          <div>
            <div className="text-2xs uppercase tracking-wider text-text-md font-semibold mb-1">
              Field
            </div>
            <div className="text-text-hi">{citation.field_path}</div>
          </div>
        )}
        <a
          href={citation.source_url}
          target="_blank"
          rel="noreferrer"
          className="chat-suggest-chip inline-flex items-center gap-1.5 self-start"
        >
          Open on SEC EDGAR
          <ExternalLink size={12} strokeWidth={1.8} />
        </a>
      </div>
    </aside>
  )
}
