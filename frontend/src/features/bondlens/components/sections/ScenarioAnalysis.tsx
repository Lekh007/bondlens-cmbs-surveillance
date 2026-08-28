import { useEffect, useMemo, useState } from 'react';
import { Square, CheckSquare, X } from 'lucide-react';
import { Card } from '@/features/bondlens/components/ui/Card';
import { scenarios, scenarioColors } from '@/features/bondlens/data/scenarios';
import type { Scenario } from '@/features/bondlens/types';
import { IrrMocChart } from './IrrMocChart';

interface Selected extends Scenario {
  color: string;
}

const INITIAL_SELECTION = ['KBRA_Concluded', 'OCM_AUW_Upside_P3', 'OCM_AUW_Upside_P2', 'MS'];

export function ScenarioAnalysis() {
  const [selectedNames, setSelectedNames] = useState<string[]>(INITIAL_SELECTION);
  const [metric, setMetric] = useState<'IRR' | 'MOC' | 'Loss'>('IRR');

  const selected: Selected[] = useMemo(
    () =>
      selectedNames
        .map((name, i) => {
          const scn = scenarios.find(s => s.name === name);
          if (!scn) return null;
          return { ...scn, color: scenarioColors[i % scenarioColors.length] };
        })
        .filter((x): x is Selected => x !== null),
    [selectedNames],
  );

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<string>).detail;
      if (detail === 'kbra-vs-base') {
        setSelectedNames(['KBRA_Concluded', 'OCM_AUW_Base_P2']);
      } else if (detail === 'agency-stack') {
        setSelectedNames(['KBRA_Concluded', 'AUW_Base_Excel', 'OCM_Model_Loss']);
      }
    };
    document.addEventListener('vichara:preset', handler);
    return () => document.removeEventListener('vichara:preset', handler);
  }, []);

  const toggle = (name: string) => {
    setSelectedNames(prev => {
      if (prev.includes(name)) return prev.filter(n => n !== name);
      if (prev.length >= 6) return prev;
      return [...prev, name];
    });
  };

  const groupAgency = scenarios.filter(s => s.family === 'rating-agency');
  const groupAuto = scenarios.filter(s => s.family === 'auto-uw');
  const groupDealer = scenarios.filter(s => s.family === 'dealer');

  const maxIrr = Math.max(...selected.flatMap(s => s.irr ?? []), 8.3);
  const maxLoss = Math.max(...selected.map(s => s.currPct), 0);

  return (
    <Card
      id="scenarios"
      title="Projected Cum. Loss Scenarios"
      subtitle="28 scenarios across rating agency, auto-underwriting, and dealer loss models · select to overlay on the IRR/MOC chart"
      actions={['filter', 'export']}
    >
      <div className="grid grid-cols-12">
        {/* Left: scenario list */}
        <div className="col-span-5 border-r border-border-l max-h-[600px] overflow-y-auto">
          <ScnGroup label={`Rating Agency · ${groupAgency.length}`} hint="Original · Current">
            {groupAgency.map(s => (
              <ScnRow key={s.name} scn={s} selected={selectedNames.includes(s.name)} onToggle={toggle} />
            ))}
          </ScnGroup>
          <ScnGroup label={`Auto-Underwriting · ${groupAuto.length}`}>
            {groupAuto.map(s => (
              <ScnRow key={s.name} scn={s} selected={selectedNames.includes(s.name)} onToggle={toggle} />
            ))}
          </ScnGroup>
          <ScnGroup label={`Dealer Loss Models · ${groupDealer.length}`}>
            {groupDealer.map(s => (
              <ScnRow key={s.name} scn={s} selected={selectedNames.includes(s.name)} onToggle={toggle} />
            ))}
          </ScnGroup>
        </div>

        {/* Right: chart */}
        <div className="col-span-7 p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-[13px] font-semibold text-text-hi">IRR &amp; MOC by Tranche</div>
              <div className="text-[11.5px] text-text-md">Active scenarios overlaid · hover bars for exact values</div>
            </div>
            <div className="seg-mini">
              {(['IRR', 'MOC', 'Loss'] as const).map(m => (
                <button key={m} className={metric === m ? 'active' : ''} onClick={() => setMetric(m)}>
                  {m}
                </button>
              ))}
            </div>
          </div>

          {/* Selected scenario chips */}
          <div className="flex flex-wrap gap-2 mb-4 min-h-[28px]">
            {selected.length === 0 ? (
              <div className="text-[12px] text-text-md italic">No scenarios selected</div>
            ) : (
              selected.map(s => (
                <div
                  key={s.name}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px]"
                  style={{ background: '#ffffff', border: `1px solid ${s.color}40` }}
                >
                  <span className="w-2 h-2 rounded-full" style={{ background: s.color }} />
                  <span>{s.name}</span>
                  <button
                    className="ml-0.5 w-4 h-4 inline-flex items-center justify-center rounded-full text-text-lo hover:text-loss hover:bg-loss-tint"
                    onClick={() => toggle(s.name)}
                  >
                    <X size={11} strokeWidth={2.4} />
                  </button>
                </div>
              ))
            )}
          </div>

          <IrrMocChart selected={selected} metric={metric} />

          <div className="grid grid-cols-3 gap-4 mt-4">
            <div className="text-center">
              <div className="kpi-label">Max IRR (C)</div>
              <div className="text-[18px] font-semibold num text-gain mt-1">{maxIrr.toFixed(1)}%</div>
            </div>
            <div className="text-center">
              <div className="kpi-label">Selected Scenarios</div>
              <div className="text-[18px] font-semibold num mt-1">{selected.length}</div>
            </div>
            <div className="text-center">
              <div className="kpi-label">Max Loss</div>
              <div className="text-[18px] font-semibold num text-loss mt-1">{maxLoss.toFixed(2)}%</div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

function ScnGroup({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <>
      <div className="scn-group-hdr">
        <span>{label}</span>
        {hint && <span className="text-text-lo normal-case font-normal">{hint}</span>}
      </div>
      {children}
    </>
  );
}

function ScnRow({ scn, selected, onToggle }: { scn: Scenario; selected: boolean; onToggle: (name: string) => void }) {
  return (
    <div className={`scn-row ${selected ? 'selected' : ''}`} onClick={() => onToggle(scn.name)}>
      {selected ? <CheckSquare size={15} strokeWidth={1.8} className="text-navy" /> : <Square size={15} strokeWidth={1.8} className="text-text-lo" />}
      <span>{scn.name}</span>
      <span className="pctn">{scn.origPct.toFixed(2)}%</span>
      <span className={`pctn ${selected ? 'font-medium' : ''}`}>{scn.currPct.toFixed(2)}%</span>
    </div>
  );
}
