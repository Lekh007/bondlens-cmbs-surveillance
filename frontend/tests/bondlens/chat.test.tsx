import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ChatPanel } from '@/features/bondlens/components/chat/ChatPanel'

const DEAL_ID = '0002110410'

function stubChatFetch(handler: (body: unknown) => Response) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      expect(new URL(url).pathname).toBe('/api/bondlens/chat')
      const body = init?.body ? JSON.parse(init.body as string) : undefined
      return handler(body)
    }),
  )
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function renderChat() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ChatPanel open onClose={() => {}} dealId={DEAL_ID} dealName="Benchmark 2026-B42 Mortgage Trust" />
    </QueryClientProvider>,
  )
}

async function ask(question: string) {
  const user = userEvent.setup()
  const input = screen.getByPlaceholderText(/ask about/i)
  await user.type(input, question)
  await user.keyboard('{Enter}')
}

describe('ChatPanel', () => {
  it('shows a pending state while the question is in flight', async () => {
    let resolveFetch: (r: Response) => void = () => {}
    vi.stubGlobal(
      'fetch',
      vi.fn(
        () =>
          new Promise<Response>((resolve) => {
            resolveFetch = resolve
          }),
      ),
    )

    renderChat()
    await ask('What changed?')

    expect(await screen.findByText(/thinking/i)).toBeInTheDocument()

    resolveFetch(
      jsonResponse({ answer: 'Answer text', citations: [], verification_passed: true }),
    )
  })

  it('renders the real answer text and citation from the backend - no canned response', async () => {
    stubChatFetch(() =>
      jsonResponse({
        answer: 'Loan 30 moved from status A to status B between June and July.',
        citations: [
          {
            source_name: 'sec_edgar',
            source_url: 'https://www.sec.gov/Archives/edgar/data/2110410/x/exh_102.xml',
            record_id: 'loan-30',
            field_path: 'paymentStatusLoanCode',
          },
        ],
        verification_passed: true,
      }),
    )

    renderChat()
    await ask('What changed for loan 30?')

    expect(
      await screen.findByText(/loan 30 moved from status a to status b/i),
    ).toBeInTheDocument()
    // Never the old canned-response bot identity/copy.
    expect(screen.queryByText(/bond viewer ai/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/msc 2019-l3/i)).not.toBeInTheDocument()

    expect(await screen.findByRole('button', { name: /loan-30/i })).toBeInTheDocument()
  })

  it('opens the evidence drawer with the SEC source link when a citation is clicked', async () => {
    stubChatFetch(() =>
      jsonResponse({
        answer: 'Loan 30 moved to status B.',
        citations: [
          {
            source_name: 'sec_edgar',
            source_url: 'https://www.sec.gov/Archives/edgar/data/2110410/x/exh_102.xml',
            record_id: 'loan-30',
            field_path: 'paymentStatusLoanCode',
          },
        ],
        verification_passed: true,
      }),
    )

    renderChat()
    await ask('What changed for loan 30?')

    const citationChip = await screen.findByRole('button', { name: /loan-30/i })
    const user = userEvent.setup()
    await user.click(citationChip)

    const link = await screen.findByRole('link', { name: /open on sec edgar/i })
    expect(link).toHaveAttribute(
      'href',
      'https://www.sec.gov/Archives/edgar/data/2110410/x/exh_102.xml',
    )
  })

  it('shows a controlled model-unavailable message on a 503, not a generic crash', async () => {
    stubChatFetch(() => jsonResponse({ detail: 'model provider is unavailable' }, 503))

    renderChat()
    await ask('What changed?')

    expect(await screen.findByText(/model is currently unavailable/i)).toBeInTheDocument()
  })

  it('shows a warning when verification did not pass, without hiding the answer', async () => {
    stubChatFetch(() =>
      jsonResponse({
        answer: 'An answer that failed the mechanical verification check.',
        citations: [],
        verification_passed: false,
      }),
    )

    renderChat()
    await ask('What changed?')

    expect(await screen.findByText(/failed the mechanical verification/i)).toBeInTheDocument()
    expect(screen.getByText(/did not pass automatic verification/i)).toBeInTheDocument()
  })
})
