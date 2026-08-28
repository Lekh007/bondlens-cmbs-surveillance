import { useEffect, useState } from 'react'
import { CheckCircle2 } from 'lucide-react'

import '@/features/bondlens/bondlens.css'

import { TopBar } from '@/features/bondlens/components/TopBar'
import { TabBar } from '@/features/bondlens/components/TabBar'
import { Sidebar } from '@/features/bondlens/components/Sidebar'
import { DealSelector } from '@/features/bondlens/components/DealSelector'
import { PeriodComparison } from '@/features/bondlens/components/PeriodComparison'

import { KpiHero } from '@/features/bondlens/components/sections/KpiHero'
import { FocusDelinquency } from '@/features/bondlens/components/sections/FocusDelinquency'
import { PropertyTypeDistribution } from '@/features/bondlens/components/sections/PropertyTypeDistribution'
import { Geography } from '@/features/bondlens/components/sections/Geography'
import { BalanceMaturityLosses } from '@/features/bondlens/components/sections/BalanceMaturityLosses'

import { ChatLauncher } from '@/features/bondlens/components/chat/ChatLauncher'
import { ChatPanel } from '@/features/bondlens/components/chat/ChatPanel'

import {
  useBalanceDrift,
  useDealCompare,
  useDealSummary,
  useGeography,
  usePropertyTypes,
  useStatusChanges,
} from '@/features/bondlens/hooks'

type Density = 'comfy' | 'compact'

export function BondLensPage() {
  const [density, setDensity] = useState<Density>(() => {
    try {
      return (localStorage.getItem('vichara_density') as Density) ?? 'comfy'
    } catch {
      return 'comfy'
    }
  })
  const [chatOpen, setChatOpen] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [selectedDealId, setSelectedDealId] = useState<string | null>(null)

  useEffect(() => {
    document.documentElement.classList.toggle('compact', density === 'compact')
    try {
      localStorage.setItem('vichara_density', density)
    } catch {
      // ignore storage failures (private browsing, quota)
    }
  }, [density])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 2400)
    return () => clearTimeout(t)
  }, [toast])

  const summaryQuery = useDealSummary(selectedDealId)
  const compareQuery = useDealCompare(selectedDealId)
  const geographyQuery = useGeography(selectedDealId)
  const propertyTypesQuery = usePropertyTypes(selectedDealId)
  const statusChangesQuery = useStatusChanges(selectedDealId)
  const balanceDriftQuery = useBalanceDrift(selectedDealId)

  const dealName = summaryQuery.data?.name ?? ''

  return (
    <>
      <TopBar
        density={density}
        onDensityChange={setDensity}
        onExport={() => setToast('Export started — Excel')}
        dealSelector={<DealSelector selectedDealId={selectedDealId} onSelect={setSelectedDealId} />}
      />
      <TabBar />

      <div className="flex">
        <Sidebar />

        <main className="flex-1 px-8 py-6 max-w-[1440px] mx-auto space-y-6" style={{ width: 0 }}>
          {!selectedDealId && (
            <div className="card p-6 text-center text-[13px] text-text-md">
              Select or ingest a deal above to see BondLens surveillance data.
            </div>
          )}

          {selectedDealId && summaryQuery.isPending && (
            <div className="card p-6 text-center text-[13px] text-text-md">Loading deal summary…</div>
          )}

          {selectedDealId && summaryQuery.isError && (
            <div className="card p-6 text-center text-[13px] text-loss">
              This deal has been ingested but has no loan data yet.
            </div>
          )}

          {selectedDealId && summaryQuery.data && (
            <>
              <div>
                <h1 className="text-[22px] font-semibold tracking-tight text-text-hi">
                  {summaryQuery.data.name}
                </h1>
                <div className="text-[13px] text-text-md mt-0.5">
                  CIK {summaryQuery.data.cik} · loan-level CMBS ABS-EE surveillance
                </div>
              </div>

              <KpiHero summary={summaryQuery.data} />

              <PeriodComparison compare={compareQuery.data ?? null} isLoading={compareQuery.isPending} />

              <FocusDelinquency ranking={statusChangesQuery.data ?? null} />

              {balanceDriftQuery.data && <BalanceMaturityLosses ranking={balanceDriftQuery.data} />}

              <div className="grid grid-cols-2 gap-6">
                {propertyTypesQuery.data && (
                  <PropertyTypeDistribution distribution={propertyTypesQuery.data} />
                )}
                {geographyQuery.data && <Geography distribution={geographyQuery.data} />}
              </div>

              <footer className="text-[11px] text-text-lo text-center pb-8 pt-2">
                BondLens · {summaryQuery.data.name} · source: SEC EDGAR ABS-EE ·{' '}
                <a href={summaryQuery.data.source_url} target="_blank" rel="noreferrer" className="link">
                  view latest filing
                </a>
              </footer>
            </>
          )}
        </main>
      </div>

      <ChatLauncher onClick={() => setChatOpen(true)} hidden={chatOpen} />
      <ChatPanel
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        dealId={selectedDealId}
        dealName={dealName}
      />

      {toast && (
        <div className="toast">
          <CheckCircle2 size={15} strokeWidth={1.8} />
          {toast}
        </div>
      )}
    </>
  )
}
