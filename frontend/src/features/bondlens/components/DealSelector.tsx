import { useEffect } from 'react'
import { RefreshCw } from 'lucide-react'
import { useDeals, useIngestDeal } from '@/features/bondlens/hooks'

// The demo deal's CIK is fixed (Benchmark 2026-B42, per design.md section
// 0) - there is no deal search/lookup endpoint, so "ingest" here means
// "(re)ingest the one deal this portfolio demo covers."
const DEMO_CIK = '0002110410'

interface Props {
  selectedDealId: string | null
  onSelect: (dealId: string) => void
}

export function DealSelector({ selectedDealId, onSelect }: Props) {
  const dealsQuery = useDeals()
  const ingest = useIngestDeal()

  // Auto-select the first deal once the list loads (or right after an
  // ingestion completes and the list refetches) - a native <select> with a
  // controlled value that matches no <option> silently falls back to
  // displaying the first option without actually firing onChange, so
  // without this the dashboard stayed on its empty state even though the
  // dropdown visibly showed the ingested deal (found via live browser
  // verification, 2026-08-29).
  useEffect(() => {
    if (selectedDealId == null && dealsQuery.data && dealsQuery.data.length > 0) {
      onSelect(dealsQuery.data[0].cik)
    }
  }, [selectedDealId, dealsQuery.data, onSelect])

  if (dealsQuery.isPending) {
    return <div className="deal-selector">Loading deals…</div>
  }

  if (dealsQuery.isError) {
    return <div className="deal-selector">Could not load deals</div>
  }

  if (dealsQuery.data.length === 0) {
    return (
      <button
        className="deal-selector"
        onClick={() => ingest.mutate(DEMO_CIK)}
        disabled={ingest.isPending}
      >
        {ingest.isPending ? (
          <>
            <RefreshCw size={13} className="animate-spin" />
            Ingesting Benchmark 2026-B42…
          </>
        ) : (
          'Ingest Benchmark 2026-B42'
        )}
      </button>
    )
  }

  return (
    <select
      className="deal-selector"
      value={selectedDealId ?? ''}
      onChange={(e) => onSelect(e.target.value)}
      aria-label="Select deal"
    >
      {dealsQuery.data.map((d) => (
        <option key={d.cik} value={d.cik}>
          {d.name}
        </option>
      ))}
    </select>
  )
}
