import { Card } from '@/features/bondlens/components/ui/Card';
import { propertyTypes } from '@/features/bondlens/data/deal';
import { fmtNum, fmtPct } from '@/features/bondlens/lib/format';

export function PropertyTypeDistribution() {
  const totalLoans = propertyTypes.reduce((s, p) => s + p.loans, 0);
  const totalBalance = propertyTypes.reduce((s, p) => s + p.balance, 0);

  return (
    <Card
      id="property"
      title="Property Type Distribution"
      subtitle={`${propertyTypes.length} property types · 50 properties · $960.3M total balance`}
      actions={['columns', 'export']}
    >
      <div className="overflow-x-auto">
        <table className="vt">
          <thead>
            <tr>
              <th>Property Type</th>
              <th className="num"># Loans</th>
              <th className="num">Balance</th>
              <th className="num">% of Pool</th>
            </tr>
          </thead>
          <tbody>
            {propertyTypes.map(p => (
              <tr key={p.type}>
                <td className="link">{p.type}</td>
                <td className="num">{p.loans}</td>
                <td className="num">{fmtNum(p.balance)}</td>
                <td className="pct-cell num" style={{ ['--pct' as never]: `${p.pct}%` } as never}>
                  <span>{fmtPct(p.pct, 2)}</span>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td>Total</td>
              <td className="num">{totalLoans}</td>
              <td className="num">{fmtNum(totalBalance)}</td>
              <td className="num">100.00%</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </Card>
  );
}
