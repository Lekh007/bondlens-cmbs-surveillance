import { z } from 'zod'
import { apiFetch } from '@/api/client'

// Schemas mirror backend/src/vichara_portfolio/bondlens/api.py response
// models exactly (field names and null-ability). Never format a missing
// value as a default - every optional field here is `.nullable()`, not
// `.optional().default(...)`, so a genuinely-absent ABS-EE field stays
// distinguishable from zero in the UI.

const dealListItemSchema = z.object({
  cik: z.string(),
  name: z.string(),
})
export type DealListItem = z.infer<typeof dealListItemSchema>

const dealSummarySchema = z.object({
  cik: z.string(),
  name: z.string(),
  loan_count: z.number(),
  property_count: z.number(),
  total_original_loan_amount: z.string(),
  total_actual_balance_amount: z.string(),
  reporting_period_ending_date: z.string().nullable(),
  source_url: z.string(),
})
export type DealSummary = z.infer<typeof dealSummarySchema>

const certificateDistributionItemSchema = z.object({
  class_name: z.string(),
  cusip: z.string(),
  pass_through_rate: z.string().nullable(),
  beginning_balance: z.string().nullable(),
  principal_distribution: z.string().nullable(),
  interest_distribution: z.string().nullable(),
  ending_balance: z.string().nullable(),
  source_url: z.string(),
})

const certificateDistributionResponseSchema = z.object({
  report_date: z.string().nullable(),
  source_url: z.string(),
  entries: z.array(certificateDistributionItemSchema),
})
export type CertificateDistributionResponse = z.infer<typeof certificateDistributionResponseSchema>

const bondCollateralReconciliationSchema = z.object({
  report_date: z.string().nullable(),
  ending_scheduled_collateral_balance: z.string().nullable(),
  beginning_actual_collateral_balance: z.string().nullable(),
  ending_actual_collateral_balance: z.string().nullable(),
  beginning_certificate_balance: z.string().nullable(),
  ending_certificate_balance: z.string().nullable(),
  under_over_collateralization: z.string().nullable(),
  source_url: z.string(),
})
export type BondCollateralReconciliation = z.infer<typeof bondCollateralReconciliationSchema>

const loanFieldChangeSchema = z.object({
  loan_asset_number: z.string(),
  field_name: z.string(),
  before_value: z.string().nullable(),
  after_value: z.string().nullable(),
})
export type LoanFieldChange = z.infer<typeof loanFieldChangeSchema>

const compareResponseSchema = z.object({
  period_a_ending_date: z.string().nullable(),
  period_b_ending_date: z.string().nullable(),
  changes: z.array(loanFieldChangeSchema),
})
export type CompareResponse = z.infer<typeof compareResponseSchema>

const geographyEntrySchema = z.object({
  state: z.string(),
  property_count: z.number(),
})

const geographyDistributionSchema = z.object({
  entries: z.array(geographyEntrySchema),
  total_properties: z.number(),
  properties_missing_state: z.number(),
})
export type GeographyDistribution = z.infer<typeof geographyDistributionSchema>

const propertyTypeEntrySchema = z.object({
  property_type_code: z.string(),
  property_count: z.number(),
})

const propertyTypeDistributionSchema = z.object({
  entries: z.array(propertyTypeEntrySchema),
  total_properties: z.number(),
  properties_missing_type: z.number(),
})
export type PropertyTypeDistribution = z.infer<typeof propertyTypeDistributionSchema>

const statusChangeEntrySchema = z.object({
  loan_asset_number: z.string(),
  property_names: z.array(z.string()),
  status_before: z.string().nullable(),
  status_after: z.string().nullable(),
  severity_rank: z.number(),
})

const statusChangeRankingSchema = z.object({
  entries: z.array(statusChangeEntrySchema),
  period_a_ending_date: z.string().nullable(),
  period_b_ending_date: z.string().nullable(),
})
export type StatusChangeRanking = z.infer<typeof statusChangeRankingSchema>

const balanceDriftEntrySchema = z.object({
  loan_asset_number: z.string(),
  property_names: z.array(z.string()),
  actual_balance_amount: z.string(),
  scheduled_balance_amount: z.string(),
  drift_amount: z.string(),
  drift_percentage: z.string().nullable(),
})

const balanceDriftRankingSchema = z.object({
  entries: z.array(balanceDriftEntrySchema),
  as_of_date: z.string().nullable(),
})
export type BalanceDriftRanking = z.infer<typeof balanceDriftRankingSchema>

const citationSchema = z.object({
  source_name: z.string(),
  source_url: z.string(),
  record_id: z.string().nullable(),
  field_path: z.string().nullable(),
})
export type Citation = z.infer<typeof citationSchema>

const chatResponseSchema = z.object({
  answer: z.string(),
  citations: z.array(citationSchema),
  verification_passed: z.boolean(),
})
export type ChatResponse = z.infer<typeof chatResponseSchema>

const ingestionJobSchema = z.object({
  job_id: z.string(),
  idempotency_key: z.string(),
  status: z.string(),
  progress: z.number(),
  error: z.object({ category: z.string(), message: z.string() }).nullable(),
  result: z.record(z.string(), z.unknown()).nullable(),
})
export type IngestionJob = z.infer<typeof ingestionJobSchema>

export function listDeals(): Promise<DealListItem[]> {
  return apiFetch('/api/bondlens/deals', z.array(dealListItemSchema))
}

export function getDealSummary(dealId: string): Promise<DealSummary> {
  return apiFetch(`/api/bondlens/deals/${dealId}/summary`, dealSummarySchema)
}

export function getCertificateDistributions(dealId: string): Promise<CertificateDistributionResponse> {
  return apiFetch(
    `/api/bondlens/deals/${dealId}/certificate-distributions`,
    certificateDistributionResponseSchema,
  )
}

export function getBondCollateralReconciliation(dealId: string): Promise<BondCollateralReconciliation> {
  return apiFetch(
    `/api/bondlens/deals/${dealId}/bond-collateral-reconciliation`,
    bondCollateralReconciliationSchema,
  )
}

export function getDealCompare(dealId: string): Promise<CompareResponse> {
  return apiFetch(`/api/bondlens/deals/${dealId}/compare`, compareResponseSchema)
}

export function getGeography(dealId: string): Promise<GeographyDistribution> {
  return apiFetch(`/api/bondlens/deals/${dealId}/geography`, geographyDistributionSchema)
}

export function getPropertyTypes(dealId: string): Promise<PropertyTypeDistribution> {
  return apiFetch(`/api/bondlens/deals/${dealId}/property-types`, propertyTypeDistributionSchema)
}

export function getStatusChanges(dealId: string): Promise<StatusChangeRanking> {
  return apiFetch(`/api/bondlens/deals/${dealId}/status-changes`, statusChangeRankingSchema)
}

export function getBalanceDrift(dealId: string): Promise<BalanceDriftRanking> {
  return apiFetch(`/api/bondlens/deals/${dealId}/balance-drift`, balanceDriftRankingSchema)
}

export function postChat(dealId: string, question: string): Promise<ChatResponse> {
  return apiFetch('/api/bondlens/chat', chatResponseSchema, {
    method: 'POST',
    body: JSON.stringify({ deal_id: dealId, question }),
  })
}

export function postIngestion(cik: string): Promise<IngestionJob> {
  return apiFetch('/api/bondlens/ingestions', ingestionJobSchema, {
    method: 'POST',
    body: JSON.stringify({ cik }),
  })
}

export function getIngestionJob(jobId: string): Promise<IngestionJob> {
  return apiFetch(`/api/bondlens/ingestions/${jobId}`, ingestionJobSchema)
}
