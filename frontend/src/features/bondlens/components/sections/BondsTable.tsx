import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Card } from '@/features/bondlens/components/ui/Card';
import { Pill } from '@/features/bondlens/components/ui/Pill';
import { tranches } from '@/features/bondlens/data/deal';
import { fmtNum, fmtPct } from '@/features/bondlens/lib/format';
import type { Tranche } from '@/features/bondlens/types';

const GROUPS = [
  { key: 'senior' as const, label: 'Senior + Mezzanine', count: 14 },
  { key: 'io' as const,     label: 'Interest-Only (IO)', count: 6  },
  { key: 'others' as const, label: 'Others',             count: 2  },
];

const TOTAL_COLS = 18;

export function BondsTable() {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const totals = {
    orig: tranches.reduce((s, t) => s + t.origBalance, 0),
    curr: tranches.reduce((s, t) => s + t.currentBalance, 0),
    shortCum: tranches.reduce((s, t) => s + t.shortCum, 0),
    shortCurr: tranches.reduce((s, t) => s + t.shortCurr, 0),
    holding: tranches.reduce((s, t) => s + (t.holding ?? 0), 0),
    kbraLoss: tranches.reduce((s, t) => s + (t.kbraLoss ?? 0), 0),
  };

  return (
    <Card
      id="bonds"
      title="Bonds & Tranches"
      subtitle={`${tranches.length} securities · Senior + Mezzanine (14) · IO (6) · Others (2) · click group rows to collapse`}
      actions={['columns', 'filter', 'export']}
    >
      <div className="overflow-x-auto">
        <table className="vt">
          <thead>
            <tr>
              <th>CUSIP</th>
              <th>Class</th>
              <th>S&amp;P</th>
              <th className="num">Orig Balance</th>
              <th className="num">Current Balance</th>
              <th className="num">Factor</th>
              <th className="num">Coupon</th>
              <th className="num">WAL</th>
              <th className="num">CE %</th>
              <th className="num">Def CE %</th>
              <th className="num">Int Short Cum</th>
              <th className="num">Int Short Curr</th>
              <th className="num">Purch Price</th>
              <th className="num">Holding</th>
              <th className="num">% Face</th>
              <th className="num">KBRA Loss</th>
              <th className="num">KBRA IRR</th>
              <th className="num">KBRA MOC</th>
            </tr>
          </thead>
          <tbody>
            {GROUPS.map(g => (
              <GroupBlock
                key={g.key}
                label={g.label}
                count={g.count}
                collapsed={collapsed[g.key]}
                onToggle={() => setCollapsed(c => ({ ...c, [g.key]: !c[g.key] }))}
                rows={tranches.filter(t => t.group === g.key)}
              />
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3}>Total · {tranches.length} securities</td>
              <td className="num">{fmtNum(totals.orig)}</td>
              <td className="num">{fmtNum(totals.curr)}</td>
              <td colSpan={5}></td>
              <td className="num">{fmtNum(totals.shortCum)}</td>
              <td className="num">{fmtNum(totals.shortCurr)}</td>
              <td colSpan={2}></td>
              <td className="num">{fmtNum(totals.holding)}</td>
              <td></td>
              <td className="num">{fmtNum(totals.kbraLoss)}</td>
              <td></td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>
    </Card>
  );
}

function GroupBlock({
  label,
  count,
  collapsed,
  onToggle,
  rows,
}: {
  label: string;
  count: number;
  collapsed?: boolean;
  onToggle: () => void;
  rows: Tranche[];
}) {
  return (
    <>
      <tr className="group-row" onClick={onToggle}>
        <td colSpan={TOTAL_COLS}>
          <span className="inline-flex items-center gap-1">
            {collapsed ? <ChevronRight size={14} strokeWidth={2} /> : <ChevronDown size={14} strokeWidth={2} />}
            {label}
            <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] bg-white/15 text-white font-semibold">
              {count} items
            </span>
          </span>
        </td>
      </tr>
      {!collapsed && rows.map(t => <BondRow key={t.cusip} t={t} />)}
    </>
  );
}

function BondRow({ t }: { t: Tranche }) {
  const ratingVariant = t.rating === 'AAA' ? 'gain' : t.rating === 'AA' ? 'info' : 'neutral';

  return (
    <tr>
      <td className="num">{t.cusip}</td>
      <td>{t.cls}</td>
      <td><Pill variant={ratingVariant}>{t.rating}</Pill></td>
      <td className="num">{fmtNum(t.origBalance)}</td>
      <td className="num">{fmtNum(t.currentBalance)}</td>
      <td className="num">{t.factor.toFixed(4)}</td>
      <td className="num">{t.coupon !== null ? t.coupon.toFixed(2) : <span className="muted">—</span>}</td>
      <td className="num">{t.wal !== null ? t.wal.toFixed(2) : <span className="muted">—</span>}</td>
      <td className="pct-cell num" style={{ ['--pct' as never]: `${t.cePct}%` } as never}><span>{fmtPct(t.cePct, 1)}</span></td>
      <td className="pct-cell num" style={{ ['--pct' as never]: `${t.defCePct}%` } as never}><span>{fmtPct(t.defCePct, 1)}</span></td>
      <td className="num">{fmtNum(t.shortCum)}</td>
      <td className="num">{fmtNum(t.shortCurr)}</td>
      <td className="num">{t.purchPrice !== undefined ? t.purchPrice.toFixed(2) : <span className="muted">—</span>}</td>
      <td className="num">{t.holding !== undefined ? fmtNum(t.holding) : <span className="muted">—</span>}</td>
      <td className="pct-cell num" style={{ ['--pct' as never]: `${t.pctFace ?? 0}%` } as never}>
        <span className={t.pctFace === undefined ? 'muted' : ''}>{t.pctFace !== undefined ? fmtPct(t.pctFace, 1) : '—'}</span>
      </td>
      <td className="num">{t.kbraLoss !== undefined ? fmtNum(t.kbraLoss) : <span className="muted">—</span>}</td>
      <td className="pct-cell num" style={{ ['--pct' as never]: `${t.kbraIrr ?? 0}%` } as never}>
        <span className={t.kbraIrr === undefined ? 'muted' : ''}>{t.kbraIrr !== undefined ? fmtPct(t.kbraIrr, 1) : '—'}</span>
      </td>
      <td className="num">{t.kbraMoc !== undefined ? `${t.kbraMoc.toFixed(2)}x` : <span className="muted">—</span>}</td>
    </tr>
  );
}
