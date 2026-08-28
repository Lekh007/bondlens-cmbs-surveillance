import { CheckCircle2, FileSpreadsheet } from 'lucide-react';
import type { ChatMessage } from '@/features/bondlens/types';

interface Props {
  message: ChatMessage;
}

export function ChatBubble({ message }: Props) {
  if (message.role === 'user') {
    return (
      <div className="flex flex-col gap-1 items-end animate-fade-up">
        <div className="chat-bubble-user">{message.text}</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 items-start animate-fade-up">
      <div className="chat-bubble-ai">
        {renderMarkdownLite(message.text)}
      </div>
      {message.payload && <PayloadCard payload={message.payload} />}
    </div>
  );
}

function renderMarkdownLite(text: string) {
  // Bold via **text**
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) {
      return <strong key={i} className="font-semibold text-text-hi">{p.slice(2, -2)}</strong>;
    }
    if (p.startsWith('*') && p.endsWith('*')) {
      return <em key={i} className="italic text-text-md">{p.slice(1, -1)}</em>;
    }
    return <span key={i}>{p}</span>;
  });
}

function PayloadCard({ payload }: { payload: NonNullable<ChatMessage['payload']> }) {
  if (payload.kind === 'kpis') {
    return (
      <div className="grid grid-cols-2 gap-2 max-w-[92%]">
        {payload.items.map((item, i) => (
          <div key={i} className="bg-surface border border-border-l rounded-lg p-2.5">
            <div className="text-[10px] uppercase tracking-wider text-text-md font-semibold">{item.label}</div>
            <div className="num text-[16px] font-semibold mt-0.5">{item.value}</div>
            {item.delta && <div className="text-[10.5px] text-text-md mt-0.5">{item.delta}</div>}
          </div>
        ))}
      </div>
    );
  }

  if (payload.kind === 'table') {
    return (
      <div className="bg-surface border border-border-l rounded-lg overflow-hidden max-w-[92%]">
        <table className="vt !text-[12px]">
          <thead>
            <tr>
              {payload.columns.map((c, i) => (
                <th key={i} className={i > 0 ? 'num' : ''}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {payload.rows.map((row, ri) => (
              <tr key={ri}>
                {row.map((cell, ci) => (
                  <td key={ci} className={ci > 0 ? 'num' : ''}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (payload.kind === 'comparison') {
    return (
      <div className="grid grid-cols-2 gap-2 max-w-[92%]">
        {payload.rows.map(scn => (
          <div key={scn.name} className="bg-surface border-l-2 rounded-lg p-2.5" style={{ borderLeftColor: scn.color }}>
            <div className="flex items-center gap-2 mb-2">
              <span className="w-2 h-2 rounded-full" style={{ background: scn.color }} />
              <span className="text-[12px] font-semibold text-text-hi">{scn.name}</span>
            </div>
            <div className="space-y-1">
              {scn.metrics.map((m, i) => (
                <div key={i} className="flex justify-between text-[11.5px]">
                  <span className="text-text-md">{m.label}</span>
                  <span className="num font-medium">{m.value}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (payload.kind === 'chart') {
    const max = Math.max(...payload.bars.map(b => b.value));
    return (
      <div className="bg-surface border border-border-l rounded-lg p-3 w-full max-w-[92%]">
        <div className="text-[12px] font-semibold mb-2">{payload.title}</div>
        <div className="space-y-1.5">
          {payload.bars.map((b, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="w-24 text-[11px] text-text-md truncate">{b.label}</div>
              <div className="flex-1 h-5 bg-zebra rounded relative">
                <div
                  className="h-full rounded"
                  style={{ width: `${(b.value / max) * 100}%`, background: b.color }}
                />
                <div className="absolute inset-y-0 right-1.5 flex items-center text-[10.5px] num font-medium text-text-hi">
                  {b.value.toFixed(2)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (payload.kind === 'download') {
    return (
      <div className="flex items-center gap-2.5 bg-gain-tint border border-gain/30 rounded-lg p-2.5 max-w-[92%]">
        <FileSpreadsheet size={20} className="text-gain shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-[12.5px] font-medium text-text-hi truncate">{payload.filename}</div>
          <div className="text-[11px] text-text-md flex items-center gap-1.5">
            <CheckCircle2 size={11} className="text-gain" />
            Download started · {payload.size}
          </div>
        </div>
      </div>
    );
  }

  return null;
}
