export type SourceVersion = {
  source_id: string
  name: string
  media_type: string
  parser: string
  status: 'ready' | 'partial' | 'failed'
  quality_score: number
  element_count: number
  chunk_count: number
  warnings: string[]
}

export type StoreCapability = {
  name: string
  implemented: boolean
  description: string
}

export type Health = {
  status: string
  service: string
  embedding_model: string
  embedding_fallback: boolean
  indexed_chunks: number
  available_vector_stores: StoreCapability[]
}

export type Citation = {
  label: string
  source_name: string
  excerpt: string
  page?: number | null
  slide?: number | null
  sheet?: string | null
  cell_range?: string | null
  json_path?: string | null
}

export type QueryResponse = {
  answer: string
  citations: Citation[]
  insufficient_evidence: boolean
  validator_messages: string[]
  trace: {
    profile: string
    vector_store: string
    fused_candidates: number
    final_context_chunks: number
    retrieval_ms: number
    generation_ms: number
    total_ms: number
    embedding_model: string
    embedding_fallback: boolean
  }
}

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) throw new Error((await response.text()) || `Request failed (${response.status})`)
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<Health>('/health'),
  sources: () => request<SourceVersion[]>('/sources'),
  query: (question: string, profile: string) =>
    request<QueryResponse>('/queries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, profile, vector_store: 'faiss', top_k: 6 }),
    }),
  ingest: (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<SourceVersion>('/ingestions', { method: 'POST', body })
  },
}
