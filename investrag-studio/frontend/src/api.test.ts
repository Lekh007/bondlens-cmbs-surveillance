import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from './api'

describe('InvestRAG API client', () => {
  afterEach(() => vi.restoreAllMocks())

  it('posts a query to the local evidence endpoint', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ answer: 'grounded', citations: [] }), { status: 200 }),
    )

    await api.query('What changed?', 'hybrid')

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/v1/queries',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
