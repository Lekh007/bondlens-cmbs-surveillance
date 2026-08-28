import { Card } from '@/features/bondlens/components/ui/Card'
import type { GeographyDistribution } from '@/features/bondlens/api'
import { fmtNum, fmtPct } from '@/features/bondlens/lib/format'

interface Props {
  distribution: GeographyDistribution
}

// property_count / % of properties, not $ balance - ABS-EE doesn't allocate
// a loan's balance across its properties, so a per-state balance would be
// invented. See analytics.py get_geography_distribution.
export function Geography({ distribution }: Props) {
  const missingNote =
    distribution.properties_missing_state > 0
      ? `${distribution.properties_missing_state} propert(y/ies) missing a state · `
      : ''

  return (
    <Card
      id="geography"
      title="Geographic Distribution"
      subtitle={`${missingNote}${distribution.entries.length} states · by property count`}
      actions={['export']}
    >
      <table className="vt">
        <thead>
          <tr>
            <th>State</th>
            <th className="num">Properties</th>
            <th className="num">% of Properties</th>
          </tr>
        </thead>
        <tbody>
          {distribution.entries.map((e) => {
            const pct =
              distribution.total_properties > 0
                ? (e.property_count / distribution.total_properties) * 100
                : 0
            return (
              <tr key={e.state}>
                <td>{e.state}</td>
                <td className="num">{fmtNum(e.property_count)}</td>
                <td className="pct-cell num" style={{ ['--pct' as never]: `${pct}%` } as never}>
                  <span>{fmtPct(pct, 2)}</span>
                </td>
              </tr>
            )
          })}
        </tbody>
        <tfoot>
          <tr>
            <td>Total</td>
            <td className="num">{fmtNum(distribution.total_properties)}</td>
            <td className="num">100.00%</td>
          </tr>
        </tfoot>
      </table>
    </Card>
  )
}
