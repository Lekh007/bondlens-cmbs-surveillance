import { Info } from 'lucide-react'
import { Card } from '@/features/bondlens/components/ui/Card'
import { Pill } from '@/features/bondlens/components/ui/Pill'
import type { StatusChangeRanking } from '@/features/bondlens/api'

interface Props {
  ranking: StatusChangeRanking | null
}

// Repurposed from the wireframe's fictional focus/watchlist/full-bucket
// delinquency census (invented data with no ABS-EE backing) to the real
// surveillance signal BondLens actually computes: loans whose
// paymentStatusLoanCode changed between the two most recently ingested
// periods. See analytics.py rank_loans_by_status_change.
function severityVariant(rank: number): 'loss' | 'warn' | 'gain' {
  if (rank === 2) return 'loss'
  if (rank === 1) return 'warn'
  return 'gain'
}

function severityLabel(rank: number): string {
  if (rank === 2) return 'Newly delinquent'
  if (rank === 1) return 'Status changed'
  return 'Cured'
}

export function FocusDelinquency({ ranking }: Props) {
  const subtitle = ranking
    ? `${ranking.period_a_ending_date ?? '—'} → ${ranking.period_b_ending_date ?? '—'}`
    : 'Requires two ingested reporting periods'

  return (
    <Card
      id="focus"
      title="Payment Status Changes"
      subtitle={subtitle}
      actions={['export']}
    >
      {!ranking || ranking.entries.length === 0 ? (
        <div className="p-4 flex items-center gap-2.5 text-[12px] text-text-md">
          <Info size={14} strokeWidth={1.8} className="text-info" />
          {ranking
            ? 'No loan changed payment status code between these two periods.'
            : 'Not enough ingested periods to compare payment status.'}
        </div>
      ) : (
        <table className="vt">
          <thead>
            <tr>
              <th>Loan</th>
              <th>Properties</th>
              <th>Status Change</th>
              <th>Severity</th>
            </tr>
          </thead>
          <tbody>
            {ranking.entries.map((e) => (
              <tr key={e.loan_asset_number}>
                <td className="link num">{e.loan_asset_number}</td>
                <td className="text-[12px] text-text-md">{e.property_names.join(', ') || '—'}</td>
                <td className="num">
                  {e.status_before ?? '—'} → {e.status_after ?? '—'}
                </td>
                <td>
                  <Pill variant={severityVariant(e.severity_rank)}>
                    {severityLabel(e.severity_rank)}
                  </Pill>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  )
}
