import { Card } from '@/features/bondlens/components/ui/Card'
import type { CompareResponse } from '@/features/bondlens/api'

interface Props {
  compare: CompareResponse | null
  isLoading: boolean
}

// The backend fixes period A/B to the two most recently ingested filings
// (BondLensService.ingest_deal keeps the last two "created" periods) -
// there is no endpoint to pick an arbitrary period pair, so this displays
// the comparison the backend already computed rather than offering a
// picker the API can't back.
export function PeriodComparison({ compare, isLoading }: Props) {
  if (isLoading) {
    return (
      <Card id="period-comparison" title="Period Comparison" subtitle="Loading…">
        <div className="p-4 text-[12px] text-text-md">Loading comparison…</div>
      </Card>
    )
  }

  if (!compare) {
    return (
      <Card id="period-comparison" title="Period Comparison" subtitle="Not enough data yet">
        <div className="p-4 text-[12px] text-text-md">
          This deal needs two ingested reporting periods before a comparison is available.
        </div>
      </Card>
    )
  }

  return (
    <Card
      id="period-comparison"
      title="Period Comparison"
      subtitle={`${compare.period_a_ending_date ?? '—'} → ${compare.period_b_ending_date ?? '—'} · ${compare.changes.length} field change(s)`}
      actions={['export']}
    >
      {compare.changes.length === 0 ? (
        <div className="p-4 text-[12px] text-text-md">No tracked field changed between these periods.</div>
      ) : (
        <table className="vt">
          <thead>
            <tr>
              <th>Loan</th>
              <th>Field</th>
              <th className="num">Before</th>
              <th className="num">After</th>
            </tr>
          </thead>
          <tbody>
            {compare.changes.map((c, i) => (
              <tr key={`${c.loan_asset_number}-${c.field_name}-${i}`}>
                <td className="link num">{c.loan_asset_number}</td>
                <td className="text-[12px] text-text-md">{c.field_name}</td>
                <td className="num muted">{c.before_value ?? '—'}</td>
                <td className="num">{c.after_value ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  )
}
