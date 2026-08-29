import type { ReactNode } from 'react'
import { Download, Settings, Bell, BarChart3 } from 'lucide-react'

interface Props {
  density: 'comfy' | 'compact'
  onDensityChange: (d: 'comfy' | 'compact') => void
  onExport: () => void
  dealSelector: ReactNode
}

export function TopBar({ density, onDensityChange, onExport, dealSelector }: Props) {
  return (
    <header className="topbar">
      <div className="flex items-center gap-2.5 pr-1">
        <div
          className="w-8 h-8 rounded-md bg-white/12 flex items-center justify-center"
          style={{ background: 'rgba(255,255,255,0.12)' }}
        >
          <BarChart3 size={18} strokeWidth={2.2} className="text-white" />
        </div>
        <div className="leading-tight">
          <div className="text-[14px] font-semibold tracking-tight">BondLens</div>
          <div className="text-[10px] uppercase tracking-wider" style={{ color: 'rgba(255,255,255,0.65)' }}>
            CMBS Surveillance
          </div>
        </div>
      </div>

      <div className="topbar-divider" />

      {dealSelector}

      <div className="flex-1" />

      <div className="seg" role="group" aria-label="Density">
        <button className={density === 'comfy' ? 'active' : ''} onClick={() => onDensityChange('comfy')}>
          Comfortable
        </button>
        <button className={density === 'compact' ? 'active' : ''} onClick={() => onDensityChange('compact')}>
          Compact
        </button>
      </div>

      <button className="btn btn-primary" onClick={onExport}>
        <Download size={13} strokeWidth={1.8} />
        Export
      </button>

      <button className="card-action-btn" title="Settings">
        <Settings size={15} strokeWidth={1.6} />
      </button>
      <button className="card-action-btn" title="Notifications">
        <Bell size={15} strokeWidth={1.6} />
      </button>
    </header>
  )
}
