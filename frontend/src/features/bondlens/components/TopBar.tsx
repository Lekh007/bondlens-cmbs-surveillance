import { Briefcase, ChevronDown, ClockAlert, Play, Cpu, Download, Settings, Bell, BarChart3 } from 'lucide-react';

interface Props {
  density: 'comfy' | 'compact';
  onDensityChange: (d: 'comfy' | 'compact') => void;
  onRunJob: (name: string) => void;
  onExport: () => void;
}

export function TopBar({ density, onDensityChange, onRunJob, onExport }: Props) {
  return (
    <header className="topbar">
      {/* Logo + brand */}
      <div className="flex items-center gap-2.5 pr-1">
        <div className="w-8 h-8 rounded-md bg-white/12 flex items-center justify-center" style={{ background: 'rgba(255,255,255,0.12)' }}>
          <BarChart3 size={18} strokeWidth={2.2} className="text-white" />
        </div>
        <div className="leading-tight">
          <div className="text-[14px] font-semibold tracking-tight">Vichara</div>
          <div className="text-[10px] uppercase tracking-wider" style={{ color: 'rgba(255,255,255,0.65)' }}>Bond Viewer</div>
        </div>
      </div>

      <div className="topbar-divider" />

      {/* Deal selector */}
      <button className="deal-selector">
        <Briefcase size={14} strokeWidth={1.8} />
        <span className="num">MSC&nbsp;2019-L3</span>
        <span className="pill pill-brand" style={{ background: 'rgba(255,255,255,0.16)', color: '#ffffff', fontSize: '10px', padding: '1px 6px' }}>Conduit</span>
        <ChevronDown size={14} strokeWidth={1.8} />
      </button>

      {/* Data freshness pill */}
      <div className="freshness" title="Last Auto-UW run was on 5/3/2024 — re-run recommended">
        <ClockAlert size={12} strokeWidth={1.8} />
        Data 13 days stale
      </div>

      <div className="flex-1" />

      {/* Settle date */}
      <label className="flex items-center gap-2 text-[12px]" style={{ color: 'rgba(255,255,255,0.85)' }}>
        Settle&nbsp;Date
        <input type="text" defaultValue="05/21/2026" className="input-date" />
      </label>

      {/* Run buttons */}
      <button className="btn btn-ghost-top" onClick={() => onRunJob('Cashflows')}>
        <Play size={13} strokeWidth={1.8} />
        Run Cashflows
      </button>
      <button className="btn btn-ghost-top" onClick={() => onRunJob('Auto-UW')}>
        <Cpu size={13} strokeWidth={1.8} />
        Run Auto-UW
      </button>

      <div className="topbar-divider" />

      {/* Density toggle */}
      <div className="seg" role="group" aria-label="Density">
        <button className={density === 'comfy' ? 'active' : ''} onClick={() => onDensityChange('comfy')}>
          Comfortable
        </button>
        <button className={density === 'compact' ? 'active' : ''} onClick={() => onDensityChange('compact')}>
          Compact
        </button>
      </div>

      {/* Export */}
      <button className="btn btn-primary" onClick={onExport}>
        <Download size={13} strokeWidth={1.8} />
        Export
      </button>

      <button className="card-action-btn" title="Settings"><Settings size={15} strokeWidth={1.6} /></button>
      <button className="card-action-btn" title="Notifications"><Bell size={15} strokeWidth={1.6} /></button>
    </header>
  );
}
