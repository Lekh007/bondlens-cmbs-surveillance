import type { Scenario } from '@/features/bondlens/types';

export const scenarios: Scenario[] = [
  // Rating Agency (1)
  { name: 'KBRA_Concluded',    family: 'rating-agency', origPct: 74.91, currPct: 79.67, irr: [8.3, 9.8, 11.8] },

  // Auto-Underwriting (22)
  { name: 'Temp_VI',             family: 'auto-uw', origPct:  0.00, currPct:  0.00, irr: [0,    0,    0]    },
  { name: 'AUW_Downside_Excel',  family: 'auto-uw', origPct:  6.14, currPct:  6.53, irr: [7.2,  8.4,  9.6]  },
  { name: 'AUW_Base_Excel',      family: 'auto-uw', origPct:  4.85, currPct:  5.16, irr: [7.6,  8.9,  10.3] },
  { name: 'AUW_Upside_Excel',    family: 'auto-uw', origPct:  3.96, currPct:  4.21, irr: [7.9,  9.2,  10.7] },
  { name: 'OCM_AUW_Downside_P3', family: 'auto-uw', origPct: 13.01, currPct: 13.83, irr: [6.4,  7.5,  8.6]  },
  { name: 'OCM_AUW_Base_P3',     family: 'auto-uw', origPct: 10.35, currPct: 11.01, irr: [7.1,  8.2,  9.4]  },
  { name: 'OCM_AUW_Upside_P3',   family: 'auto-uw', origPct:  9.61, currPct: 10.22, irr: [8.3,  9.8,  9.7]  },
  { name: 'OCM_AUW_Downside_P2', family: 'auto-uw', origPct: 12.65, currPct: 13.46, irr: [6.5,  7.6,  8.7]  },
  { name: 'OCM_AUW_Base_P2',     family: 'auto-uw', origPct:  9.64, currPct: 10.25, irr: [7.4,  8.6,  9.9]  },
  { name: 'OCM_AUW_Upside_P2',   family: 'auto-uw', origPct:  8.82, currPct:  9.38, irr: [8.3,  9.8,  9.7]  },
  { name: 'OCM_AUW_Downside_P1', family: 'auto-uw', origPct: 12.23, currPct: 13.01, irr: [6.6,  7.7,  8.8]  },
  { name: 'OCM_AUW_Base_P1',     family: 'auto-uw', origPct:  8.78, currPct:  9.33, irr: [7.6,  8.8,  10.1] },
  { name: 'OCM_AUW_Upside_P1',   family: 'auto-uw', origPct:  7.88, currPct:  8.37, irr: [8.0,  9.3,  10.6] },
  { name: 'OCM_AUW_Downside_M1', family: 'auto-uw', origPct: 10.92, currPct: 11.61, irr: [7.0,  8.1,  9.3]  },
  { name: 'OCM_AUW_Base_M1',     family: 'auto-uw', origPct:  6.52, currPct:  6.93, irr: [7.8,  9.0,  10.4] },
  { name: 'OCM_AUW_Upside_M1',   family: 'auto-uw', origPct:  5.43, currPct:  5.77, irr: [8.1,  9.5,  10.9] },
  { name: 'OCM_AUW_Downside_M2', family: 'auto-uw', origPct:  9.93, currPct: 10.56, irr: [7.2,  8.3,  9.5]  },
  { name: 'OCM_AUW_Base_M2',     family: 'auto-uw', origPct:  4.93, currPct:  5.24, irr: [7.9,  9.2,  10.6] },
  { name: 'OCM_AUW_Upside_M2',   family: 'auto-uw', origPct:  3.95, currPct:  4.20, irr: [8.2,  9.6,  11.1] },
  { name: 'OCM_AUW_Downside_M3', family: 'auto-uw', origPct: 13.30, currPct: 14.15, irr: [6.3,  7.4,  8.5]  },
  { name: 'OCM_AUW_Base_M3',     family: 'auto-uw', origPct:  6.21, currPct:  6.61, irr: [7.7,  8.9,  10.2] },
  { name: 'OCM_AUW_Upside_M3',   family: 'auto-uw', origPct:  4.22, currPct:  4.49, irr: [8.1,  9.4,  10.8] },

  // Dealer Loss Models (5)
  { name: 'OCM_Model_Loss', family: 'dealer', origPct: 1.77, currPct: 1.88, irr: [8.4, 9.9, 11.5] },
  { name: 'BAML_Loss',      family: 'dealer', origPct: 1.01, currPct: 1.07, irr: [8.5, 10.0, 11.7] },
  { name: 'JPM Loss',       family: 'dealer', origPct: 1.32, currPct: 1.40, irr: [8.5, 10.0, 11.6] },
  { name: 'MSJenga',        family: 'dealer', origPct: 4.44, currPct: 4.72, irr: [8.0, 9.3, 10.6]  },
  { name: 'MS',             family: 'dealer', origPct: 4.44, currPct: 4.72, irr: [8.0, 9.3, 10.6]  },
];

export const scenarioColors: string[] = [
  '#1E3A8A', // navy
  '#15803D', // green
  '#A16207', // amber
  '#B91C1C', // red
  '#7C3AED', // purple
  '#DB2777', // pink
];
