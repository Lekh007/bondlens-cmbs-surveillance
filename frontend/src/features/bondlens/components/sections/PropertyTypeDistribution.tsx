import { Card } from '@/features/bondlens/components/ui/Card'
import type { PropertyTypeDistribution as PropertyTypeDistributionData } from '@/features/bondlens/api'
import { fmtNum, fmtPct } from '@/features/bondlens/lib/format'

interface Props {
  distribution: PropertyTypeDistributionData
}

// Raw SEC ABS-EE propertyTypeCode values (e.g. "SS", "MF"), not expanded
// to full names - the code-to-label mapping isn't verified against this
// deal's actual data, so showing the raw code beats guessing a label.
export function PropertyTypeDistribution({ distribution }: Props) {
  const missingNote =
    distribution.properties_missing_type > 0
      ? `${distribution.properties_missing_type} propert(y/ies) missing a type code · `
      : ''

  return (
    <Card
      id="property"
      title="Property Type Distribution"
      subtitle={`${missingNote}${distribution.entries.length} property type codes (raw ABS-EE codes)`}
      actions={['export']}
    >
      <table className="vt">
        <thead>
          <tr>
            <th>Type Code</th>
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
              <tr key={e.property_type_code}>
                <td className="num">{e.property_type_code}</td>
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
