export type Rating = 'AAA' | 'AA' | 'A' | 'BBB' | 'BB' | 'B' | 'NA';

export interface Tranche {
  cusip: string;
  cls: string;
  rating: Rating;
  origBalance: number;
  currentBalance: number;
  factor: number;
  coupon: number | null;
  wal: number | null;
  cePct: number;
  defCePct: number;
  shortCum: number;
  shortCurr: number;
  purchPrice?: number;
  holding?: number;
  pctFace?: number;
  kbraLoss?: number;
  kbraCe?: number;
  kbraIrr?: number;
  kbraMoc?: number;
  group: 'senior' | 'io' | 'others';
}

export interface Scenario {
  name: string;
  family: 'rating-agency' | 'auto-uw' | 'dealer';
  origPct: number;
  currPct: number;
  irr?: [number, number, number]; // AS, B, C
}

export interface PropertyTypeRow {
  type: string;
  loans: number;
  balance: number;
  pct: number;
}

export interface GeoRow {
  loc: string;
  balance: number;
  pct: number;
}

export interface LeaseRow {
  tenant: string;
  sf: number;
  tenantPct: number;
  expDate: string;
  loanName: string;
  property: string;
  propertyType: string;
  city: string;
  balance: number;
  psf: number;
  loanMaturity: string;
  months: number;
}

export interface LeaseGroup {
  label: string;
  rangeMonths: string;
  totalTenants: number;
  totalSf: number;
  totalBalance: number;
  rows: LeaseRow[];
  severity: 'loss' | 'warn' | 'gain';
}

export interface ServicerKeyword {
  keyword: string;
  loans: number;
  balance: number;
  pct: number;
  severity: 'gain' | 'warn' | 'loss' | 'info' | 'brand' | 'neutral';
}

export interface DealOverview {
  bbgName: string;
  lastUpdate: string;
  type: string;
  firstSettle: string;
  trustee: string;
  masterServicer: string;
  specialServicer: string;
  bPieceBuyer: string;
  riskRetention: string;
  currCumLoss: number;
  locPct: number;
  projCumLoss: number;
}

export interface PortfolioMetrics {
  numLoansOrig: number;
  numLoansCurr: number | null;
  totalBalanceOrig: number;
  totalBalanceCurr: number;
  avgBalanceOrig: number;
  avgBalanceCurr: number;
  wacOrig: number;
  wacCurr: number;
  waLtvOrig: number;
  waLtvCurr: number;
  waDscrOrig: number;
  waDscrCurr: number;
  currCumLossOrig: number;
  currCumLossCurr: number;
  projCumLossCurr: number;
}

export type DelinquencyStatus =
  | 'Current'
  | '<1 Month'
  | '30 Days'
  | '60 Days'
  | '90+ Days'
  | 'Foreclosure'
  | 'REO'
  | 'Grace / Not yet due'
  | 'NonPerfMatBall'
  | 'Unknown';

export interface ChatMessage {
  id: string;
  role: 'user' | 'ai';
  text: string;
  payload?: ChatPayload;
}

export type ChatPayload =
  | { kind: 'kpis'; items: { label: string; value: string; delta?: string }[] }
  | {
      kind: 'table';
      columns: string[];
      rows: (string | number)[][];
    }
  | { kind: 'comparison'; rows: { name: string; color: string; metrics: { label: string; value: string }[] }[] }
  | { kind: 'chart'; title: string; bars: { label: string; value: number; color: string }[] }
  | { kind: 'download'; filename: string; size: string };
