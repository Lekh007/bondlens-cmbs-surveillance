import type { ChatMessage, ChatPayload } from '@/features/bondlens/types';

interface Canned {
  /** Regex patterns that must match (any one) */
  match: RegExp[];
  text: string;
  payload?: ChatPayload;
}

export const CANNED: Canned[] = [
  // ============================== DSCR / metrics ==============================
  {
    match: [/dscr|debt service/i],
    text:
      'MSC 2019-L3 has a **WA DSCR of 2.63x** (current) vs **2.18x** at issuance — an improvement of +0.45x driven by net cash flow recovery across hotel and multifamily loans. The Mixed (Retail/Office) and Industrial segments anchor the strongest DSCR contributions.',
    payload: {
      kind: 'kpis',
      items: [
        { label: 'WA DSCR · Current', value: '2.63x', delta: '+0.45x' },
        { label: 'WA DSCR · Original', value: '2.18x' },
        { label: 'WAC', value: '3.70%', delta: '+9 bp' },
        { label: 'WA LTV', value: '59.29%', delta: '+64 bp' },
      ],
    },
  },

  // ============================== Total balance / overview ==============================
  {
    match: [/total balance|outstanding|deal size|how (big|much)/i],
    text:
      'MSC 2019-L3 is a 2019-vintage Conduit deal with **$960.3M outstanding** across **51 loans** (originally $1.02B). Master Servicer is Wells Fargo Bank, Trustee is Wilmington Trust. Risk-retention is L-shape with Starwood as the B-piece buyer.',
    payload: {
      kind: 'kpis',
      items: [
        { label: 'Total Balance', value: '$960.3M', delta: '−6.0% vs orig' },
        { label: '# of Loans', value: '51' },
        { label: 'Deal Type', value: 'Conduit' },
        { label: 'Vintage', value: '2019' },
      ],
    },
  },

  // ============================== NY / state concentration ==============================
  {
    match: [/\bny\b|new york|state concentration|geographic/i],
    text:
      'New York is the largest state concentration at **15.89% of the pool ($152.6M)**. Two NY properties carry $60.5M and $59.6M respectively. California (11.71%) and Florida (9.06%) round out the top three.',
    payload: {
      kind: 'table',
      columns: ['State', 'Balance', '% of Pool'],
      rows: [
        ['New York · NY', '$152,600,000', '15.89%'],
        ['California · CA', '$112,478,439', '11.71%'],
        ['Florida · FL', '$87,028,928', '9.06%'],
        ['Maryland · MD', '$72,696,525', '7.57%'],
        ['Nevada · NV', '$72,347,331', '7.53%'],
      ],
    },
  },

  // ============================== Scenario comparison ==============================
  {
    match: [/compare.*kbra|kbra.*vs|scenario.*compare|upside.*downside/i],
    text:
      'Comparing **KBRA_Concluded** vs **OCM_AUW_Upside_P3** — KBRA projects a meaningfully higher cumulative loss (79.67% vs 10.22%) because rating agencies use deeper stress assumptions. Both scenarios land at similar IRR for AS (8.3%) but diverge on Class C, where KBRA shows 11.8% vs OCM Upside at 9.7%.',
    payload: {
      kind: 'comparison',
      rows: [
        {
          name: 'KBRA_Concluded',
          color: '#1E3A8A',
          metrics: [
            { label: 'Cum Loss', value: '79.67%' },
            { label: 'AS IRR', value: '8.3%' },
            { label: 'B IRR', value: '9.8%' },
            { label: 'C IRR', value: '11.8%' },
          ],
        },
        {
          name: 'OCM_AUW_Upside_P3',
          color: '#15803D',
          metrics: [
            { label: 'Cum Loss', value: '10.22%' },
            { label: 'AS IRR', value: '8.3%' },
            { label: 'B IRR', value: '9.8%' },
            { label: 'C IRR', value: '9.7%' },
          ],
        },
      ],
    },
  },

  // ============================== Property type concentration ==============================
  {
    match: [/property type|property concentration|mixed|multifamily|office concentration/i],
    text:
      'The collateral is heavily diversified across 25 property types. **Mixed (Retail/Office) leads at 23.66%** ($227M, 7 loans), followed by Multi Family at 20.45% ($196M, 11 loans). The portfolio is meaningfully overweight non-pure office collateral.',
    payload: {
      kind: 'chart',
      title: 'Top 6 Property Types · Balance % of Pool',
      bars: [
        { label: 'Mixed (R/O)',    value: 23.66, color: '#1E3A8A' },
        { label: 'Multi Family',   value: 20.45, color: '#2563EB' },
        { label: 'Office',         value: 19.77, color: '#3B82F6' },
        { label: 'Retail',         value: 16.63, color: '#A16207' },
        { label: 'Garden',         value: 15.89, color: '#15803D' },
        { label: 'Suburban',       value: 12.27, color: '#7C3AED' },
      ],
    },
  },

  // ============================== Loans / tranches over X ==============================
  {
    match: [/loan.*over|loan.*greater|tranche.*over|maturing/i],
    text:
      '**5 loans carry $50M+ outstanding**, totaling $310M (32% of the pool). Most are concentrated in the ILPT Industrial Portfolio and GNL Office/Industrial portfolios. None of these are flagged for special servicing.',
    payload: {
      kind: 'table',
      columns: ['Loan', 'Balance', 'Maturity'],
      rows: [
        ['East Village Multifamily Por', '$60,500,000', '10/06/29'],
        ['ILPT Industrial Portfolio (×3)', '$150,000,000', '11/07/29'],
        ['GNL Office and Industrial (×3)', '$132,567,693', '10/01/29'],
        ['Victory Food Lion Portfolio (×3)', '$27,311,367', '10/01/29'],
        ['9174 Sky Park Court', '$6,000,000', '10/01/29'],
      ],
    },
  },

  // ============================== Lease rollover risk ==============================
  {
    match: [/lease.*roll|lease.*expir|tenant.*expir|rollover/i],
    text:
      '**4 tenants on $204.7M of collateral expire within 12 months** — Amazon at Whitestown is the largest exposure (100% of property SF), followed by AT&T San Antonio (100%) and Cummins Walton (100%). Sage The Cat (44% of 165-167 Avenue A) is a smaller secondary risk.',
    payload: {
      kind: 'table',
      columns: ['Tenant', 'SF', 'Exp Date', 'Loan Balance', 'Months'],
      rows: [
        ['AT&T',          '401,516',   '07/17/26', '$44,189,231', '2'],
        ['Amazon.com',    '1,036,573', '08/31/26', '$50,000,000', '3'],
        ['Sage The Cat',  '1,416',     '09/30/26', '$60,500,000', '4'],
        ['Cummins, Inc.', '603,586',   '10/31/26', '$50,000,000', '5'],
      ],
    },
  },

  // ============================== Servicer flags ==============================
  {
    match: [/servicer|flag|forbearance|covid|watchlist|delinqu/i],
    text:
      'No loans are currently delinquent or in special servicing. Servicer commentary keywords flag **6 loans for Tenant Vacate/Vacate (7.96% of pool)** and **3 loans for Tenant BK ($58.8M, 6.12%)** — these are the watch-worthy clusters even though none are currently distressed.',
    payload: {
      kind: 'table',
      columns: ['Keyword', '# Loans', 'Balance', '% of Pool'],
      rows: [
        ['Tenant Vacate',   '6', '$76,458,014', '7.96%'],
        ['Vacate',          '6', '$76,458,014', '7.96%'],
        ['Cash Event',      '3', '$62,004,383', '6.46%'],
        ['Tenant BK',       '3', '$58,754,599', '6.12%'],
        ['Flag',            '4', '$59,324,254', '6.18%'],
      ],
    },
  },

  // ============================== Export ==============================
  {
    match: [/export|download|excel|csv/i],
    text: "Exporting **Lease Rollover · ≤12 month tenants** to Excel. I've filtered to 4 tenants on $204.7M total balance with full property metadata.",
    payload: {
      kind: 'download',
      filename: 'MSC2019-L3_lease_rollover_12mo.xlsx',
      size: '18.4 KB',
    },
  },

  // ============================== Why B-class loss elevated ==============================
  {
    match: [/why.*b|b-class|junior|loss.*elevat|why.*loss/i],
    text:
      'Class B (CUSIP 61691UBJ7) shows a KBRA-projected loss of **$53.6M with a 9.8% IRR**. The driver is its position in the capital stack — 16.5% credit support but only $53.6M outstanding makes it the absorber for losses above the senior 31.9% CE. Under softer scenarios (OCM_AUW_Base_P2), B holds par.',
  },
];

const FALLBACK: ChatMessage = {
  id: 'fallback',
  role: 'ai',
  text:
    "I can answer questions about MSC 2019-L3's tranches, scenarios, geography, property types, lease rollover, servicer flags, or export data. Try a question like *\"What's the WA DSCR?\"* or *\"Show me NY loans.\"*",
};

export function matchCanned(userText: string): ChatMessage {
  const hit = CANNED.find(c => c.match.some(re => re.test(userText)));
  if (!hit) return { ...FALLBACK, id: crypto.randomUUID() };
  return {
    id: crypto.randomUUID(),
    role: 'ai',
    text: hit.text,
    payload: hit.payload,
  };
}

export const SUGGESTED_PROMPTS = [
  "What's the WA DSCR?",
  'Show me NY loans',
  'Compare KBRA vs OCM Upside P3',
  'Property type concentration',
  'Lease rollover under 12 months',
  'Export lease rollover',
];
