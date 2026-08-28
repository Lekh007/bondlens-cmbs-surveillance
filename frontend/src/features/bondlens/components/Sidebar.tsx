import { useEffect, useState } from 'react';
import {
  LayoutDashboard,
  FileText,
  List,
  TrendingUp,
  Banknote,
  CalendarClock,
  Palette,
  Folder,
} from 'lucide-react';

const ANCHORS = [
  { id: 'overview',           label: 'Overview' },
  { id: 'period-comparison',  label: 'Period Comparison' },
  { id: 'focus',              label: 'Payment Status Changes' },
  { id: 'balance-maturity',   label: 'Balance Drift' },
  { id: 'property',           label: 'Property Type' },
  { id: 'geography',          label: 'Geography' },
];

const OTHER_TABS = [
  { label: 'Underwriting',  Icon: FileText },
  { label: 'Loan Details',  Icon: List },
  { label: 'Loan Vectors',  Icon: TrendingUp },
  { label: 'Cashflows',     Icon: Banknote },
  { label: 'Loan Events',   Icon: CalendarClock },
  { label: 'Market Color',  Icon: Palette },
  { label: 'Documents',     Icon: Folder },
];

export function Sidebar() {
  const [activeAnchor, setActiveAnchor] = useState<string>('overview');

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            setActiveAnchor(entry.target.id);
          }
        });
      },
      { rootMargin: '-120px 0px -60% 0px', threshold: 0 },
    );
    ANCHORS.forEach(a => {
      const el = document.getElementById(a.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  const onAnchorClick = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault();
    const target = document.getElementById(id);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <aside className="sidebar">
      <div className="px-2 pb-2 text-2xs uppercase tracking-wider text-text-md font-semibold">Sections</div>

      <a href="#overview" className="nav-item active">
        <LayoutDashboard size={15} strokeWidth={1.6} />
        Deal Summary
      </a>

      {ANCHORS.map(a => (
        <a
          key={a.id}
          href={`#${a.id}`}
          className={`nav-anchor ${activeAnchor === a.id ? 'active' : ''}`}
          onClick={e => onAnchorClick(e, a.id)}
        >
          {a.label}
        </a>
      ))}

      <div className="px-2 pt-4 pb-2 text-2xs uppercase tracking-wider text-text-md font-semibold">Other Tabs</div>

      {OTHER_TABS.map(({ label, Icon }) => (
        <div key={label} className="nav-item disabled">
          <Icon size={15} strokeWidth={1.6} />
          {label}
        </div>
      ))}

      <div className="mt-6 p-3 rounded-lg" style={{ background: '#EFF6FF', border: '1px solid #DBEAFE' }}>
        <div className="text-2xs font-semibold text-navy uppercase tracking-wider mb-1">Portfolio Demo</div>
        <div className="text-[12px] text-text-md leading-snug">
          Loan-level CMBS ABS-EE surveillance, backed by real SEC filings. Other tabs are not built.
        </div>
      </div>
    </aside>
  );
}
