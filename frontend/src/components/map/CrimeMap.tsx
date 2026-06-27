import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useAppStore } from '@/store'
import { RISK_META, type RiskLevel } from '@/utils/constants'

// Fix default Leaflet icon paths
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl:       'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl:     'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

export default function CrimeMap() {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstance = useRef<L.Map | null>(null)
  const markersRef = useRef<L.LayerGroup | null>(null)
  const heatLayer = useRef<L.LayerGroup | null>(null)

  const { areas, predictions, heatmapData, setSelectedAreaId, setActivePrediction } = useAppStore()

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstance.current) return

    const map = L.map(mapRef.current, {
      center: [41.8827, -87.6298],  // Chicago default (city-agnostic: changes with area data)
      zoom: 12,
      zoomControl: true,
    })

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap',
      maxZoom: 18,
    }).addTo(map)

    markersRef.current = L.layerGroup().addTo(map)
    heatLayer.current = L.layerGroup().addTo(map)
    mapInstance.current = map

    return () => { map.remove(); mapInstance.current = null }
  }, [])

  // Update area markers when predictions change
  useEffect(() => {
    if (!mapInstance.current || !markersRef.current) return
    markersRef.current.clearLayers()

    areas.forEach(area => {
      if (!area.centroid_lat || !area.centroid_lon) return
      const pred = predictions[area.id]
      const riskLevel = (pred?.risk_level ?? 'LOW') as RiskLevel
      const meta = RISK_META[riskLevel]

      const icon = L.divIcon({
        className: '',
        html: `<div style="
          width: 40px; height: 40px;
          background: ${meta.color}22;
          border: 2px solid ${meta.color};
          border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          font-size: 11px; font-weight: 800; color: ${meta.color};
          backdrop-filter: blur(4px);
          box-shadow: 0 0 12px ${meta.color}44;
          cursor: pointer;
          transition: transform 0.2s;
        " onmouseover="this.style.transform='scale(1.2)'" onmouseout="this.style.transform='scale(1)'">
          ${pred ? Math.round(pred.risk_score) : '?'}
        </div>`,
        iconSize: [40, 40],
        iconAnchor: [20, 20],
      })

      const marker = L.marker([area.centroid_lat, area.centroid_lon], { icon })
      marker.bindTooltip(`
        <div style="background:#111827;border:1px solid #1f2937;border-radius:8px;padding:10px 14px;color:#f1f5f9;min-width:160px;">
          <div style="font-weight:700;margin-bottom:4px;">${area.name}</div>
          ${pred ? `
            <div style="color:${meta.color};font-weight:600;font-size:12px;">${meta.label} Risk · ${pred.risk_score.toFixed(1)}/100</div>
            <div style="color:#94a3b8;font-size:11px;margin-top:2px;">${pred.crime_type?.replace(/_/g, ' ') ?? ''}</div>
          ` : '<div style="color:#475569;font-size:11px;">No prediction</div>'}
        </div>
      `, { permanent: false, direction: 'top', className: 'custom-tooltip' })

      marker.on('click', () => {
        setSelectedAreaId(area.id)
        if (pred) setActivePrediction(pred)
      })

      markersRef.current!.addLayer(marker)
    })
  }, [areas, predictions])

  // Render heatmap circles
  useEffect(() => {
    if (!mapInstance.current || !heatLayer.current || !heatmapData) return
    heatLayer.current.clearLayers()

    heatmapData.features.forEach((f) => {
      const [lon, lat] = (f.geometry as GeoJSON.Point).coordinates
      const { risk_score, risk_level } = f.properties as any
      const meta = RISK_META[risk_level as RiskLevel]
      L.circle([lat, lon], {
        radius: 600,
        fillColor: meta.color,
        fillOpacity: (risk_score / 100) * 0.35,
        color: meta.color,
        weight: 1,
        opacity: 0.4,
      }).addTo(heatLayer.current!)
    })
  }, [heatmapData])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={mapRef} style={{ width: '100%', height: '100%', borderRadius: 12 }} />
      {/* Legend */}
      <div style={{
        position: 'absolute', bottom: 16, right: 16, zIndex: 1000,
        background: 'var(--color-bg-glass)', backdropFilter: 'blur(12px)',
        border: '1px solid var(--color-border)', borderRadius: 10,
        padding: '10px 14px',
      }}>
        {Object.entries(RISK_META).map(([level, meta]) => (
          <div key={level} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: meta.color }} />
            <span style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)' }}>{meta.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
