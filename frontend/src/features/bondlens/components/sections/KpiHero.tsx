import { TrendingUp, TrendingDown, Briefcase, Minus } from 'lucide-react';
import { Pill } from '@/features/bondlens/components/ui/Pill';
import { dealOverview, portfolioMetrics } from '@/features/bondlens/data/deal';
import { fmtMoney, fmtPct, fmtDscr, fmtNum } from '@/features/bondlens/lib/format';

interface Kpi {
  label: string;
  value: string;
  delta?: { direction: 'up' | 'down' | 'flat'; text: string; variant: 'gain' | 'loss' | 'warn' | 'neutral' };
  footRight?: string;
}

export function KpiHero() {
  const kpis: Kpi[] = [
    {
      label: 'Deal Type',
      value: dealOverview.type,
      delta: { direction: 'flat', text: 'Vintage 2019', variant: 'neutral' },
    },
    {
      label: 'Total Balance',
      value: fmtMoney(portfolioMetrics.totalBalanceCurr),
      delta: { direction: 'down', text: '6.0% vs orig', variant: 'loss' },
      footRight: `${fmtMoney(portfolioMetrics.totalBalanceOrig)} orig`,
    },
    {
      label: '# of Loans',
      value: fmtNum(portfolioMetrics.numLoansCurr),
      delta: { direction: 'flat', text: 'unchanged', variant: 'neutral' },
      footRight: `avg ${fmtMoney(portfolioMetrics.avgBalanceCurr)}`,
    },
    {
      label: 'WAC',
      value: fmtPct(portfolioMetrics.wacCurr, 2),
      delta: { direction: 'up', text: '+9 bp', variant: 'gain' },
      footRight: `${fmtPct(portfolioMetrics.wacOrig, 2)} orig`,
    },
    {
      label: 'WA LTV',
      value: fmtPct(portfolioMetrics.waLtvCurr, 2),
      delta: { direction: 'up', text: '+64 bp', variant: 'warn' },
      footRight: `${fmtPct(portfolioMetrics.waLtvOrig, 2)} orig`,
    },
    {
      label: 'WA DSCR',
      value: fmtDscr(portfolioMetrics.waDscrCurr),
      delta: { direction: 'up', text: '+0.45x', variant: 'gain' },
      footRight: `${fmtDscr(portfolioMetrics.waDscrOrig)} orig`,
    },
    {
      label: 'Curr Cum Loss',
      value: fmtPct(portfolioMetrics.currCumLossCurr, 2),
      delta: { direction: 'flat', text: 'no realized loss', variant: 'neutral' },
      footRight: `proj ${fmtPct(portfolioMetrics.projCumLossCurr, 1)}`,
    },
  ];

  return (
    <section id="overview" className="grid grid-cols-7 gap-3">
      {kpis.map((k, i) => (
        <div key={i} className="kpi">
          <div className="kpi-label">{k.label}</div>
          <div className="kpi-value num">{k.value}</div>
          <div className="kpi-foot">
            {k.delta && (
              <Pill variant={k.delta.variant}>
                {k.delta.direction === 'up'   && <TrendingUp size={11} strokeWidth={2} />}
                {k.delta.direction === 'down' && <TrendingDown size={11} strokeWidth={2} />}
                {k.delta.direction === 'flat' && <Minus size={11} strokeWidth={2} />}
                {k.delta.text}
              </Pill>
            )}
            {k.footRight && <span className="text-[10.5px] text-text-lo num">{k.footRight}</span>}
            {!k.footRight && k.label === 'Deal Type' && <Briefcase size={13} strokeWidth={1.6} className="text-text-lo" />}
          </div>
        </div>
      ))}
    </section>
  );
}
