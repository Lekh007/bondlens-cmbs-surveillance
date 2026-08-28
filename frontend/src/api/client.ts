import type { ZodType } from 'zod'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export class ApiError extends Error {
  readonly status: number | null
  readonly kind: 'network' | 'http' | 'schema'

  constructor(message: string, kind: 'network' | 'http' | 'schema', status: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
  }
}

/**
 * Fetches `path` and validates the JSON body against `schema`. Never
 * returns malformed data silently: a non-2xx response, a body that isn't
 * JSON, or a body that fails schema validation all raise a typed ApiError
 * the UI can render distinctly from an empty/loading state.
 */
export async function apiFetch<T>(
  path: string,
  schema: ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError(
      `Could not reach the BondLens API at ${API_BASE_URL}${path}`,
      'network',
    )
  }

  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new ApiError(
      `BondLens API returned ${response.status} for ${path}${detail ? `: ${detail}` : ''}`,
      'http',
      response.status,
    )
  }

  const body: unknown = await response.json().catch(() => {
    throw new ApiError(`BondLens API returned non-JSON for ${path}`, 'schema', response.status)
  })

  const parsed = schema.safeParse(body)
  if (!parsed.success) {
    throw new ApiError(
      `BondLens API response for ${path} did not match the expected shape: ${parsed.error.message}`,
      'schema',
      response.status,
    )
  }
  return parsed.data
}
