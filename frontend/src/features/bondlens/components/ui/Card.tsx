import { Download, Filter, Maximize2, Columns3 } from 'lucide-react';
import type { ReactNode } from 'react';

interface Props {
  id?: string;
  title: string;
  subtitle?: string;
  actions?: ('columns' | 'filter' | 'export' | 'expand')[];
  className?: string;
  children: ReactNode;
}

export function Card({ id, title, subtitle, actions = ['export'], className, children }: Props) {
  return (
    <article id={id} className={`card ${className ?? ''}`}>
      <header className="card-hdr">
        <div>
          <div className="card-title">{title}</div>
          {subtitle && <div className="card-sub">{subtitle}</div>}
        </div>
        <div className="card-actions">
          {actions.includes('columns') && (
            <button className="card-action-btn" title="Columns">
              <Columns3 size={15} strokeWidth={1.6} />
            </button>
          )}
          {actions.includes('filter') && (
            <button className="card-action-btn" title="Filter">
              <Filter size={15} strokeWidth={1.6} />
            </button>
          )}
          {actions.includes('export') && (
            <button className="card-action-btn" title="Export">
              <Download size={15} strokeWidth={1.6} />
            </button>
          )}
          {actions.includes('expand') && (
            <button className="card-action-btn" title="Expand">
              <Maximize2 size={15} strokeWidth={1.6} />
            </button>
          )}
        </div>
      </header>
      {children}
    </article>
  );
}
