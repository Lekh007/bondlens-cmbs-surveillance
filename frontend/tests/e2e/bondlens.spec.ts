import { test, expect, type Page } from '@playwright/test'

// Runs against a fixture BondLens API (page.route interception, not a real
// backend) so it stays fast and deterministic in CI. See docs/plans/
// implementation.md Task 16 Step 6 - this is the "against fixture server"
// pass; the "against local API" pass is a manual run with the real
// backend/frontend dev servers up and no route interception.

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
    entries: [{ state: 'NY', property_count: 31 }],
    total_properties: 31,
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

const CHAT_RESPONSE = {
  answer:
    'Between June and July, no property recorded a genuine NOI change - the deal is too young for meaningful property-level financial deterioration. Loan 30 (Cummins Station) is the one real surveillance signal: its payment status moved from A to B.',
  citations: [
    {
      source_name: 'sec_edgar',
      source_url: 'https://www.sec.gov/Archives/edgar/data/2110410/x/exh_102.xml',
      record_id: 'loan-30',
      field_path: 'paymentStatusLoanCode',
    },
  ],
  verification_passed: true,
}

async function mockBondLensApi(page: Page) {
  await page.route('**/api/bondlens/**', async (route) => {
    const url = new URL(route.request().url())

    if (route.request().method() === 'POST' && url.pathname === '/api/bondlens/chat') {
      await route.fulfill({ json: CHAT_RESPONSE })
      return
    }

    const body = FIXTURES[url.pathname]
    if (body === undefined) {
      await route.fulfill({ status: 404, json: { detail: 'not found' } })
      return
    }
    await route.fulfill({ json: body })
  })
}

test('BondLens flow: dashboard loads, comparison renders, chat cites a real SEC source', async ({
  page,
}) => {
  await mockBondLensApi(page)
  await page.goto('/bondlens')

  // Deal auto-selects (only one ingested deal) and the real dashboard loads.
  await expect(page.getByRole('combobox', { name: /select deal/i })).toContainText(
    'Benchmark 2026-B42 Mortgage Trust',
  )
  await expect(page.getByText('62', { exact: true })).toBeVisible()

  // Period comparison renders real before/after values.
  const comparisonCard = page.locator('#period-comparison')
  await expect(comparisonCard.getByText('paymentStatusLoanCode')).toBeVisible()
  await expect(comparisonCard.getByText('2026-06-11 → 2026-07-13')).toBeVisible()

  // Ask a golden question - including the negative one about property
  // deterioration, which the real deal data does not support.
  await page.getByRole('button', { name: /open bondlens analyst/i }).click()
  await page.getByPlaceholder(/ask about/i).fill('Which properties deteriorated most between May and July?')
  await page.getByPlaceholder(/ask about/i).press('Enter')

  await expect(page.getByText(/no property recorded a genuine noi change/i)).toBeVisible()

  // Open one SEC citation from the answer.
  await page.getByRole('button', { name: /loan-30/i }).click()
  const sourceLink = page.getByRole('link', { name: /open on sec edgar/i })
  await expect(sourceLink).toHaveAttribute(
    'href',
    'https://www.sec.gov/Archives/edgar/data/2110410/x/exh_102.xml',
  )
})
