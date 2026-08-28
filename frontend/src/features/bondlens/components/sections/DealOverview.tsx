import { Card } from '@/features/bondlens/components/ui/Card';
import { dealOverview, portfolioMetrics } from '@/features/bondlens/data/deal';
import { fmtNum, fmtPct, fmtDscr } from '@/features/bondlens/lib/format';

export function DealOverview() {
  return (
    <Card
      id="deal-overview"
      title="Deal Overview"
      subtitle="Deal metadata and portfolio-level metrics"
      actions={['export', 'expand']}
    >
      <div className="grid grid-cols-2 divide-x divide-border-l">
        {/* Left: metadata */}
        <div className="overflow-x-auto">
          <table className="vt">
            <thead>
              <tr>
                <th colSpan={2}>Deal Metadata</th>
              </tr>
            </thead>
            <tbody>
              <Row label="BBG Deal Name"           value={dealOverview.bbgName}           mono />
              <Row label="Last Update From Intex"  value={dealOverview.lastUpdate}        mono />
              <Row label="Type"                    value={dealOverview.type} />
              <Row label="First Settle Date"       value={dealOverview.firstSettle}       mono />
              <Row label="Trustee"                 value={dealOverview.trustee} />
              <Row label="MS (Master Servicer)"    value={dealOverview.masterServicer} />
              <Row label="SS (Special Servicer)"   value={dealOverview.specialServicer}   small />
              <Row label="B-Piece Buyer"           value={dealOverview.bPieceBuyer} />
              <Row label="Risk Retention Type"     value={dealOverview.riskRetention} />
              <Row label="Curr Cum Loss %"         value={fmtPct(dealOverview.currCumLoss, 2)} mono />
              <Row label="LOC %"                   value={fmtPct(dealOverview.locPct, 2)} mono />
              <Row label="Proj Cum Loss %"         value={fmtPct(dealOverview.projCumLoss, 2)} mono />
            </tbody>
          </table>
        </div>

        {/* Right: portfolio metrics */}
        <div className="overflow-x-auto">
          <table className="vt">
            <thead>
              <tr>
                <th>Portfolio Metrics</th>
                <th className="num">Original</th>
                <th className="num">Current</th>
              </tr>
            </thead>
            <tbody>
              <MetricRow label="# of Loans"          orig={fmtNum(portfolioMetrics.numLoansOrig)} curr={fmtNum(portfolioMetrics.numLoansCurr)} />
              <MetricRow label="Total Balance"       orig={`$${fmtNum(portfolioMetrics.totalBalanceOrig)}`} curr={`$${fmtNum(portfolioMetrics.totalBalanceCurr)}`} bold />
              <MetricRow label="Average Balance"     orig={`$${fmtNum(portfolioMetrics.avgBalanceOrig)}`} curr={`$${fmtNum(portfolioMetrics.avgBalanceCurr)}`} />
              <MetricRow label="WAC"                 orig={fmtPct(portfolioMetrics.wacOrig, 2)} curr={fmtPct(portfolioMetrics.wacCurr, 2)} bold />
              <MetricRow label="WA LTV"              orig={fmtPct(portfolioMetrics.waLtvOrig, 2)} curr={fmtPct(portfolioMetrics.waLtvCurr, 2)} bold />
              <MetricRow label="WA DSCR"             orig={fmtDscr(portfolioMetrics.waDscrOrig)} curr={fmtDscr(portfolioMetrics.waDscrCurr)} bold />
              <MetricRow label="Historical Losses"   orig="—" curr="—" muted />
              <MetricRow label="Curr Cum Loss %"     orig={fmtPct(portfolioMetrics.currCumLossOrig, 2)} curr={fmtPct(portfolioMetrics.currCumLossCurr, 2)} />
              <MetricRow label="Projected Cum Loss %" orig="—" curr={fmtPct(portfolioMetrics.projCumLossCurr, 2)} bold />
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}

function Row({ label, value, mono = false, small = false }: { label: string; value: string; mono?: boolean; small?: boolean }) {
  return (
    <tr>
      <td className="text-text-md w-1/2">{label}</td>
      <td className={`font-medium ${mono ? 'num' : ''} ${small ? 'text-[12px]' : ''}`}>{value}</td>
    </tr>
  );
}

function MetricRow({ label, orig, curr, bold = false, muted = false }: { label: string; orig: string; curr: string; bold?: boolean; muted?: boolean }) {
  return (
    <tr>
      <td className="text-text-md">{label}</td>
      <td className={`num ${muted ? 'muted' : ''}`}>{orig}</td>
      <td className={`num ${bold ? 'font-medium' : ''} ${muted ? 'muted' : ''}`}>{curr}</td>
    </tr>
  );
}
