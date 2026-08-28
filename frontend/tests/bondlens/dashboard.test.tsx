import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { BondLensPage } from '@/features/bondlens/BondLensPage'

const DEAL_ID = '0002110410'

const FIXTURES: Record<string, unknown> = {
  '/api/bondlens/deals': [{ cik: DEAL_ID, name: 'Benchmark 2026-B42 Mortgage Trust' }],
  [`/api/bondlens/deals/${DEAL_ID}/summary`]: {
    cik: DEAL_ID,
    name: 'Benchmark 2026-B42 Mortgage Trust',
    loan_count: 62,
    property_count: 123,
    total_original_loan_amount: '729839000.00000000',
    total_actual_balance_amount: '728470251.29000000',
    reporting_period_ending_date: '2026-07-13',
    source_url: 'https://www.sec.gov/Archives/edgar/data/2110410/x/exh_102.xml',
  },
  [`/api/bondlens/deals/${DEAL_ID}/compare`]: {
    period_a_ending_date: '2026-06-11',
    period_b_ending_date: '2026-07-13',
    changes: [
      {
        loan_asset_number: '30',
        field_name: 'paymentStatusLoanCode',
        before_value: 'A',
        after_value: 'B',
      },
    ],
  },
  [`/api/bondlens/deals/${DEAL_ID}/geography`]: {
    entries: [
      { state: 'NY', property_count: 31 },
      { state: 'CA', property_count: 13 },
    ],
    total_properties: 44,
    properties_missing_state: 0,
  },
  [`/api/bondlens/deals/${DEAL_ID}/property-types`]: {
    entries: [{ property_type_code: 'SS', property_count: 52 }],
    total_properties: 52,
    properties_missing_type: 0,
  },
  [`/api/bondlens/deals/${DEAL_ID}/status-changes`]: {
    entries: [
      {
        loan_asset_number: '30',
        property_names: ['Cummins Station'],
        status_before: 'A',
        status_after: 'B',
        severity_rank: 2,
      },
    ],
    period_a_ending_date: '2026-06-11',
    period_b_ending_date: '2026-07-13',
  },
  [`/api/bondlens/deals/${DEAL_ID}/balance-drift`]: {
    entries: [
      {
        loan_asset_number: '1',
        property_names: ['Some Property'],
        actual_balance_amount: '900000.00',
        scheduled_balance_amount: '905000.00',
        drift_amount: '-5000.00',
        drift_percentage: '-0.55',
      },
    ],
    as_of_date: '2026-07-13',
  },
}

function stubFetch() {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      const path = new URL(url).pathname
      const body = FIXTURES[path]
      if (body === undefined) {
        return Promise.resolve(new Response('not found', { status: 404 }))
      }
      return Promise.resolve(
        new Response(JSON.stringify(body), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    }),
  )
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <BondLensPage />
    </QueryClientProvider>,
  )
}

describe('BondLensPage dashboard', () => {
  it('loads the real deal list and lets the user select one', async () => {
    stubFetch()
    renderPage()

    const select = await screen.findByRole('combobox', { name: /select deal/i })
    expect(select).toHaveTextContent('Benchmark 2026-B42 Mortgage Trust')
  })

  it('auto-selects the only deal without requiring a manual dropdown interaction', async () => {
    // Regression test for a real bug (2026-08-29, live browser
    // verification): a controlled <select> whose value matched no <option>
    // silently displayed the first option without firing onChange, so the
    // dashboard stayed on its empty state even though the deal was loaded.
    stubFetch()
    renderPage()

    expect(await screen.findByText('62')).toBeInTheDocument() // loan_count, no click needed
    expect(screen.queryByText(/select or ingest a deal/i)).not.toBeInTheDocument()
  })

  it('renders real KPI numbers from the deal summary, never inventing figures', async () => {
    stubFetch()
    const user = userEvent.setup()
    renderPage()

    const select = await screen.findByRole('combobox', { name: /select deal/i })
    await user.selectOptions(select, DEAL_ID)

    expect(await screen.findByText('62')).toBeInTheDocument() // loan_count
    expect(await screen.findByText(/123 properties/i)).toBeInTheDocument()
    expect(await screen.findByText('2026-07-13')).toBeInTheDocument()
  })

  it('renders the period comparison with real before/after values', async () => {
    stubFetch()
    const user = userEvent.setup()
    renderPage()

    const select = await screen.findByRole('combobox', { name: /select deal/i })
    await user.selectOptions(select, DEAL_ID)

    const fieldCell = await screen.findByText('paymentStatusLoanCode')
    const comparisonCard = fieldCell.closest('article')
    expect(comparisonCard).not.toBeNull()
    expect(comparisonCard!.textContent).toContain('2026-06-11')
    expect(comparisonCard!.textContent).toContain('2026-07-13')
    expect(within(comparisonCard!).getByText('A')).toBeInTheDocument()
    expect(within(comparisonCard!).getByText('B')).toBeInTheDocument()
  })

  it('renders geography and property-type distributions by property count, not invented balances', async () => {
    stubFetch()
    const user = userEvent.setup()
    renderPage()

    const select = await screen.findByRole('combobox', { name: /select deal/i })
    await user.selectOptions(select, DEAL_ID)

    const geographyCard = (await screen.findByText('NY')).closest('article')
    const propertyTypeCard = (await screen.findByText('SS')).closest('article')
    expect(geographyCard).not.toBeNull()
    expect(propertyTypeCard).not.toBeNull()
    // Neither card renders a dollar balance - that data isn't in the
    // geography/property-type API responses, so a $ figure would be invented.
    expect(within(geographyCard!).queryByText(/^\$/)).not.toBeInTheDocument()
    expect(within(propertyTypeCard!).queryByText(/^\$/)).not.toBeInTheDocument()
  })

  it('shows an explicit empty state before any deal is selected', () => {
    stubFetch()
    renderPage()

    expect(screen.getByText(/select or ingest a deal/i)).toBeInTheDocument()
  })
})
