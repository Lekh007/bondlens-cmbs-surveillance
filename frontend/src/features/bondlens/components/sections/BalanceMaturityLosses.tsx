import { Info } from 'lucide-react';
import { Card } from '@/features/bondlens/components/ui/Card';
import { Pill } from '@/features/bondlens/components/ui/Pill';

export function BalanceMaturityLosses() {
  return (
    <section id="balance-maturity" className="grid grid-cols-3 gap-6">
      {/* Loan Balance Distribution */}
      <Card title="Loan Balance Distribution" subtitle="Top-N concentration" actions={['export']}>
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
            {['Top 5 Loans', 'Top 10 Loans', 'Top 15 Loans'].map(label => (
              <tr key={label}>
                <td className="link">{label}</td>
                <td className="num muted">·</td>
                <td className="num muted">·</td>
                <td className="pct-cell num" style={{ ['--pct' as never]: `0%` } as never}>
                  <span className="muted">0.00%</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="p-3 border-t border-border-l bg-bg text-[11.5px] text-text-md flex items-center gap-2">
          <Info size={13} strokeWidth={1.8} className="text-info" />
          Not populated · run Auto-UW to calculate concentration
        </div>
      </Card>

      {/* Remaining Term to Maturity */}
      <Card title="Remaining Term to Maturity" subtitle="By bucket" actions={['export']}>
        <table className="vt">
          <thead>
            <tr>
              <th>Bucket</th>
              <th className="num"># Loans</th>
              <th className="num">Balance</th>
              <th className="num">% of Pool</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><Pill variant="warn">≤ 36 months</Pill></td>
              <td className="num">0</td>
              <td className="num muted">·</td>
              <td className="pct-cell num" style={{ ['--pct' as never]: `0%` } as never}>
                <span className="muted">0.00%</span>
              </td>
            </tr>
            <tr>
              <td><Pill variant="info">≤ 60 months</Pill></td>
              <td className="num">49</td>
              <td className="num">952,255,170</td>
              <td className="pct-cell num" style={{ ['--pct' as never]: `99.17%` } as never}>
                <span>99.17%</span>
              </td>
            </tr>
            <tr>
              <td><Pill variant="gain">≤ 84 months</Pill></td>
              <td className="num">49</td>
              <td className="num">952,255,170</td>
              <td className="pct-cell num" style={{ ['--pct' as never]: `99.17%` } as never}>
                <span>99.17%</span>
              </td>
            </tr>
          </tbody>
        </table>
      </Card>

      {/* Timing of Losses */}
      <Card title="Timing of Losses" subtitle="Annual projected loss" actions={['export']}>
        <table className="vt">
          <thead>
            <tr>
              <th>Period</th>
              <th className="num">Annual Loss</th>
              <th className="num">Cumulative</th>
            </tr>
          </thead>
          <tbody>
            <tr><td>2026</td><td className="num">0</td><td className="num">0</td></tr>
            <tr><td>2027</td><td className="num">0</td><td className="num">0</td></tr>
            <tr><td>2028</td><td className="num">0</td><td className="num">0</td></tr>
            <tr>
              <td>2029</td>
              <td className="num text-loss">(15,232,794)</td>
              <td className="num text-loss">(15,232,794)</td>
            </tr>
          </tbody>
        </table>
      </Card>
    </section>
  );
}
