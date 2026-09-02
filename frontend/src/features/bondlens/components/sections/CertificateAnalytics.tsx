import type {
  BondCollateralReconciliation,
  CertificateDistributionResponse,
} from '@/features/bondlens/api'
import { Card } from '@/features/bondlens/components/ui/Card'
import { fmtMoney, fmtPct } from '@/features/bondlens/lib/format'

type Props = {
  distributions: CertificateDistributionResponse | null
  reconciliation: BondCollateralReconciliation | null
}

function money(value: string | null): string {
  return value == null ? 'Not reported' : fmtMoney(Number(value))
}

export function CertificateAnalytics({ distributions, reconciliation }: Props) {
  if (!distributions || !reconciliation) return null
  const a1 = distributions.entries.find((entry) => entry.class_name === 'A-1')

  return (
    <Card
      title="Certificate & collateral reconciliation"
      subtitle={`Exhibit 99.1 · distribution date ${distributions.report_date ?? 'not reported'}`}
    >
      <div className="mb-4 text-right">
        <a href={distributions.source_url} target="_blank" rel="noreferrer" className="link text-[11px]">
          View Exhibit 99.1
        </a>
      </div>
      <div className="grid grid-cols-2 gap-4 mb-5 lg:grid-cols-4">
        <Metric label="Ending scheduled collateral" value={money(reconciliation.ending_scheduled_collateral_balance)} />
        <Metric label="Ending collateral balance" value={money(reconciliation.ending_actual_collateral_balance)} />
        <Metric label="Ending certificate balance" value={money(reconciliation.ending_certificate_balance)} />
        <Metric label="Under / over-collateralization" value={money(reconciliation.under_over_collateralization)} />
      </div>

      {a1 && (
        <div className="rounded-md border border-border bg-bg-subtle px-4 py-3">
          <div className="flex items-baseline justify-between gap-3 mb-2">
            <span className="text-[12px] font-semibold text-text-hi">Class A-1</span>
            <span className="text-[11px] text-text-md">
              CUSIP {a1.cusip} · {a1.pass_through_rate == null ? 'Rate not reported' : fmtPct(Number(a1.pass_through_rate))}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-3 text-[12px]">
            <Metric label="Beginning" value={money(a1.beginning_balance)} />
            <Metric label="Principal distributed" value={money(a1.principal_distribution)} />
            <Metric label="Interest distributed" value={money(a1.interest_distribution)} />
          </div>
        </div>
      )}
    </Card>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-text-lo">{label}</div>
      <div className="mt-1 text-[13px] font-semibold text-text-hi num">{value}</div>
    </div>
  )
}
