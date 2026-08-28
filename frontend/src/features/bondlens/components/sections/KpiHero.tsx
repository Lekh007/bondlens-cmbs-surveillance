import { Layers, Calendar } from 'lucide-react'
import type { DealSummary } from '@/features/bondlens/api'
import { fmtMoney, fmtNum } from '@/features/bondlens/lib/format'

interface Props {
  summary: DealSummary
}

// Only fields the backend's get_deal_summary actually computes from real
// ABS-EE data - no WAC/LTV/DSCR/cum-loss, since those aren't modeled by
// BondLens's loan/property domain (see analytics.py DealSummary).
export function KpiHero({ summary }: Props) {
  const original = Number(summary.total_original_loan_amount)
  const actual = Number(summary.total_actual_balance_amount)
  const paydownPct = original > 0 ? ((original - actual) / original) * 100 : null

  return (
    <section id="overview" className="grid grid-cols-4 gap-3">
      <div className="kpi">
        <div className="kpi-label">Loan Count</div>
        <div className="kpi-value num">{fmtNum(summary.loan_count)}</div>
        <div className="kpi-foot">
          <span className="text-[10.5px] text-text-lo num">
            {fmtNum(summary.property_count)} properties
          </span>
          <Layers size={13} strokeWidth={1.6} className="text-text-lo" />
        </div>
      </div>

      <div className="kpi">
        <div className="kpi-label">Actual Balance</div>
        <div className="kpi-value num">{fmtMoney(actual)}</div>
        <div className="kpi-foot">
          <span className="text-[10.5px] text-text-lo num">{fmtMoney(original)} original</span>
        </div>
      </div>

      <div className="kpi">
        <div className="kpi-label">Paydown Since Issuance</div>
        <div className="kpi-value num">
          {paydownPct === null ? '—' : `${paydownPct.toFixed(2)}%`}
        </div>
        <div className="kpi-foot">
          <span className="text-[10.5px] text-text-lo">of original balance</span>
        </div>
      </div>

      <div className="kpi">
        <div className="kpi-label">Latest Reporting Period</div>
        <div className="kpi-value num">{summary.reporting_period_ending_date ?? '—'}</div>
        <div className="kpi-foot">
          <Calendar size={13} strokeWidth={1.6} className="text-text-lo" />
        </div>
      </div>
    </section>
  )
}
