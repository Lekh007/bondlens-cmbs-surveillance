import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Card } from '@/features/bondlens/components/ui/Card';
import { Pill } from '@/features/bondlens/components/ui/Pill';
import { leaseGroups } from '@/features/bondlens/data/deal';
import { fmtNum, fmtPct } from '@/features/bondlens/lib/format';
import type { LeaseGroup, LeaseRow } from '@/features/bondlens/types';

const TOTAL_COLS = 12;

export function LeaseRollover() {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const totals = leaseGroups.reduce(
    (acc, g) => ({
      tenants: acc.tenants + g.totalTenants,
      sf:      acc.sf + g.totalSf,
      balance: acc.balance + g.totalBalance,
    }),
    { tenants: 0, sf: 0, balance: 0 },
  );

  return (
    <Card
      id="lease"
      title="Lease Rollover"
      subtitle={`${totals.tenants} tenants across 3 maturity buckets · grouped by expiration window`}
      actions={['columns', 'filter', 'export']}
    >
      <div className="overflow-x-auto">
        <table className="vt">
          <thead>
            <tr>
              <th>Tenant</th>
              <th className="num">Tenant SF</th>
              <th className="num">Tenant %</th>
              <th className="num">Exp Date</th>
              <th>Loan</th>
              <th>Property</th>
              <th>Type</th>
              <th>City</th>
              <th className="num">Balance</th>
              <th className="num">PSF</th>
              <th className="num">Maturity</th>
              <th className="num">Months</th>
            </tr>
          </thead>
          <tbody>
            {leaseGroups.map(g => (
              <LeaseGroupBlock
                key={g.rangeMonths}
                group={g}
                collapsed={collapsed[g.rangeMonths]}
                onToggle={() => setCollapsed(c => ({ ...c, [g.rangeMonths]: !c[g.rangeMonths] }))}
              />
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td>Total · {totals.tenants} tenants</td>
              <td className="num">{fmtNum(totals.sf)}</td>
              <td colSpan={6}></td>
              <td className="num">{fmtNum(totals.balance)}</td>
              <td colSpan={3}></td>
            </tr>
          </tfoot>
        </table>
      </div>
    </Card>
  );
}

function LeaseGroupBlock({ group, collapsed, onToggle }: { group: LeaseGroup; collapsed?: boolean; onToggle: () => void }) {
  return (
    <>
      <tr className="group-row" onClick={onToggle}>
        <td colSpan={TOTAL_COLS}>
          <span className="inline-flex items-center gap-1.5">
            {collapsed ? <ChevronRight size={14} strokeWidth={2} /> : <ChevronDown size={14} strokeWidth={2} />}
            {group.label}
            <span className="ml-2">
              <Pill variant={group.severity} className="!bg-white/15 !text-white text-[10px] py-0">
                {group.totalTenants} tenants · {fmtNum(group.totalSf)} SF · ${(group.totalBalance / 1_000_000).toFixed(1)}M
              </Pill>
            </span>
          </span>
        </td>
      </tr>
      {!collapsed && group.rows.map((r, i) => <LeaseTenantRow key={`${r.tenant}-${i}`} row={r} severity={group.severity} />)}
    </>
  );
}

function LeaseTenantRow({ row, severity }: { row: LeaseRow; severity: 'loss' | 'warn' | 'gain' }) {
  const monthsClass = severity === 'loss' ? 'num text-loss font-medium' : 'num';

  const typeVariant =
    row.propertyType === 'Industrial' ? 'info' :
    row.propertyType === 'Office'     ? 'brand' :
    row.propertyType === 'Retail'     ? 'warn'  :
    'neutral';

  return (
    <tr>
      <td>{row.tenant}</td>
      <td className="num">{fmtNum(row.sf)}</td>
      <td className="pct-cell num" style={{ ['--pct' as never]: `${row.tenantPct}%` } as never}>
        <span>{fmtPct(row.tenantPct, 2)}</span>
      </td>
      <td className="num">{row.expDate}</td>
      <td className="link">{row.loanName}</td>
      <td>{row.property}</td>
      <td><Pill variant={typeVariant}>{row.propertyType}</Pill></td>
      <td>{row.city}</td>
      <td className="num">{fmtNum(row.balance)}</td>
      <td className="num">{row.psf.toFixed(2)}</td>
      <td className="num">{row.loanMaturity}</td>
      <td className={monthsClass}>{row.months}</td>
    </tr>
  );
}
