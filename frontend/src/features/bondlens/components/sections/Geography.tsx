import { Card } from '@/features/bondlens/components/ui/Card';
import { topStates, topCities } from '@/features/bondlens/data/deal';
import { fmtNum, fmtPct } from '@/features/bondlens/lib/format';
import type { GeoRow } from '@/features/bondlens/types';

export function Geography() {
  return (
    <section id="geography" className="grid grid-cols-2 gap-6">
      <Card title="Top 15 States · Geographic Distribution" subtitle="By balance · NY leads at 15.89%" actions={['export']}>
        <GeoTable rows={topStates} />
      </Card>
      <Card title="Top 15 Cities · Geographic Distribution" subtitle="By balance · Las Vegas leads at 7.53%" actions={['export']}>
        <GeoTable rows={topCities} />
      </Card>
    </section>
  );
}

function GeoTable({ rows }: { rows: GeoRow[] }) {
  const total = rows.reduce((s, r) => s + r.balance, 0);
  return (
    <table className="vt">
      <thead>
        <tr>
          <th>Location</th>
          <th className="num">Balance</th>
          <th className="num">% of Pool</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={`${r.loc}-${i}`}>
            <td className={r.loc === 'Other' ? 'text-text-md' : 'link'}>{r.loc}</td>
            <td className="num">{fmtNum(r.balance)}</td>
            <td className="pct-cell num" style={{ ['--pct' as never]: `${r.pct}%` } as never}>
              <span>{fmtPct(r.pct, 2)}</span>
            </td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <td>Total</td>
          <td className="num">{fmtNum(total)}</td>
          <td className="num">100.00%</td>
        </tr>
      </tfoot>
    </table>
  );
}
