import { useEffect, useState } from 'react'
import { CheckCircle2, ChevronRight } from 'lucide-react'

import '@/features/bondlens/bondlens.css'

import { TopBar } from '@/features/bondlens/components/TopBar'
import { TabBar } from '@/features/bondlens/components/TabBar'
import { Sidebar } from '@/features/bondlens/components/Sidebar'

import { KpiHero } from '@/features/bondlens/components/sections/KpiHero'
import { DealOverview } from '@/features/bondlens/components/sections/DealOverview'
import { ScenarioAnalysis } from '@/features/bondlens/components/sections/ScenarioAnalysis'
import { BondsTable } from '@/features/bondlens/components/sections/BondsTable'
import { FocusDelinquency } from '@/features/bondlens/components/sections/FocusDelinquency'
import { PropertyTypeDistribution } from '@/features/bondlens/components/sections/PropertyTypeDistribution'
import { Geography } from '@/features/bondlens/components/sections/Geography'
import { BalanceMaturityLosses } from '@/features/bondlens/components/sections/BalanceMaturityLosses'
import { LeaseRollover } from '@/features/bondlens/components/sections/LeaseRollover'
import { ServicerCommentary } from '@/features/bondlens/components/sections/ServicerCommentary'

import { ChatLauncher } from '@/features/bondlens/components/chat/ChatLauncher'
import { ChatPanel } from '@/features/bondlens/components/chat/ChatPanel'

type Density = 'comfy' | 'compact'

// This is the reference wireframe shell copied mechanically from
// wiki/analyses/vichara-cmbs-react (Task 15 Step 1) and adapted only to fit
// the router/providers scaffold. It is still fixture-driven - real BondLens
// API wiring (deal summary, period comparison, cited chat) replaces the
// static deal.ts data and canned chat responses in Task 16.
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

  const showToast = (msg: string) => setToast(msg)

  return (
    <>
      <TopBar
        density={density}
        onDensityChange={setDensity}
        onRunJob={(n) => showToast(`${n} run started · wireframe demo`)}
        onExport={() => showToast('Export started — Excel')}
      />
      <TabBar />

      <div className="flex">
        <Sidebar />

        <main className="flex-1 px-8 py-6 max-w-[1440px] mx-auto space-y-6" style={{ width: 0 }}>
          <div className="flex items-end justify-between">
            <div>
              <div className="flex items-center gap-1.5 text-[12px] text-text-md mb-1">
                <span>Deals</span>
                <ChevronRight size={12} strokeWidth={1.8} />
                <span>Conduit</span>
                <ChevronRight size={12} strokeWidth={1.8} />
                <span className="text-text-hi font-medium">MSC 2019-L3</span>
              </div>
              <h1 className="text-[22px] font-semibold tracking-tight text-text-hi">
                Underwriting Information for MSC&nbsp;2019-L3
              </h1>
              <div className="text-[13px] text-text-md mt-0.5">
                51 loans &middot; $960.3M outstanding &middot; Conduit &middot; Wells Fargo Bank
                (MS) &middot; Wilmington Trust (Trustee)
              </div>
            </div>
            <div className="text-right text-[12px] text-text-md">
              <div>
                Auto-UW completed <span className="text-text-hi font-medium">5/3/2024 10:50 PM</span>
              </div>
              <div>
                Intex update <span className="text-text-hi font-medium">5/1/2026</span>
              </div>
            </div>
          </div>

          <KpiHero />
          <DealOverview />
          <ScenarioAnalysis />
          <BondsTable />
          <FocusDelinquency />
          <PropertyTypeDistribution />
          <Geography />
          <BalanceMaturityLosses />
          <LeaseRollover />
          <ServicerCommentary />

          <footer className="text-[11px] text-text-lo text-center pb-8 pt-2">
            Vichara Bond Viewer &middot; MSC 2019-L3 &middot; Wireframe prototype &middot; Data as
            of 5/3/2024
          </footer>
        </main>
      </div>

      <ChatLauncher onClick={() => setChatOpen(true)} hidden={chatOpen} />
      <ChatPanel open={chatOpen} onClose={() => setChatOpen(false)} />

      {toast && (
        <div className="toast">
          <CheckCircle2 size={15} strokeWidth={1.8} />
          {toast}
        </div>
      )}
    </>
  )
}
