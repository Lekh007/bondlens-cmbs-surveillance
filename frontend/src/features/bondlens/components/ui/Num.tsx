import { fmtNum } from '@/features/bondlens/lib/format';

interface Props {
  value: number | null | undefined;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  muted?: boolean;
  className?: string;
}

export function Num({ value, decimals = 0, prefix, suffix, muted, className }: Props) {
  if (value === null || value === undefined) {
    return <span className={`num muted ${className ?? ''}`}>—</span>;
  }
  return (
    <span className={`num ${muted ? 'muted' : ''} ${className ?? ''}`}>
      {prefix ?? ''}
      {fmtNum(value, { decimals })}
      {suffix ?? ''}
    </span>
  );
}
