import React from 'react'
import PriceSparkline from '../components/PriceSparkline'

type ShipGroup = {
  group_id: number
  label: string
  sample_names: string[]
  tech_levels: number[]
  type_count: number
}

type RegionOption = {
  region_id: number
  name: string
  is_default?: boolean
}

type ShipRecord = {
  type_id: number
  name: string
  group_id: number | null
  market_group_id: number | null
  tech_level: number | null
}

type Indicator = {
  ma: string | number
  bollinger: { upper: string | number; middle: string | number; lower: string | number }
  volatility: string | number
  depth?: { total_quantity?: string | number; volume_weighted_price?: string | number }
}

const STORAGE_KEY = 'eveindy:market-pane'

function loadStoredFilters() {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object') {
      return parsed as {
        region_id?: number
        tech_level?: number
        group_ids?: number[]
        search?: string
      }
    }
  } catch (err) {
    console.warn('Failed to read market pane filters', err)
  }
  return null
}

export default function MarketAnalysis() {
  const [groups, setGroups] = React.useState<ShipGroup[]>([])
  const [regions, setRegions] = React.useState<RegionOption[]>([])
  const [selectedRegion, setSelectedRegion] = React.useState<number | null>(null)
  const [techLevel, setTechLevel] = React.useState<number>(2)
  const [selectedGroups, setSelectedGroups] = React.useState<number[]>([])
  const [search, setSearch] = React.useState<string>('')
  const [ships, setShips] = React.useState<ShipRecord[]>([])
  const [loadingShips, setLoadingShips] = React.useState<boolean>(false)
  const [loadingIndicators, setLoadingIndicators] = React.useState<boolean>(false)
  const [indicatorData, setIndicatorData] = React.useState<Record<number, Indicator | null>>({})
  const [error, setError] = React.useState<string | null>(null)
  const [filtersReady, setFiltersReady] = React.useState<boolean>(false)

  React.useEffect(() => {
    let cancelled = false
    Promise.all([
      fetch('/market/groups').then((r) => (r.ok ? r.json() : Promise.reject(new Error('groups')))),
      fetch('/market/regions').then((r) => (r.ok ? r.json() : Promise.reject(new Error('regions'))))
    ])
      .then(([groupPayload, regionPayload]) => {
        if (cancelled) return
        const groupItems: ShipGroup[] = (groupPayload.items || []).map((g: any) => ({
          group_id: g.group_id,
          label: g.label,
          sample_names: g.sample_names || [],
          tech_levels: g.tech_levels || [],
          type_count: g.type_count || 0
        }))
        setGroups(groupItems)
        const regionItems: RegionOption[] = (regionPayload.items || []).map((r: any) => ({
          region_id: r.region_id,
          name: r.name,
          is_default: !!r.is_default
        }))
        setRegions(regionItems)
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load market metadata')
      })
    return () => {
      cancelled = true
    }
  }, [])

  React.useEffect(() => {
    if (!groups.length || !regions.length || filtersReady) return
    const stored = loadStoredFilters()
    if (stored) {
      if (stored.tech_level) setTechLevel(stored.tech_level)
      if (stored.group_ids && stored.group_ids.length) setSelectedGroups(stored.group_ids)
      if (stored.region_id) setSelectedRegion(stored.region_id)
      if (typeof stored.search === 'string') setSearch(stored.search)
    }
    if (!stored?.group_ids?.length) {
      const defaultGroups = groups.filter((g) => !g.tech_levels.length || g.tech_levels.includes(techLevel)).slice(0, 5)
      if (defaultGroups.length) setSelectedGroups(defaultGroups.map((g) => g.group_id))
    }
    if (!stored?.region_id) {
      const defaultRegion = regions.find((r) => r.is_default) || regions.find((r) => /forge/i.test(r.name)) || regions[0]
      if (defaultRegion) setSelectedRegion(defaultRegion.region_id)
    }
    setFiltersReady(true)
  }, [groups, regions, filtersReady, techLevel])

  React.useEffect(() => {
    if (!filtersReady) return
    if (typeof window === 'undefined') return
    const payload = {
      region_id: selectedRegion ?? undefined,
      tech_level: techLevel,
      group_ids: selectedGroups,
      search
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  }, [filtersReady, selectedRegion, techLevel, selectedGroups, search])

  const loadSelection = React.useCallback(async (warnIfMissing = false) => {
    if (!selectedRegion) {
      if (warnIfMissing) setError('Select a region to load market data')
      return
    }
    setError(null)
    setLoadingShips(true)
    const params = new URLSearchParams()
    params.append('tech_level', String(techLevel))
    selectedGroups.forEach((gid) => params.append('group_id', String(gid)))
    if (search.trim().length >= 2) {
      params.append('q', search.trim())
    }
    params.append('limit', '50')
    try {
      const res = await fetch(`/market/ships?${params.toString()}`)
      if (!res.ok) throw new Error('ships')
      const payload = await res.json()
      const list: ShipRecord[] = Array.isArray(payload.items) ? payload.items : []
      setShips(list)
    } catch (err) {
      console.error(err)
      setError('Unable to load ships for the selected filters')
      setShips([])
    } finally {
      setLoadingShips(false)
    }
  }, [selectedRegion, techLevel, selectedGroups, search])

  React.useEffect(() => {
    if (!filtersReady) return
    loadSelection(false)
  }, [filtersReady, loadSelection])

  React.useEffect(() => {
    if (!ships.length || !selectedRegion) {
      setIndicatorData({})
      return
    }
    let cancelled = false
    setLoadingIndicators(true)
    const controller = new AbortController()
    const fetchIndicators = async () => {
      const entries: [number, Indicator | null][] = await Promise.all(
        ships.map(async (ship) => {
          try {
            const res = await fetch(`/analytics/indicators?type_id=${ship.type_id}&region_id=${selectedRegion}&window=7`, {
              signal: controller.signal
            })
            if (!res.ok) throw new Error('indicator')
            const data = await res.json()
            return [ship.type_id, data as Indicator]
          } catch (err) {
            console.error(err)
            return [ship.type_id, null]
          }
        })
      )
      if (!cancelled) {
        const next: Record<number, Indicator | null> = {}
        for (const [typeId, data] of entries) {
          next[typeId] = data
        }
        setIndicatorData(next)
        setLoadingIndicators(false)
      }
    }
    fetchIndicators()
    return () => {
      cancelled = true
      controller.abort()
    }
  }, [ships, selectedRegion])

  const toggleGroup = (gid: number) => {
    setSelectedGroups((prev) => (prev.includes(gid) ? prev.filter((g) => g !== gid) : [...prev, gid]))
  }

  const selectAllForTech = () => {
    const matches = groups.filter((g) => !g.tech_levels.length || g.tech_levels.includes(techLevel))
    setSelectedGroups(matches.map((g) => g.group_id))
  }

  const clearGroups = () => setSelectedGroups([])

  return (
    <div className="market-pane">
      <h2>Market Analysis</h2>
      <div className="market-controls">
        <label>
          Region
          <select value={selectedRegion ?? ''} onChange={(e) => setSelectedRegion(Number(e.target.value) || null)}>
            <option value="" disabled>Select region</option>
            {regions.map((r) => (
              <option key={r.region_id} value={r.region_id}>
                {r.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Tech Level
          <select value={techLevel} onChange={(e) => setTechLevel(Number(e.target.value) || 1)}>
            <option value={1}>Tech I</option>
            <option value={2}>Tech II</option>
          </select>
        </label>
        <label>
          Search
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name contains…" />
        </label>
        <div className="market-control-buttons">
          <button className="btn" onClick={() => loadSelection(true)} disabled={loadingShips}>
            {loadingShips ? 'Loading…' : 'Load Selection'}
          </button>
          <button className="btn" onClick={selectAllForTech} type="button">Select All ({techLevel === 2 ? 'T2' : 'T1'})</button>
          <button className="btn" onClick={clearGroups} type="button">Clear Groups</button>
        </div>
      </div>
      <div className="market-groups">
        {groups.map((g) => (
          <label key={g.group_id} className={`market-group-option ${selectedGroups.includes(g.group_id) ? 'selected' : ''}`}>
            <input
              type="checkbox"
              checked={selectedGroups.includes(g.group_id)}
              onChange={() => toggleGroup(g.group_id)}
            />
            <span className="market-group-label">{g.label}</span>
            {g.sample_names.length > 0 && (
              <span className="market-group-samples">e.g. {g.sample_names.slice(0, 3).join(', ')}</span>
            )}
          </label>
        ))}
      </div>
      {error && <div className="market-error">{error}</div>}
      <div className="market-results">
        {ships.map((ship) => {
          const indicators = indicatorData[ship.type_id]
          const ma = indicators ? Number(indicators.ma) : null
          const volatility = indicators ? Number(indicators.volatility) : null
          const depthQty = indicators?.depth?.total_quantity ? Number(indicators.depth.total_quantity) : null
          const depthPrice = indicators?.depth?.volume_weighted_price ? Number(indicators.depth.volume_weighted_price) : null
          return (
            <div key={ship.type_id} className="card market-ship-card">
              <div className="market-ship-header">
                <div>
                  <strong>{ship.name}</strong>
                  <div className="market-ship-meta">
                    Group #{ship.group_id ?? '—'} • Tech {ship.tech_level ?? '?'}
                  </div>
                </div>
                <div className="market-ship-metrics">
                  <div>
                    <span className="accent">MA:</span> {ma ? ma.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '—'}
                  </div>
                  <div>
                    <span className="accent">Volatility:</span> {volatility ? volatility.toFixed(3) : '—'}
                  </div>
                  <div>
                    <span className="accent">Depth Qty:</span> {depthQty ? depthQty.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '—'}
                  </div>
                  <div>
                    <span className="accent">Depth VWAP:</span> {depthPrice ? depthPrice.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '—'}
                  </div>
                </div>
              </div>
              <div className="market-ship-chart">
                <PriceSparkline typeId={ship.type_id} regionId={selectedRegion} />
              </div>
            </div>
          )
        })}
        {!ships.length && !loadingShips && (
          <div className="market-empty">No ships match the selected filters.</div>
        )}
      </div>
      {loadingIndicators && ships.length > 0 && <div className="market-loading">Updating indicators…</div>}
    </div>
  )
}
