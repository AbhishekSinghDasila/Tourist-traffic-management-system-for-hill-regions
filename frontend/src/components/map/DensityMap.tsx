import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet'
import '../../lib/leafletIcons'
import type { DistrictDensity } from '../../types'

// Approximate lat/lng for each hill district/town the backend knows about.
// The traffic-service density payload only carries a district name and
// counts — no coordinates — so this fixed lookup is what places the
// circles on the map. Kept local to this component since nothing else
// needs district coordinates.
const DISTRICT_COORDS: Record<string, [number, number]> = {
  nainital: [29.3803, 79.4636],
  mussoorie: [30.4598, 78.0664],
  haridwar: [29.9457, 78.1642],
  rishikesh: [30.0869, 78.2676],
  ranikhet: [29.6417, 79.4333],
  almora: [29.5892, 79.6467],
  kedarnath: [30.7346, 79.0669],
  badrinath: [30.7433, 79.4938],
  shimla: [31.1048, 77.1734],
  manali: [32.2432, 77.1892],
  dharamsala: [32.219, 76.3234],
}

const DEFAULT_CENTER: [number, number] = [30.3, 78.6]

function riskColor(risk: string): string {
  if (risk === 'RED') return '#dc2626'
  if (risk === 'AMBER') return '#d97706'
  if (risk === 'GREEN') return '#16a34a'
  return '#64748b'
}

export function DensityMap({
  districts,
  height = 420,
}: {
  districts: DistrictDensity[]
  height?: number
}) {
  const placed = districts.filter((d) => DISTRICT_COORDS[d.district.toLowerCase()])

  return (
    <div style={{ height }} className="overflow-hidden rounded-xl border border-slate-200">
      <MapContainer center={DEFAULT_CENTER} zoom={7} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {placed.map((d) => {
          const coords = DISTRICT_COORDS[d.district.toLowerCase()]
          const radius = 10 + Math.min(20, d.percentage / 5)
          return (
            <CircleMarker
              key={d.district}
              center={coords}
              radius={radius}
              pathOptions={{
                color: riskColor(d.risk_level),
                fillColor: riskColor(d.risk_level),
                fillOpacity: 0.5,
              }}
            >
              <Popup>
                <div className="text-sm">
                  <p className="font-semibold capitalize">{d.district}</p>
                  <p>
                    {d.active_vehicles} / {d.capacity} vehicles ({d.percentage.toFixed(1)}%)
                  </p>
                  <p>
                    Risk: <span className="font-medium">{d.risk_level}</span>
                  </p>
                </div>
              </Popup>
            </CircleMarker>
          )
        })}
      </MapContainer>
    </div>
  )
}
