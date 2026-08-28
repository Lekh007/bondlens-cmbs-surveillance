import { Info } from 'lucide-react';
import { Card } from '@/features/bondlens/components/ui/Card';
import { Pill } from '@/features/bondlens/components/ui/Pill';
import type { DelinquencyStatus } from '@/features/bondlens/types';

const STATUSES: { label: DelinquencyStatus; variant: 'gain' | 'warn' | 'loss' | 'neutral' }[] = [
  { label: 'Current',             variant: 'gain' },
  { label: '<1 Month',            variant: 'warn' },
  { label: '30 Days',             variant: 'warn' },
  { label: '60 Days',             variant: 'warn' },
  { label: '90+ Days',            variant: 'loss' },
  { label: 'Foreclosure',         variant: 'loss' },
  { label: 'REO',                 variant: 'loss' },
  { label: 'Grace / Not yet due', variant: 'neutral' },
  { label: 'NonPerfMatBall',      variant: 'neutral' },
  { label: 'Unknown',             variant: 'neutral' },
];

export function FocusDelinquency() {
  return (
    <section id="focus" className="grid grid-cols-2 gap-6">
      {/* Focus Loans */}
      <Card title="Focus Loans" subtitle="User-flagged loans, special servicing, and watchlist" actions={['export']}>
        <table className="vt">
          <thead>
            <tr>
              <th></th>
              <th className="num"># Loans</th>
              <th className="num">Balance</th>
              <th className="num">% of Pool</th>
            </tr>
          </thead>
          <tbody>
            <FocusRow label="USER Focus" />
            <FocusRow label="Special Servicing" linkable />
            <FocusRow label="Watchlist" linkable />
          </tbody>
        </table>
        <div className="p-4 border-t border-border-l bg-bg flex items-center gap-2.5 text-[12px] text-text-md">
          <Info size={14} strokeWidth={1.8} className="text-info" />
          No loans currently flagged for focus or special servicing.{' '}
          <span className="text-link cursor-pointer hover:underline">Flag a loan →</span>
        </div>
      </Card>

      {/* Delinquency */}
      <Card title="Delinquency Status" subtitle="Status distribution across all 51 loans" actions={['export']}>
        <table className="vt">
          <thead>
            <tr>
              <th>Status</th>
              <th className="num"># Loans</th>
              <th className="num">Balance</th>
              <th className="num">% of Pool</th>
            </tr>
          </thead>
          <tbody>
            {STATUSES.map(s => (
              <tr key={s.label}>
                <td><Pill variant={s.variant}>{s.label}</Pill></td>
                <td className="num muted">·</td>
                <td className="num muted">·</td>
                <td className="pct-cell num" style={{ ['--pct' as never]: `0%` } as never}>
                  <span className="muted">0.00%</span>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td>Total</td>
              <td className="num">0</td>
              <td className="num">0</td>
              <td className="num">0.00%</td>
            </tr>
          </tfoot>
        </table>
      </Card>
    </section>
  );
}

function FocusRow({ label, linkable }: { label: string; linkable?: boolean }) {
  return (
    <tr>
      <td className={linkable ? 'link' : 'text-text-md'}>{label}</td>
      <td className="num muted">·</td>
      <td className="num muted">·</td>
      <td className="pct-cell num" style={{ ['--pct' as never]: `0%` } as never}>
        <span className="muted">0.00%</span>
      </td>
    </tr>
  );
}
