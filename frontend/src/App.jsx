// frontend/src/App.jsx — 30-60-90 Premium Black UI (Part 1 of 4)
// Setup, API client, styles, and Dashboard/Vehicle List

import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Cell
} from 'recharts'

// ---------------------------------------------------------------------------
// API CLIENT
// ---------------------------------------------------------------------------
const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  headers: { 'X-Dealership-ID': '1' },
})

// ---------------------------------------------------------------------------
// STYLES (inline object — premium black/charcoal theme)
// ---------------------------------------------------------------------------
const S = {
  // Layout
  app: {
    minHeight: '100vh',
    background: '#0a0a0a',
    color: '#e0e0e0',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 32px',
    borderBottom: '1px solid #1e1e1e',
    background: '#0f0f0f',
  },
  logo: {
    fontSize: '22px',
    fontWeight: '800',
    letterSpacing: '-0.5px',
    color: '#ffffff',
  },
  logoAccent: {
    color: '#22d3ee',
  },
  nav: {
    display: 'flex',
    gap: '4px',
  },
  navBtn: (active) => ({
    padding: '8px 18px',
    borderRadius: '6px',
    border: 'none',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: active ? '600' : '400',
    color: active ? '#0a0a0a' : '#a0a0a0',
    background: active ? '#22d3ee' : 'transparent',
    transition: 'all 0.2s',
  }),
  main: {
    padding: '24px 32px',
    maxWidth: '1440px',
    margin: '0 auto',
  },

  // Cards
  card: {
    background: '#141414',
    border: '1px solid #1e1e1e',
    borderRadius: '10px',
    padding: '20px',
    marginBottom: '16px',
  },
  cardTitle: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#707070',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: '12px',
  },

  // KPI
  kpiRow: {
    display: 'flex',
    gap: '12px',
    marginBottom: '20px',
    flexWrap: 'wrap',
  },
  kpi: (color = '#22d3ee') => ({
    background: '#141414',
    border: '1px solid #1e1e1e',
    borderRadius: '10px',
    padding: '16px 20px',
    flex: '1',
    minWidth: '160px',
    borderTop: `3px solid ${color}`,
  }),
  kpiLabel: {
    fontSize: '11px',
    fontWeight: '500',
    color: '#707070',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  kpiValue: {
    fontSize: '26px',
    fontWeight: '700',
    color: '#ffffff',
    marginTop: '4px',
  },
  kpiSub: {
    fontSize: '12px',
    color: '#505050',
    marginTop: '2px',
  },

  // Table
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
  },
  th: {
    textAlign: 'left',
    padding: '10px 12px',
    color: '#606060',
    fontWeight: '600',
    fontSize: '11px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    borderBottom: '1px solid #1e1e1e',
  },
  td: {
    padding: '10px 12px',
    borderBottom: '1px solid #141414',
  },
  tr: {
    cursor: 'pointer',
    transition: 'background 0.15s',
  },

  // Badges
  badge: (type) => {
    const colors = {
      healthy: { bg: '#052e16', color: '#4ade80', border: '#166534' },
      at_risk: { bg: '#2a1f00', color: '#facc15', border: '#713f12' },
      danger: { bg: '#2a0000', color: '#f87171', border: '#7f1d1d' },
      hold: { bg: '#1a1a2e', color: '#818cf8', border: '#312e81' },
      reduce: { bg: '#2a0000', color: '#f87171', border: '#7f1d1d' },
      increase: { bg: '#052e16', color: '#4ade80', border: '#166534' },
    }
    const c = colors[type] || colors.hold
    return {
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: '4px',
      fontSize: '11px',
      fontWeight: '600',
      background: c.bg,
      color: c.color,
      border: `1px solid ${c.border}`,
    }
  },

  // Buttons
  btnPrimary: {
    padding: '10px 20px',
    borderRadius: '6px',
    border: 'none',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '600',
    color: '#0a0a0a',
    background: '#22d3ee',
    transition: 'opacity 0.2s',
  },
  btnSecondary: {
    padding: '10px 20px',
    borderRadius: '6px',
    border: '1px solid #2a2a2a',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
    color: '#a0a0a0',
    background: 'transparent',
    transition: 'all 0.2s',
  },

  // Forms
  input: {
    padding: '10px 14px',
    borderRadius: '6px',
    border: '1px solid #2a2a2a',
    background: '#0f0f0f',
    color: '#e0e0e0',
    fontSize: '13px',
    outline: 'none',
    width: '100%',
  },
  label: {
    fontSize: '11px',
    fontWeight: '500',
    color: '#707070',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: '4px',
    display: 'block',
  },
  formGroup: {
    marginBottom: '12px',
  },
  formRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
    gap: '12px',
    marginBottom: '12px',
  },

  // Utilities
  flex: { display: 'flex', alignItems: 'center', gap: '8px' },
  spaceBetween: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  mt: (n) => ({ marginTop: `${n}px` }),
  mb: (n) => ({ marginBottom: `${n}px` }),
  textMuted: { color: '#606060', fontSize: '12px' },
  textWhite: { color: '#ffffff' },
  textCyan: { color: '#22d3ee' },
  textRed: { color: '#f87171' },
  textGreen: { color: '#4ade80' },
  textYellow: { color: '#facc15' },
}

// ---------------------------------------------------------------------------
// HELPERS
// ---------------------------------------------------------------------------
const fmt = (n) => {
  if (n === null || n === undefined) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', maximumFractionDigits: 0,
  }).format(n)
}

const pct = (n) => {
  if (n === null || n === undefined) return '—'
  return `${(n * 100).toFixed(1)}%`
}

const agingLabel = {
  healthy: 'Healthy',
  at_risk: 'At Risk',
  danger: 'Danger Zone',
}

// ---------------------------------------------------------------------------
// MAIN APP
// ---------------------------------------------------------------------------
export default function App() {
  const [tab, setTab] = useState('dashboard')
  const [vehicles, setVehicles] = useState([])
  const [insights, setInsights] = useState([])
  const [selectedVehicle, setSelectedVehicle] = useState(null)
  const [alarm, setAlarm] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [vRes, iRes] = await Promise.all([
        API.get('/api/vehicles?status=active'),
        API.get('/api/inventory/insights?status=active'),
      ])
      setVehicles(vRes.data)
      setInsights(iRes.data)

      try {
        const aRes = await API.get('/api/alarms/latest')
        setAlarm(aRes.data)
      } catch (e) {
        // No alarm yet
      }
    } catch (e) {
      console.error('Load error:', e)
    }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const selectVehicle = (v) => {
    setSelectedVehicle(v)
    setTab('detail')
  }

  return (
    <div style={S.app}>
      {/* HEADER */}
      <div style={S.header}>
        <div style={S.logo}>
          <span style={S.logoAccent}>30</span>-
          <span style={S.logoAccent}>60</span>-
          <span style={S.logoAccent}>90</span>
        </div>
        <div style={S.nav}>
          <button style={S.navBtn(tab === 'dashboard')} onClick={() => setTab('dashboard')}>
            Dashboard
          </button>
          <button style={S.navBtn(tab === 'add')} onClick={() => setTab('add')}>
            + Add Vehicle
          </button>
          {selectedVehicle && (
            <button style={S.navBtn(tab === 'detail')} onClick={() => setTab('detail')}>
              Vehicle Detail
            </button>
          )}
        </div>
      </div>

      {/* MAIN */}
      <div style={S.main}>
        {loading && <div style={{ textAlign: 'center', padding: '40px', color: '#505050' }}>Loading...</div>}
        {!loading && tab === 'dashboard' && (
          <Dashboard
            insights={insights}
            alarm={alarm}
            vehicles={vehicles}
            onSelect={selectVehicle}
            onRefresh={load}
          />
        )}
        {!loading && tab === 'add' && (
          <AddVehicle onAdded={() => { load(); setTab('dashboard') }} />
        )}
        {!loading && tab === 'detail' && selectedVehicle && (
          <VehicleDetail
            vehicleId={selectedVehicle.vehicle_id || selectedVehicle.id}
            onBack={() => setTab('dashboard')}
            onRefresh={load}
          />
        )}
      </div>
    </div>
  )
}
// ---------------------------------------------------------------------------
// DASHBOARD
// ---------------------------------------------------------------------------
function Dashboard({ insights, alarm, vehicles, onSelect, onRefresh }) {
  const totalUnits = insights.length
  const totalDaily = insights.reduce((s, i) => s + (i.daily_carry_cost || 0), 0)
  const dangerCount = insights.filter(i => i.aging_class === 'danger').length
  const atRiskCount = insights.filter(i => i.aging_class === 'at_risk').length
  const avgDays = totalUnits > 0
    ? Math.round(insights.reduce((s, i) => s + i.days_in_inventory, 0) / totalUnits)
    : 0

  const runAlarm = async () => {
    try {
      await API.post('/api/alarms/run')
      const res = await API.get('/api/alarms/latest')
      window.location.reload()
    } catch (e) {
      console.error(e)
    }
  }

  const analyzeAll = async () => {
    try {
      await API.post('/api/vehicles/refresh-all-comps')
      await API.post('/api/vehicles/analyze-all')
      onRefresh()
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div>
      {/* Action bar */}
      <div style={{ ...S.spaceBetween, ...S.mb(20) }}>
        <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#fff' }}>
          Inventory Command Center
        </h2>
        <div style={S.flex}>
          <button style={S.btnSecondary} onClick={runAlarm}>Run Alarm</button>
          <button style={S.btnPrimary} onClick={analyzeAll}>Analyze All</button>
        </div>
      </div>

      {/* KPI Row */}
      <div style={S.kpiRow}>
        <div style={S.kpi('#22d3ee')}>
          <div style={S.kpiLabel}>Active Units</div>
          <div style={S.kpiValue}>{totalUnits}</div>
        </div>
        <div style={S.kpi('#f87171')}>
          <div style={S.kpiLabel}>Daily Burn</div>
          <div style={S.kpiValue}>{fmt(totalDaily)}</div>
          <div style={S.kpiSub}>{fmt(totalDaily * 30)}/mo projected</div>
        </div>
        <div style={S.kpi('#facc15')}>
          <div style={S.kpiLabel}>Avg Days</div>
          <div style={S.kpiValue}>{avgDays}</div>
        </div>
        <div style={S.kpi('#f87171')}>
          <div style={S.kpiLabel}>Danger Zone</div>
          <div style={S.kpiValue}>{dangerCount}</div>
          <div style={S.kpiSub}>{atRiskCount} at risk</div>
        </div>
      </div>

      {/* Alarm Card */}
      {alarm && <AlarmCard alarm={alarm} />}

      {/* Vehicle Table */}
      <div style={S.card}>
        <div style={S.cardTitle}>Active Inventory</div>
        {insights.length === 0 ? (
          <div style={{ padding: '30px', textAlign: 'center', color: '#505050' }}>
            No vehicles yet. Add one to get started.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={S.table}>
              <thead>
                <tr>
                  <th style={S.th}>Vehicle</th>
                  <th style={S.th}>VIN</th>
                  <th style={S.th}>Days</th>
                  <th style={S.th}>List Price</th>
                  <th style={S.th}>P(30)</th>
                  <th style={S.th}>P(60)</th>
                  <th style={S.th}>P(90)</th>
                  <th style={S.th}>Status</th>
                  <th style={S.th}>Daily Burn</th>
                  <th style={S.th}>Action</th>
                </tr>
              </thead>
              <tbody>
                {insights.map((v) => (
                  <tr
                    key={v.vehicle_id}
                    style={S.tr}
                    onClick={() => onSelect(v)}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#1a1a1a'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={S.td}>
                      <span style={S.textWhite}>
                        {v.year} {v.make} {v.model}
                      </span>
                      {v.trim && <span style={S.textMuted}> {v.trim}</span>}
                    </td>
                    <td style={{ ...S.td, fontFamily: 'monospace', fontSize: '11px', color: '#707070' }}>
                      {v.vin}
                    </td>
                    <td style={S.td}>
                      <span style={{
                        color: v.days_in_inventory > 60 ? '#f87171'
                          : v.days_in_inventory > 30 ? '#facc15' : '#4ade80'
                      }}>
                        {v.days_in_inventory}
                      </span>
                    </td>
                    <td style={{ ...S.td, ...S.textWhite }}>{fmt(v.list_price)}</td>
                    <td style={S.td}>{pct(v.p30)}</td>
                    <td style={S.td}>{pct(v.p60)}</td>
                    <td style={S.td}>{pct(v.p90)}</td>
                    <td style={S.td}>
                      {v.aging_class && (
                        <span style={S.badge(v.aging_class)}>
                          {agingLabel[v.aging_class] || v.aging_class}
                        </span>
                      )}
                    </td>
                    <td style={{ ...S.td, ...S.textRed }}>
                      {v.daily_carry_cost ? fmt(v.daily_carry_cost) : '—'}/day
                    </td>
                    <td style={{ ...S.td, fontSize: '12px', maxWidth: '200px' }}>
                      {v.price_action && (
                        <span style={{ ...S.badge(v.price_action), marginRight: '6px' }}>
                          {v.price_action}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}


// ---------------------------------------------------------------------------
// ALARM CARD
// ---------------------------------------------------------------------------
function AlarmCard({ alarm }) {
  return (
    <div style={{
      ...S.card,
      borderLeft: '3px solid #f87171',
      background: '#1a0a0a',
    }}>
      <div style={S.spaceBetween}>
        <div style={S.cardTitle}>⚠ Floorplan Alarm — {alarm.alarm_date}</div>
        <span style={S.textMuted}>{alarm.total_active_units} units</span>
      </div>

      {/* Alarm KPIs */}
      <div style={{ ...S.kpiRow, ...S.mt(8) }}>
        <div style={S.kpi('#f87171')}>
          <div style={S.kpiLabel}>Daily Burn</div>
          <div style={{ ...S.kpiValue, fontSize: '20px' }}>{fmt(alarm.total_daily_burn)}</div>
        </div>
        <div style={S.kpi('#facc15')}>
          <div style={S.kpiLabel}>30-Day Projected</div>
          <div style={{ ...S.kpiValue, fontSize: '20px' }}>{fmt(alarm.projected_burn_30)}</div>
        </div>
        <div style={S.kpi('#f87171')}>
          <div style={S.kpiLabel}>60-Day Projected</div>
          <div style={{ ...S.kpiValue, fontSize: '20px' }}>{fmt(alarm.projected_burn_60)}</div>
        </div>
        <div style={S.kpi('#f87171')}>
          <div style={S.kpiLabel}>Underwater</div>
          <div style={{ ...S.kpiValue, fontSize: '20px' }}>
            {alarm.underwater_vehicles ? alarm.underwater_vehicles.length : 0}
          </div>
        </div>
      </div>

      {/* Executive Summary */}
      <div style={{
        padding: '12px 16px',
        background: '#0f0505',
        borderRadius: '6px',
        fontSize: '13px',
        lineHeight: '1.6',
        color: '#c0c0c0',
        ...S.mt(8),
      }}>
        {alarm.executive_summary}
      </div>

      {/* Top Burners */}
      {alarm.top_burners && alarm.top_burners.length > 0 && (
        <div style={S.mt(12)}>
          <div style={{ ...S.cardTitle, fontSize: '11px' }}>Top Burners</div>
          {alarm.top_burners.map((b, i) => (
            <div key={i} style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '6px 0',
              borderBottom: '1px solid #1e1e1e',
              fontSize: '12px',
            }}>
              <span style={S.textWhite}>
                {b.year} {b.make} {b.model}
                <span style={{ ...S.textMuted, marginLeft: '8px' }}>{b.vin}</span>
              </span>
              <span>
                <span style={S.textRed}>{fmt(b.daily_cost)}/day</span>
                <span style={{ ...S.textMuted, marginLeft: '12px' }}>{b.days} days</span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


// ---------------------------------------------------------------------------
// ADD VEHICLE
// ---------------------------------------------------------------------------
function AddVehicle({ onAdded }) {
  const [vin, setVin] = useState('')
  const [fields, setFields] = useState({
    acquisition_cost: '',
    recon_cost: '',
    list_price: '',
    floorplan_rate_apr: '6.5',
    wholesale_exit_price: '',
    min_acceptable_margin: '500',
    mileage: '',
    date_acquired: new Date().toISOString().split('T')[0],
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [decoded, setDecoded] = useState(null)

  const handleVin = async () => {
    if (vin.length !== 17) return
    setError(null)
    try {
      // Just submit with VIN — backend decodes
      setDecoded({ status: 'ready', vin: vin.toUpperCase() })
    } catch (e) {
      setError('VIN lookup failed')
    }
  }

  const submit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const payload = {
        vin: vin.toUpperCase(),
        acquisition_cost: parseFloat(fields.acquisition_cost) || 0,
        recon_cost: parseFloat(fields.recon_cost) || 0,
        list_price: parseFloat(fields.list_price) || 0,
        floorplan_rate_apr: parseFloat(fields.floorplan_rate_apr) || 6.5,
        wholesale_exit_price: parseFloat(fields.wholesale_exit_price) || 0,
        min_acceptable_margin: parseFloat(fields.min_acceptable_margin) || 500,
        mileage: parseInt(fields.mileage) || 0,
        date_acquired: fields.date_acquired || null,
      }
      const res = await API.post('/api/vehicles/from-vin', payload)

      // Auto-refresh comps and analyze
      try {
        await API.post(`/api/vehicles/${res.data.id}/comps/refresh`)
        await API.post(`/api/vehicles/${res.data.id}/analyze`)
      } catch (e) {
        // Non-fatal
      }

      onAdded()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to add vehicle')
    }
    setSubmitting(false)
  }

  const updateField = (key, val) => setFields(f => ({ ...f, [key]: val }))

  return (
    <div style={{ maxWidth: '700px' }}>
      <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#fff', ...S.mb(20) }}>
        Add Vehicle
      </h2>

      {/* VIN Input */}
      <div style={S.card}>
        <div style={S.cardTitle}>VIN Decode</div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            style={{ ...S.input, fontFamily: 'monospace', fontSize: '15px', letterSpacing: '1px' }}
            placeholder="Enter 17-character VIN"
            value={vin}
            onChange={(e) => setVin(e.target.value.toUpperCase().slice(0, 17))}
            maxLength={17}
          />
          <button
            style={S.btnPrimary}
            onClick={handleVin}
            disabled={vin.length !== 17}
          >
            Decode
          </button>
        </div>
        {decoded && (
          <div style={{ ...S.mt(8), fontSize: '12px', ...S.textCyan }}>
            ✓ VIN ready — fill financials below and submit
          </div>
        )}
        {vin.length > 0 && vin.length < 17 && (
          <div style={{ ...S.mt(4), fontSize: '11px', color: '#505050' }}>
            {17 - vin.length} characters remaining
          </div>
        )}
      </div>

      {/* Financials */}
      <div style={S.card}>
        <div style={S.cardTitle}>Vehicle Financials</div>
        <div style={S.formRow}>
          {[
            ['acquisition_cost', 'Acquisition Cost ($)'],
            ['recon_cost', 'Recon Cost ($)'],
            ['list_price', 'List Price ($)'],
            ['wholesale_exit_price', 'Wholesale Exit ($)'],
            ['mileage', 'Mileage'],
            ['floorplan_rate_apr', 'Floorplan APR (%)'],
            ['min_acceptable_margin', 'Min Margin ($)'],
            ['date_acquired', 'Date Acquired'],
          ].map(([key, label]) => (
            <div key={key} style={S.formGroup}>
              <label style={S.label}>{label}</label>
              <input
                style={S.input}
                type={key === 'date_acquired' ? 'date' : 'text'}
                value={fields[key]}
                onChange={(e) => updateField(key, e.target.value)}
              />
            </div>
          ))}
        </div>
      </div>

      {error && (
        <div style={{ padding: '10px 14px', background: '#2a0000', border: '1px solid #7f1d1d', borderRadius: '6px', color: '#f87171', fontSize: '13px', ...S.mb(12) }}>
          {error}
        </div>
      )}

      <button
        style={{ ...S.btnPrimary, width: '100%', padding: '14px', fontSize: '15px' }}
        onClick={submit}
        disabled={vin.length !== 17 || submitting}
      >
        {submitting ? 'Adding...' : 'Add Vehicle & Analyze'}
      </button>
    </div>
  )
}
// ---------------------------------------------------------------------------
// VEHICLE DETAIL — Main Container
// ---------------------------------------------------------------------------
function VehicleDetail({ vehicleId, onBack, onRefresh }) {
  const [vehicle, setVehicle] = useState(null)
  const [report, setReport] = useState(null)
  const [compSummary, setCompSummary] = useState(null)
  const [waterfall, setWaterfall] = useState(null)
  const [priceEvents, setPriceEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [detailTab, setDetailTab] = useState('analysis')

  const loadDetail = useCallback(async () => {
    setLoading(true)
    try {
      const vRes = await API.get(`/api/vehicles/${vehicleId}`)
      setVehicle(vRes.data)

      // Load analysis (latest)
      try {
        const aRes = await API.post(`/api/vehicles/${vehicleId}/analyze`)
        setReport(aRes.data)
      } catch (e) {
        // Try fetching curve as fallback
        try {
          const cRes = await API.get(`/api/vehicles/${vehicleId}/curve?days=90`)
          setReport(prev => prev ? { ...prev, daily_curve: cRes.data.curve } : null)
        } catch (e2) { /* no analysis yet */ }
      }

      // Comp summary
      try {
        const csRes = await API.get(`/api/vehicles/${vehicleId}/comps/summary`)
        setCompSummary(csRes.data)
      } catch (e) { /* no comps */ }

      // Waterfall
      try {
        const wRes = await API.post(`/api/vehicles/${vehicleId}/pricing-waterfall/plan`)
        setWaterfall(wRes.data)
      } catch (e) { /* no waterfall */ }

      // Price events
      try {
        const peRes = await API.get(`/api/vehicles/${vehicleId}/price-events`)
        setPriceEvents(peRes.data)
      } catch (e) { /* no events */ }

    } catch (e) {
      console.error('Detail load error:', e)
    }
    setLoading(false)
  }, [vehicleId])

  useEffect(() => { loadDetail() }, [loadDetail])

  const reAnalyze = async () => {
    setAnalyzing(true)
    try {
      await API.post(`/api/vehicles/${vehicleId}/comps/refresh`)
      const aRes = await API.post(`/api/vehicles/${vehicleId}/analyze`)
      setReport(aRes.data)
      const csRes = await API.get(`/api/vehicles/${vehicleId}/comps/summary`)
      setCompSummary(csRes.data)
      const wRes = await API.post(`/api/vehicles/${vehicleId}/pricing-waterfall/plan`)
      setWaterfall(wRes.data)
      onRefresh()
    } catch (e) {
      console.error(e)
    }
    setAnalyzing(false)
  }

  if (loading) return <div style={{ padding: '40px', textAlign: 'center', color: '#505050' }}>Loading vehicle...</div>
  if (!vehicle) return <div style={{ padding: '40px', color: '#f87171' }}>Vehicle not found.</div>

  return (
    <div>
      {/* Back + Title */}
      <div style={{ ...S.spaceBetween, ...S.mb(20) }}>
        <div>
          <button onClick={onBack} style={{ ...S.btnSecondary, marginRight: '12px', padding: '6px 14px' }}>
            ← Back
          </button>
          <span style={{ fontSize: '20px', fontWeight: '700', color: '#fff' }}>
            {vehicle.year} {vehicle.make} {vehicle.model}
          </span>
          {vehicle.trim && <span style={{ ...S.textMuted, marginLeft: '8px' }}>{vehicle.trim}</span>}
          <span style={{ fontFamily: 'monospace', fontSize: '12px', color: '#505050', marginLeft: '16px' }}>
            {vehicle.vin}
          </span>
        </div>
        <button
          style={S.btnPrimary}
          onClick={reAnalyze}
          disabled={analyzing}
        >
          {analyzing ? 'Analyzing...' : '↻ Re-Analyze'}
        </button>
      </div>

      {/* Vehicle KPIs */}
      <div style={S.kpiRow}>
        <div style={S.kpi('#22d3ee')}>
          <div style={S.kpiLabel}>List Price</div>
          <div style={S.kpiValue}>{fmt(vehicle.list_price)}</div>
        </div>
        <div style={S.kpi('#818cf8')}>
          <div style={S.kpiLabel}>Total Cost</div>
          <div style={S.kpiValue}>{fmt(vehicle.acquisition_cost + vehicle.recon_cost)}</div>
          <div style={S.kpiSub}>Acq {fmt(vehicle.acquisition_cost)} + Recon {fmt(vehicle.recon_cost)}</div>
        </div>
        <div style={S.kpi(vehicle.days_in_inventory > 60 ? '#f87171' : vehicle.days_in_inventory > 30 ? '#facc15' : '#4ade80')}>
          <div style={S.kpiLabel}>Days in Inventory</div>
          <div style={S.kpiValue}>{vehicle.days_in_inventory}</div>
        </div>
        <div style={S.kpi('#4ade80')}>
          <div style={S.kpiLabel}>Potential Gross</div>
          <div style={S.kpiValue}>{fmt(vehicle.list_price - vehicle.acquisition_cost - vehicle.recon_cost)}</div>
        </div>
        <div style={S.kpi('#f87171')}>
          <div style={S.kpiLabel}>Wholesale Exit</div>
          <div style={S.kpiValue}>{fmt(vehicle.wholesale_exit_price)}</div>
        </div>
      </div>

      {/* Sub-tabs */}
      <div style={{ ...S.flex, ...S.mb(16), gap: '4px' }}>
        {['analysis', 'curve', 'comps', 'waterfall', 'history'].map(t => (
          <button
            key={t}
            style={S.navBtn(detailTab === t)}
            onClick={() => setDetailTab(t)}
          >
            {t === 'analysis' ? '📊 Analysis' :
             t === 'curve' ? '📈 90-Day Curve' :
             t === 'comps' ? '🔍 Comps' :
             t === 'waterfall' ? '💧 Waterfall' :
             '📋 Price History'}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {detailTab === 'analysis' && report && <AnalysisPanel report={report} />}
      {detailTab === 'analysis' && !report && (
        <div style={{ ...S.card, textAlign: 'center', color: '#505050', padding: '40px' }}>
          No analysis yet. Click Re-Analyze above.
        </div>
      )}
      {detailTab === 'curve' && report && report.daily_curve && (
        <CurveChart curve={report.daily_curve} inflectionDay={report.inflection_day} />
      )}
      {detailTab === 'curve' && (!report || !report.daily_curve) && (
        <div style={{ ...S.card, textAlign: 'center', color: '#505050', padding: '40px' }}>
          No curve data. Run analysis first.
        </div>
      )}
      {detailTab === 'comps' && <CompsPanel vehicleId={vehicleId} summary={compSummary} />}
      {detailTab === 'waterfall' && <WaterfallPanel vehicleId={vehicleId} plan={waterfall} onRefresh={loadDetail} />}
      {detailTab === 'history' && <PriceHistoryPanel events={priceEvents} />}
    </div>
  )
}


// ---------------------------------------------------------------------------
// ANALYSIS PANEL
// ---------------------------------------------------------------------------
function AnalysisPanel({ report }) {
  return (
    <div>
      {/* Probability Row */}
      <div style={S.kpiRow}>
        <div style={S.kpi('#4ade80')}>
          <div style={S.kpiLabel}>P(Sell 30 Days)</div>
          <div style={S.kpiValue}>{pct(report.p30)}</div>
        </div>
        <div style={S.kpi('#facc15')}>
          <div style={S.kpiLabel}>P(Sell 60 Days)</div>
          <div style={S.kpiValue}>{pct(report.p60)}</div>
        </div>
        <div style={S.kpi('#22d3ee')}>
          <div style={S.kpiLabel}>P(Sell 90 Days)</div>
          <div style={S.kpiValue}>{pct(report.p90)}</div>
        </div>
        <div style={S.kpi(report.aging_class === 'danger' ? '#f87171' : report.aging_class === 'at_risk' ? '#facc15' : '#4ade80')}>
          <div style={S.kpiLabel}>Classification</div>
          <div style={{ ...S.kpiValue, fontSize: '20px' }}>
            <span style={S.badge(report.aging_class)}>
              {agingLabel[report.aging_class] || report.aging_class}
            </span>
          </div>
        </div>
        <div style={S.kpi('#f87171')}>
          <div style={S.kpiLabel}>Inflection Day</div>
          <div style={S.kpiValue}>{report.inflection_day}</div>
          <div style={S.kpiSub}>When holding becomes irrational</div>
        </div>
      </div>

      {/* Two-column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>

        {/* Carry Cost + Erosion */}
        <div style={S.card}>
          <div style={S.cardTitle}>Carry Cost & Margin Erosion</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <div>
              <div style={S.kpiLabel}>Daily Carry</div>
              <div style={{ fontSize: '18px', fontWeight: '700', ...S.textRed }}>{fmt(report.daily_carry_cost)}</div>
            </div>
            <div>
              <div style={S.kpiLabel}>Carry @ 30d</div>
              <div style={{ fontSize: '16px', fontWeight: '600', color: '#e0e0e0' }}>{fmt(report.carry_cost_30)}</div>
            </div>
            <div>
              <div style={S.kpiLabel}>Carry @ 60d</div>
              <div style={{ fontSize: '16px', fontWeight: '600', color: '#e0e0e0' }}>{fmt(report.carry_cost_60)}</div>
            </div>
            <div>
              <div style={S.kpiLabel}>Carry @ 90d</div>
              <div style={{ fontSize: '16px', fontWeight: '600', color: '#e0e0e0' }}>{fmt(report.carry_cost_90)}</div>
            </div>
          </div>
          <div style={{ ...S.mt(12), borderTop: '1px solid #1e1e1e', paddingTop: '12px' }}>
            <div style={S.kpiLabel}>Net Gross if Sold At</div>
            <div style={{ display: 'flex', gap: '16px', ...S.mt(4) }}>
              <span style={{ fontSize: '13px' }}>30d: <strong style={report.margin_erosion_30 < 0 ? S.textRed : S.textGreen}>{fmt(report.margin_erosion_30)}</strong></span>
              <span style={{ fontSize: '13px' }}>60d: <strong style={report.margin_erosion_60 < 0 ? S.textRed : S.textGreen}>{fmt(report.margin_erosion_60)}</strong></span>
              <span style={{ fontSize: '13px' }}>90d: <strong style={report.margin_erosion_90 < 0 ? S.textRed : S.textGreen}>{fmt(report.margin_erosion_90)}</strong></span>
            </div>
          </div>
        </div>

        {/* Pricing Strategy */}
        <div style={S.card}>
          <div style={S.cardTitle}>Pricing Strategy</div>
          <div style={{ ...S.flex, ...S.mb(12) }}>
            <span style={S.badge(report.price_action)}>{report.price_action.toUpperCase()}</span>
            {report.price_change_amount > 0 && (
              <span style={{ fontSize: '18px', fontWeight: '700', color: '#fff' }}>
                {report.price_action === 'reduce' ? '−' : '+'}{fmt(report.price_change_amount)}
              </span>
            )}
          </div>
          <div style={{ fontSize: '13px', color: '#a0a0a0', lineHeight: '1.6' }}>
            <div>Expected probability lift: <strong style={S.textCyan}>{pct(report.price_action_lift_p)}</strong></div>
            <div>Expected gross impact: <strong style={report.price_action_gross_impact >= 0 ? S.textGreen : S.textRed}>{fmt(report.price_action_gross_impact)}</strong></div>
            <div style={S.mt(8)}>
              Elasticity: <span style={S.badge(report.price_elasticity === 'high' ? 'danger' : report.price_elasticity === 'low' ? 'healthy' : 'at_risk')}>
                {report.price_elasticity}
              </span>
            </div>
            <div style={{ ...S.mt(4), fontSize: '12px', color: '#707070' }}>{report.elasticity_reason}</div>
          </div>
        </div>

        {/* Exit Path */}
        <div style={S.card}>
          <div style={S.cardTitle}>Optimal Exit Path</div>
          <div style={{ ...S.flex, ...S.mb(8) }}>
            <span style={{
              ...S.badge(report.optimal_exit === 'retail' ? 'healthy' : report.optimal_exit === 'wholesale_auction' ? 'danger' : 'at_risk'),
              fontSize: '13px',
              padding: '4px 12px',
            }}>
              {report.optimal_exit === 'retail' ? '🏪 Retail' :
               report.optimal_exit === 'wholesale_auction' ? '🔨 Wholesale/Auction' :
               '🤝 Dealer Trade'}
            </span>
          </div>
          <div style={{ fontSize: '13px', color: '#a0a0a0', lineHeight: '1.6' }}>
            <div>Expected gross: <strong style={S.textGreen}>{fmt(report.exit_expected_gross)}</strong></div>
            <div>Expected days to exit: <strong style={S.textCyan}>{report.exit_expected_days}</strong></div>
            <div style={{ ...S.mt(8), fontSize: '12px', color: '#707070' }}>{report.exit_reason}</div>
          </div>
        </div>

        {/* Risk & Confidence */}
        <div style={S.card}>
          <div style={S.cardTitle}>Risk & Confidence</div>
          <div style={{ ...S.mb(8) }}>
            Confidence: <span style={S.badge(
              report.confidence === 'high' ? 'healthy' : report.confidence === 'low' ? 'danger' : 'at_risk'
            )}>{report.confidence}</span>
          </div>
          <div style={S.kpiLabel}>Risks</div>
          <ul style={{ paddingLeft: '16px', fontSize: '12px', color: '#a0a0a0', lineHeight: '1.8' }}>
            {(report.risks || []).map((r, i) => <li key={i}>{r}</li>)}
          </ul>
          <div style={{ ...S.kpiLabel, ...S.mt(8) }}>What Would Change the Call</div>
          <ul style={{ paddingLeft: '16px', fontSize: '12px', color: '#a0a0a0', lineHeight: '1.8' }}>
            {(report.change_triggers || []).map((t, i) => <li key={i}>{t}</li>)}
          </ul>
        </div>
      </div>

      {/* Action Plan — full width */}
      <div style={{ ...S.card, borderLeft: '3px solid #22d3ee' }}>
        <div style={S.cardTitle}>⚡ This Week's Action Plan</div>
        {(report.action_plan || []).map((a, i) => (
          <div key={i} style={{
            padding: '10px 14px',
            background: i % 2 === 0 ? '#0f1a1a' : 'transparent',
            borderRadius: '4px',
            fontSize: '13px',
            color: '#d0d0d0',
            lineHeight: '1.5',
            display: 'flex',
            gap: '10px',
          }}>
            <span style={{ color: '#22d3ee', fontWeight: '700', minWidth: '20px' }}>{i + 1}.</span>
            {a}
          </div>
        ))}
      </div>
    </div>
  )
}
// ---------------------------------------------------------------------------
// 90-DAY CURVE CHART (Hoverable)
// ---------------------------------------------------------------------------
function CurveChart({ curve, inflectionDay }) {
  if (!curve || curve.length === 0) return null

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null
    const d = payload[0].payload
    return (
      <div style={{
        background: '#1a1a1a',
        border: '1px solid #2a2a2a',
        borderRadius: '8px',
        padding: '12px 16px',
        fontSize: '12px',
        lineHeight: '1.8',
        minWidth: '200px',
      }}>
        <div style={{ fontWeight: '700', color: '#fff', fontSize: '13px', marginBottom: '4px' }}>
          Day {d.day}
        </div>
        <div style={{ color: '#22d3ee' }}>
          Daily P(sell): <strong>{(d.daily_sell_probability * 100).toFixed(2)}%</strong>
        </div>
        <div style={{ color: '#818cf8' }}>
          Cumulative P: <strong>{(d.cumulative_sell_probability * 100).toFixed(1)}%</strong>
        </div>
        <div style={{ color: '#f87171' }}>
          Floorplan cost: <strong>{fmt(d.floorplan_cost_to_date)}</strong>
        </div>
        <div style={{ color: '#facc15' }}>
          Gross erosion: <strong>{fmt(d.gross_erosion_to_date)}</strong>
        </div>
      </div>
    )
  }

  // Add inflection marker to data
  const chartData = curve.map(d => ({
    ...d,
    cumPct: d.cumulative_sell_probability * 100,
    dailyPct: d.daily_sell_probability * 100,
    isInflection: d.day === inflectionDay,
  }))

  return (
    <div style={S.card}>
      <div style={S.spaceBetween}>
        <div style={S.cardTitle}>90-Day Probability & Cost Curve</div>
        {inflectionDay && (
          <div style={{ fontSize: '12px', color: '#f87171' }}>
            ⚠ Inflection point: Day {inflectionDay}
          </div>
        )}
      </div>

      {/* Cumulative Probability + Floorplan Cost */}
      <div style={S.mt(12)}>
        <div style={{ fontSize: '11px', color: '#505050', marginBottom: '4px' }}>
          Cumulative Sell Probability (%) & Floorplan Cost ($)
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="gradCum" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradCost" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f87171" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e1e1e" />
            <XAxis
              dataKey="day"
              stroke="#404040"
              tick={{ fontSize: 10, fill: '#505050' }}
              tickLine={false}
            />
            <YAxis
              yAxisId="pct"
              stroke="#404040"
              tick={{ fontSize: 10, fill: '#505050' }}
              tickLine={false}
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
            />
            <YAxis
              yAxisId="cost"
              orientation="right"
              stroke="#404040"
              tick={{ fontSize: 10, fill: '#505050' }}
              tickLine={false}
              tickFormatter={(v) => `$${v}`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              yAxisId="pct"
              type="monotone"
              dataKey="cumPct"
              stroke="#22d3ee"
              strokeWidth={2}
              fill="url(#gradCum)"
              name="Cum. Probability"
            />
            <Area
              yAxisId="cost"
              type="monotone"
              dataKey="floorplan_cost_to_date"
              stroke="#f87171"
              strokeWidth={2}
              fill="url(#gradCost)"
              name="Floorplan Cost"
            />
            {inflectionDay && (
              <CartesianGrid
                strokeDasharray="6 4"
                stroke="#f87171"
                horizontalPoints={[]}
                verticalPoints={[inflectionDay]}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Daily Probability Bar */}
      <div style={S.mt(24)}>
        <div style={{ fontSize: '11px', color: '#505050', marginBottom: '4px' }}>
          Daily Sell Probability (%)
        </div>
        <ResponsiveContainer width="100%" height={150}>
          <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e1e1e" />
            <XAxis
              dataKey="day"
              stroke="#404040"
              tick={{ fontSize: 10, fill: '#505050' }}
              tickLine={false}
            />
            <YAxis
              stroke="#404040"
              tick={{ fontSize: 10, fill: '#505050' }}
              tickLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="dailyPct" radius={[2, 2, 0, 0]}>
              {chartData.map((entry, idx) => (
                <Cell
                  key={idx}
                  fill={entry.day <= 30 ? '#4ade80' : entry.day <= 60 ? '#facc15' : '#f87171'}
                  opacity={0.7}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: '24px', ...S.mt(12), fontSize: '11px' }}>
        <span><span style={{ color: '#22d3ee' }}>■</span> Cumulative sell probability</span>
        <span><span style={{ color: '#f87171' }}>■</span> Floorplan cost</span>
        <span><span style={{ color: '#4ade80' }}>■</span> Days 1-30</span>
        <span><span style={{ color: '#facc15' }}>■</span> Days 31-60</span>
        <span><span style={{ color: '#f87171' }}>■</span> Days 61-90</span>
        {inflectionDay && <span><span style={{ color: '#f87171' }}>┊</span> Inflection day {inflectionDay}</span>}
      </div>
    </div>
  )
}


// ---------------------------------------------------------------------------
// COMPS PANEL
// ---------------------------------------------------------------------------
function CompsPanel({ vehicleId, summary }) {
  const [comps, setComps] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const res = await API.get(`/api/vehicles/${vehicleId}/comps?source=all`)
        setComps(res.data)
      } catch (e) { /* no comps */ }
      setLoading(false)
    }
    load()
  }, [vehicleId])

  return (
    <div>
      {/* Summary Card */}
      {summary && (
        <div style={S.card}>
          <div style={S.cardTitle}>Comp Summary</div>
          <div style={S.kpiRow}>
            <div style={S.kpi('#22d3ee')}>
              <div style={S.kpiLabel}>Median Price</div>
              <div style={{ ...S.kpiValue, fontSize: '20px' }}>{fmt(summary.median_price)}</div>
            </div>
            <div style={S.kpi('#818cf8')}>
              <div style={S.kpiLabel}>Price Range</div>
              <div style={{ ...S.kpiValue, fontSize: '16px' }}>{fmt(summary.low_price)} — {fmt(summary.high_price)}</div>
            </div>
            <div style={S.kpi('#facc15')}>
              <div style={S.kpiLabel}>Median Days to Sale</div>
              <div style={{ ...S.kpiValue, fontSize: '20px' }}>{summary.median_days_to_sale || '—'}</div>
            </div>
            <div style={S.kpi('#4ade80')}>
              <div style={S.kpiLabel}>Supply vs Demand</div>
              <div style={{ ...S.kpiValue, fontSize: '16px' }}>{summary.supply_vs_demand || '—'}</div>
              <div style={S.kpiSub}>Demand score: {summary.demand_score}</div>
            </div>
            <div style={S.kpi('#818cf8')}>
              <div style={S.kpiLabel}>Comp Count</div>
              <div style={{ ...S.kpiValue, fontSize: '20px' }}>{summary.auto_count + summary.manual_count}</div>
              <div style={S.kpiSub}>{summary.auto_count} auto / {summary.manual_count} manual</div>
            </div>
          </div>

          {/* Discrepancy Warning */}
          {summary.discrepancy_flag && (
            <div style={{
              padding: '10px 14px',
              background: '#2a1f00',
              border: '1px solid #713f12',
              borderRadius: '6px',
              fontSize: '12px',
              lineHeight: '1.6',
              ...S.mt(8),
            }}>
              <div style={{ fontWeight: '600', color: '#facc15', marginBottom: '4px' }}>
                ⚠ Data Discrepancy Detected
              </div>
              <div style={{ color: '#c0a000' }}>{summary.discrepancy_note}</div>
              <div style={{ color: '#a0a0a0', ...S.mt(4) }}>
                <strong>Weighted source:</strong> {summary.weighted_source} — {summary.weight_reason}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Comp Table */}
      <div style={S.card}>
        <div style={S.spaceBetween}>
          <div style={S.cardTitle}>Comparable Vehicles ({comps.length})</div>
        </div>
        {loading ? (
          <div style={{ padding: '20px', color: '#505050' }}>Loading comps...</div>
        ) : comps.length === 0 ? (
          <div style={{ padding: '20px', color: '#505050' }}>No comps found. Run comp refresh.</div>
        ) : (
          <div style={{ overflowX: 'auto', maxHeight: '400px', overflowY: 'auto' }}>
            <table style={S.table}>
              <thead>
                <tr>
                  <th style={{ ...S.th, position: 'sticky', top: 0, background: '#141414' }}>Source</th>
                  <th style={{ ...S.th, position: 'sticky', top: 0, background: '#141414' }}>Vehicle</th>
                  <th style={{ ...S.th, position: 'sticky', top: 0, background: '#141414' }}>Mileage</th>
                  <th style={{ ...S.th, position: 'sticky', top: 0, background: '#141414' }}>Price</th>
                  <th style={{ ...S.th, position: 'sticky', top: 0, background: '#141414' }}>Sold Price</th>
                  <th style={{ ...S.th, position: 'sticky', top: 0, background: '#141414' }}>DOM</th>
                  <th style={{ ...S.th, position: 'sticky', top: 0, background: '#141414' }}>Distance</th>
                  <th style={{ ...S.th, position: 'sticky', top: 0, background: '#141414' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {comps.map(c => (
                  <tr key={c.id}>
                    <td style={S.td}>
                      <span style={S.badge(c.source === 'auto' ? 'healthy' : 'at_risk')}>
                        {c.source}
                      </span>
                    </td>
                    <td style={{ ...S.td, ...S.textWhite }}>
                      {c.year} {c.make} {c.model} {c.trim || ''}
                    </td>
                    <td style={S.td}>{c.mileage ? c.mileage.toLocaleString() : '—'}</td>
                    <td style={{ ...S.td, ...S.textWhite }}>{fmt(c.price)}</td>
                    <td style={{ ...S.td, ...(c.sold_price ? S.textGreen : S.textMuted) }}>
                      {c.sold_price ? fmt(c.sold_price) : '—'}
                    </td>
                    <td style={S.td}>{c.days_on_market || '—'}</td>
                    <td style={S.td}>{c.distance_miles ? `${c.distance_miles} mi` : '—'}</td>
                    <td style={S.td}>
                      <span style={S.badge(c.listing_status === 'sold' ? 'healthy' : c.listing_status === 'delisted' ? 'danger' : 'hold')}>
                        {c.listing_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}


// ---------------------------------------------------------------------------
// WATERFALL PANEL
// ---------------------------------------------------------------------------
function WaterfallPanel({ vehicleId, plan, onRefresh }) {
  const [applying, setApplying] = useState(null)

  const applyStep = async (stepNum) => {
    setApplying(stepNum)
    try {
      await API.post(`/api/vehicles/${vehicleId}/pricing-waterfall/apply?step=${stepNum}`)
      onRefresh()
    } catch (e) {
      console.error(e)
    }
    setApplying(null)
  }

  if (!plan) {
    return (
      <div style={{ ...S.card, textAlign: 'center', color: '#505050', padding: '40px' }}>
        No waterfall plan available.
      </div>
    )
  }

  return (
    <div>
      {/* Plan Header */}
      <div style={S.card}>
        <div style={S.cardTitle}>Pricing Waterfall Plan</div>
        <div style={S.kpiRow}>
          <div style={S.kpi('#22d3ee')}>
            <div style={S.kpiLabel}>Current Price</div>
            <div style={{ ...S.kpiValue, fontSize: '20px' }}>{fmt(plan.current_price)}</div>
          </div>
          <div style={S.kpi('#818cf8')}>
            <div style={S.kpiLabel}>Total Cost</div>
            <div style={{ ...S.kpiValue, fontSize: '20px' }}>{fmt(plan.total_cost)}</div>
          </div>
          <div style={S.kpi('#f87171')}>
            <div style={S.kpiLabel}>Wholesale Exit</div>
            <div style={{ ...S.kpiValue, fontSize: '20px' }}>{fmt(plan.wholesale_exit_price)}</div>
          </div>
        </div>
        <div style={{ fontSize: '13px', color: '#a0a0a0', ...S.mt(4) }}>
          {plan.recommendation}
        </div>
      </div>

      {/* Steps */}
      {plan.steps && plan.steps.map((step) => (
        <div key={step.step} style={{
          ...S.card,
          borderLeft: `3px solid ${step.stop_condition === 'Wholesale exit superior' ? '#f87171' : '#22d3ee'}`,
        }}>
          <div style={S.spaceBetween}>
            <div>
              <span style={{
                display: 'inline-block',
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                background: '#22d3ee',
                color: '#0a0a0a',
                textAlign: 'center',
                lineHeight: '28px',
                fontWeight: '700',
                fontSize: '13px',
                marginRight: '10px',
              }}>
                {step.step}
              </span>
              <span style={{ fontWeight: '600', color: '#fff', fontSize: '14px' }}>
                {step.trigger_condition}
              </span>
            </div>
            <button
              style={{
                ...S.btnPrimary,
                padding: '6px 14px',
                fontSize: '12px',
                opacity: applying === step.step ? 0.5 : 1,
              }}
              onClick={() => applyStep(step.step)}
              disabled={applying === step.step}
            >
              {applying === step.step ? 'Applying...' : 'Apply'}
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', ...S.mt(12) }}>
            <div>
              <div style={S.kpiLabel}>Price Change</div>
              <div style={{ fontSize: '16px', fontWeight: '700', ...S.textRed }}>
                {fmt(step.dollar_change)}
              </div>
              <div style={S.kpiSub}>{fmt(step.current_price)} → {fmt(step.new_price)}</div>
            </div>
            <div>
              <div style={S.kpiLabel}>Probability Lift</div>
              <div style={{ fontSize: '16px', fontWeight: '700', ...S.textGreen }}>
                +{pct(step.expected_probability_lift)}
              </div>
            </div>
            <div>
              <div style={S.kpiLabel}>Days Saved</div>
              <div style={{ fontSize: '16px', fontWeight: '700', ...S.textCyan }}>
                {step.expected_days_saved}
              </div>
            </div>
            <div>
              <div style={S.kpiLabel}>Price Floor</div>
              <div style={{ fontSize: '16px', fontWeight: '700', color: '#e0e0e0' }}>
                {fmt(step.price_floor)}
              </div>
            </div>
          </div>

          {step.stop_condition === 'Wholesale exit superior' && (
            <div style={{
              ...S.mt(8),
              padding: '6px 12px',
              background: '#2a0000',
              borderRadius: '4px',
              fontSize: '11px',
              color: '#f87171',
            }}>
              ⚠ Beyond this point, wholesale exit is the better economic decision.
            </div>
          )}
        </div>
      ))}
    </div>
  )
}


// ---------------------------------------------------------------------------
// PRICE HISTORY PANEL
// ---------------------------------------------------------------------------
function PriceHistoryPanel({ events }) {
  if (!events || events.length === 0) {
    return (
      <div style={{ ...S.card, textAlign: 'center', color: '#505050', padding: '40px' }}>
        No price events recorded yet.
      </div>
    )
  }

  const typeColors = {
    waterfall_reduction: '#22d3ee',
    manual_override: '#facc15',
    status_change: '#818cf8',
  }

  return (
    <div style={S.card}>
      <div style={S.cardTitle}>Price Event Audit Trail</div>
      <div style={{ overflowX: 'auto' }}>
        <table style={S.table}>
          <thead>
            <tr>
              <th style={S.th}>Date</th>
              <th style={S.th}>Type</th>
              <th style={S.th}>Old Price</th>
              <th style={S.th}>New Price</th>
              <th style={S.th}>Change</th>
              <th style={S.th}>Reason</th>
              <th style={S.th}>By</th>
            </tr>
          </thead>
          <tbody>
            {events.map(e => {
              const change = e.new_price - e.old_price
              return (
                <tr key={e.id}>
                  <td style={{ ...S.td, fontSize: '12px', color: '#707070', whiteSpace: 'nowrap' }}>
                    {new Date(e.created_at).toLocaleDateString()}{' '}
                    {new Date(e.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                  <td style={S.td}>
                    <span style={{
                      display: 'inline-block',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '10px',
                      fontWeight: '600',
                      color: typeColors[e.event_type] || '#a0a0a0',
                      border: `1px solid ${typeColors[e.event_type] || '#2a2a2a'}`,
                    }}>
                      {e.event_type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td style={{ ...S.td, ...S.textWhite }}>{fmt(e.old_price)}</td>
                  <td style={{ ...S.td, ...S.textWhite }}>{fmt(e.new_price)}</td>
                  <td style={{ ...S.td, ...(change < 0 ? S.textRed : change > 0 ? S.textGreen : S.textMuted) }}>
                    {change < 0 ? '−' : change > 0 ? '+' : ''}{fmt(Math.abs(change))}
                  </td>
                  <td style={{ ...S.td, fontSize: '12px', color: '#a0a0a0', maxWidth: '300px' }}>
                    {e.reason}
                  </td>
                  <td style={{ ...S.td, fontSize: '11px', color: '#505050' }}>
                    {e.triggered_by}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
