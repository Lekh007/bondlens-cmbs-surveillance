export const fmtNum = (n: number | null | undefined, opts: { commas?: boolean; decimals?: number } = {}): string => {
  if (n === null || n === undefined) return '—';
  const { commas = true, decimals = 0 } = opts;
  const fixed = n.toFixed(decimals);
  if (!commas) return fixed;
  const [int, dec] = fixed.split('.');
  const withCommas = int.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return dec ? `${withCommas}.${dec}` : withCommas;
};

export const fmtPct = (n: number | null | undefined, decimals: number = 2): string => {
  if (n === null || n === undefined) return '—';
  return `${n.toFixed(decimals)}%`;
};

export const fmtBalance = (n: number | null | undefined): string => {
  if (n === null || n === undefined) return '—';
  return fmtNum(n);
};

export const fmtMoney = (n: number | null | undefined): string => {
  if (n === null || n === undefined) return '—';
  if (Math.abs(n) >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`;
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
};

export const fmtMoneyFull = (n: number | null | undefined): string => {
  if (n === null || n === undefined) return '—';
  return `$${fmtNum(n)}`;
};

export const fmtDscr = (n: number | null | undefined): string => {
  if (n === null || n === undefined) return '—';
  return `${n.toFixed(2)}x`;
};
