import { Info } from 'lucide-react'
import { Card } from '@/features/bondlens/components/ui/Card'
import type { BalanceDriftRanking } from '@/features/bondlens/api'
import { fmtMoney, fmtPct } from '@/features/bondlens/lib/format'

interface Props {
  ranking: BalanceDriftRanking
}

// Repurposed from the wireframe's fictional top-N concentration / maturity
// bucket / loss-timing tables (no lease, maturity-bucket, or loss-timing
// data exists in ABS-EE loan/property records) to the real surveillance
// signal BondLens actually computes: actual vs scheduled balance drift as
// of the latest ingested period. See analytics.py rank_loans_by_balance_drift.
export function BalanceMaturityLosses({ ranking }: Props) {
  const top = ranking.entries.slice(0, 10)

  return (
    <Card
      id="balance-maturity"
      title="Balance Drift"
      subtitle={`As of ${ranking.as_of_date ?? '—'} · top ${top.length} of ${ranking.entries.length} loans by |drift|`}
      actions={['export']}
    >
      {top.length === 0 ? (
        <div className="p-4 flex items-center gap-2.5 text-[12px] text-text-md">
          <Info size={14} strokeWidth={1.8} className="text-info" />
          No loan has both an actual and scheduled balance in this period.
        </div>
      ) : (
        <table className="vt">
          <thead>
            <tr>
              <th>Loan</th>
              <th className="num">Actual Balance</th>
              <th className="num">Scheduled Balance</th>
              <th className="num">Drift</th>
              <th className="num">Drift %</th>
            </tr>
          </thead>
          <tbody>
            {top.map((e) => (
              <tr key={e.loan_asset_number}>
                <td className="link num">{e.loan_asset_number}</td>
                <td className="num">{fmtMoney(Number(e.actual_balance_amount))}</td>
                <td className="num">{fmtMoney(Number(e.scheduled_balance_amount))}</td>
                <td className={`num ${Number(e.drift_amount) < 0 ? 'text-loss' : 'text-gain'}`}>
                  {fmtMoney(Number(e.drift_amount))}
                </td>
                <td className="num">
                  {e.drift_percentage === null ? '—' : fmtPct(Number(e.drift_percentage), 2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  )
}
