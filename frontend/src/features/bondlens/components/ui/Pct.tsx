import { fmtPct } from '@/features/bondlens/lib/format';

interface Props {
  value: number | null | undefined;
  decimals?: number;
  muted?: boolean;
  showBar?: boolean;
}

export function Pct({ value, decimals = 2, muted = false, showBar = true }: Props) {
  if (value === null || value === undefined) {
    return <span className="muted num">·</span>;
  }
  const formatted = fmtPct(value, decimals);
  return (
    <span
      className="pct-cell num inline-block w-full"
      style={showBar ? ({ ['--pct' as never]: `${Math.min(value, 100)}%` } as never) : undefined}
    >
      <span className={muted || value === 0 ? 'muted' : ''}>{formatted}</span>
    </span>
  );
}

/**
 * Variant for table-cell usage: returns the styled wrapper as a TD-friendly content.
 */
export function PctCell({ value, decimals = 2, muted = false }: Props) {
  if (value === null || value === undefined) {
    return (
      <td className="num">
        <span className="muted">·</span>
      </td>
    );
  }
  return (
    <td
      className="pct-cell num"
      style={{ ['--pct' as never]: `${Math.min(value, 100)}%` } as never}
    >
      <span className={muted || value === 0 ? 'muted' : ''}>{fmtPct(value, decimals)}</span>
    </td>
  );
}
