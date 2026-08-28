import type { ReactNode } from 'react';
import { cn } from '@/features/bondlens/lib/cn';

type Variant = 'gain' | 'loss' | 'warn' | 'info' | 'neutral' | 'brand';

interface Props {
  variant?: Variant;
  className?: string;
  children: ReactNode;
}

export function Pill({ variant = 'neutral', className, children }: Props) {
  return <span className={cn('pill', `pill-${variant}`, className)}>{children}</span>;
}
