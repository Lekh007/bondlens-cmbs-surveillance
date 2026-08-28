import type { Scenario } from '@/features/bondlens/types';

interface Selected extends Scenario {
  color: string;
}

interface Props {
  selected: Selected[];
  metric: 'IRR' | 'MOC' | 'Loss';
}

const TRANCHES = ['AS', 'B', 'C'] as const;

export function IrrMocChart({ selected, metric }: Props) {
  const W = 700;
  const H = 280;
  const padL = 44;
  const padR = 16;
  const padT = 16;
  const padB = 36;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  if (selected.length === 0) {
    return (
      <div className="bg-bg rounded-lg border border-border-l p-4 flex items-center justify-center" style={{ minHeight: 280 }}>
        <div className="text-center max-w-md">
          <div className="text-text-md text-[14px] mb-1">Select scenarios from the table to populate</div>
          <div className="text-text-lo text-[12px] mb-4">Or use one of these preset combinations:</div>
          <div className="flex gap-2 justify-center">
            <button
              className="btn btn-ghost"
              onClick={() => {
                document.dispatchEvent(new CustomEvent('vichara:preset', { detail: 'kbra-vs-base' }));
              }}
            >
              Quick Compare: KBRA vs Base
            </button>
            <button
              className="btn btn-ghost"
              onClick={() => {
                document.dispatchEvent(new CustomEvent('vichara:preset', { detail: 'agency-stack' }));
              }}
            >
              Agency Stack
            </button>
          </div>
        </div>
      </div>
    );
  }

  const getValue = (scn: Selected, tranche: typeof TRANCHES[number]) => {
    const idx = TRANCHES.indexOf(tranche);
    if (metric === 'IRR') return scn.irr?.[idx] ?? 0;
    if (metric === 'MOC') return (1 + (scn.irr?.[idx] ?? 0) / 100) * 1.2;
    if (metric === 'Loss') return scn.currPct;
    return 0;
  };

  const allValues = selected.flatMap(s => TRANCHES.map(t => getValue(s, t)));
  const maxVal = Math.max(...allValues, metric === 'MOC' ? 2 : 15);
  const yTicks = 5;

  const groupW = innerW / TRANCHES.length;
  const barW = Math.min(28, (groupW - 20) / selected.length);
  const groupContentW = barW * selected.length + (selected.length - 1) * 4;

  const valueSuffix = metric === 'IRR' ? '%' : metric === 'MOC' ? 'x' : '%';

  return (
    <div className="bg-bg rounded-lg border border-border-l p-4">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 280 }} preserveAspectRatio="xMidYMid meet">
        {/* Y-axis gridlines + labels */}
        {Array.from({ length: yTicks + 1 }).map((_, i) => {
          const v = (maxVal / yTicks) * i;
          const y = padT + innerH - (v / maxVal) * innerH;
          return (
            <g key={i}>
              <line
                x1={padL}
                x2={W - padR}
                y1={y}
                y2={y}
                stroke="#E2E8F0"
                strokeWidth={1}
                strokeDasharray={i === 0 ? '0' : '2,2'}
              />
              <text x={padL - 8} y={y + 4} textAnchor="end" fill="#94A3B8" fontSize={10} fontFamily="JetBrains Mono, monospace">
                {v.toFixed(metric === 'MOC' ? 2 : 0)}
                {valueSuffix}
              </text>
            </g>
          );
        })}

        {/* Baseline */}
        <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="#CBD5E1" strokeWidth={1} />

        {/* Bars */}
        {TRANCHES.map((tranche, gi) => {
          const groupX = padL + groupW * gi + (groupW - groupContentW) / 2;
          return (
            <g key={tranche}>
              {selected.map((scn, si) => {
                const val = getValue(scn, tranche);
                const h = (val / maxVal) * innerH;
                const x = groupX + si * (barW + 4);
                const y = padT + innerH - h;
                return (
                  <g key={scn.name}>
                    <rect x={x} y={y} width={barW} height={h} rx={2} fill={scn.color} opacity={0.92}>
                      <title>{`${scn.name} · ${tranche}: ${val.toFixed(metric === 'MOC' ? 2 : 1)}${valueSuffix}`}</title>
                    </rect>
                    {h > 22 && (
                      <text
                        x={x + barW / 2}
                        y={y + 12}
                        textAnchor="middle"
                        fill="#ffffff"
                        fontSize={9}
                        fontWeight={600}
                        fontFamily="JetBrains Mono, monospace"
                      >
                        {val.toFixed(metric === 'MOC' ? 2 : 1)}
                      </text>
                    )}
                  </g>
                );
              })}
              {/* X-axis label */}
              <text
                x={padL + groupW * gi + groupW / 2}
                y={padT + innerH + 22}
                textAnchor="middle"
                fill="#475569"
                fontSize={12}
                fontWeight={600}
                fontFamily="Inter, sans-serif"
              >
                {tranche}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
