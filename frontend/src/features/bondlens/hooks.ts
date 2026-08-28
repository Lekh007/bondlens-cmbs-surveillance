import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '@/api/client'
import {
  getBalanceDrift,
  getDealCompare,
  getDealSummary,
  getGeography,
  getIngestionJob,
  getPropertyTypes,
  getStatusChanges,
  listDeals,
  postChat,
  postIngestion,
} from '@/features/bondlens/api'

// A 404/422 from a not-yet-ingested or single-period deal is expected
// application state, not a fetch failure - callers branch on error.status
// rather than treating every error the same way.
function isExpectedDealState(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 404 || error.status === 422)
}

export function useDeals() {
  return useQuery({ queryKey: ['bondlens', 'deals'], queryFn: listDeals })
}

export function useDealSummary(dealId: string | null) {
  return useQuery({
    queryKey: ['bondlens', 'deal', dealId, 'summary'],
    queryFn: () => getDealSummary(dealId!),
    enabled: dealId != null,
    retry: (failureCount, error) => !isExpectedDealState(error) && failureCount < 1,
  })
}

export function useDealCompare(dealId: string | null) {
  return useQuery({
    queryKey: ['bondlens', 'deal', dealId, 'compare'],
    queryFn: () => getDealCompare(dealId!),
    enabled: dealId != null,
    retry: (failureCount, error) => !isExpectedDealState(error) && failureCount < 1,
  })
}

export function useGeography(dealId: string | null) {
  return useQuery({
    queryKey: ['bondlens', 'deal', dealId, 'geography'],
    queryFn: () => getGeography(dealId!),
    enabled: dealId != null,
  })
}

export function usePropertyTypes(dealId: string | null) {
  return useQuery({
    queryKey: ['bondlens', 'deal', dealId, 'property-types'],
    queryFn: () => getPropertyTypes(dealId!),
    enabled: dealId != null,
  })
}

export function useStatusChanges(dealId: string | null) {
  return useQuery({
    queryKey: ['bondlens', 'deal', dealId, 'status-changes'],
    queryFn: () => getStatusChanges(dealId!),
    enabled: dealId != null,
    retry: (failureCount, error) => !isExpectedDealState(error) && failureCount < 1,
  })
}

export function useBalanceDrift(dealId: string | null) {
  return useQuery({
    queryKey: ['bondlens', 'deal', dealId, 'balance-drift'],
    queryFn: () => getBalanceDrift(dealId!),
    enabled: dealId != null,
  })
}

export function useChat(dealId: string) {
  return useMutation({
    mutationFn: (question: string) => postChat(dealId, question),
  })
}

// Ingestion runs synchronously on the backend today (InMemoryJobQueue /
// RQJobQueue.perform_job both block until done), so this resolves once the
// job is already complete - no polling loop needed. It stays a mutation
// (not a query) because triggering an ingestion is a deliberate action.
export function useIngestDeal() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (cik: string) => {
      const job = await postIngestion(cik)
      if (job.status === 'queued' || job.status === 'running') {
        return getIngestionJob(job.job_id)
      }
      return job
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['bondlens', 'deals'] })
    },
  })
}
