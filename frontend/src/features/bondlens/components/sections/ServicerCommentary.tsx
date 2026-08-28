import { Card } from '@/features/bondlens/components/ui/Card';
import { Pill } from '@/features/bondlens/components/ui/Pill';
import { servicerKeywords } from '@/features/bondlens/data/deal';
import { fmtNum, fmtPct } from '@/features/bondlens/lib/format';

export function ServicerCommentary() {
  return (
    <Card
      id="servicer"
      title="Servicer Commentary Keywords"
      subtitle={`${servicerKeywords.length} keywords surfaced from special-servicer notes · click to view associated loans`}
      actions={['export']}
      className="mb-8"
    >
      <table className="vt">
        <thead>
          <tr>
            <th>Keyword</th>
            <th className="num"># Loans</th>
            <th className="num">Balance</th>
            <th className="num">% of Pool</th>
          </tr>
        </thead>
        <tbody>
          {servicerKeywords.map(k => (
            <tr key={k.keyword}>
              <td><Pill variant={k.severity}>{k.keyword}</Pill></td>
              <td className="num">{k.loans}</td>
              <td className="num">{fmtNum(k.balance)}</td>
              <td className="pct-cell num" style={{ ['--pct' as never]: `${k.pct}%` } as never}>
                <span>{fmtPct(k.pct, 2)}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
