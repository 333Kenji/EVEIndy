import React from 'react'
import { computeMaterialsAndTime, type Activity, type Bom, type CalcInput, type Skills, type Structure } from '../lib/evecalc'

type PriceMap = Record<string, number>

const NITROGEN_FUEL_BLOCK_BOM: Bom = [
  { name: 'Heavy Water', qty: 150 },
  { name: 'Liquid Ozone', qty: 150 },
  { name: 'Enriched Uranium', qty: 4 },
  { name: 'Mechanical Parts', qty: 4 },
  { name: 'Coolant', qty: 20 }
]

const T2_SMALL_SHIP_BOM: Bom = [
  { name: 'Tritanium', qty: 5000 },
  { name: 'Pyerite', qty: 2000 },
  { name: 'Mexallon', qty: 1000 },
  { name: 'Isogen', qty: 500 }
]

const DEFAULT_PRICE_MAP: PriceMap = {
  'Heavy Water': 200,
  'Liquid Ozone': 350,
  'Enriched Uranium': 7000,
  'Mechanical Parts': 5500,
  'Coolant': 800
}

const DUMMY_SKILLS_ALL_V: Skills = { industry: 5, advancedIndustry: 5, reactions: 5 }
const PRESET_TATARA: Structure = {
  name: 'Tatara (T1 rigs)',
  activity: 'Reactions',
  meBonus: 0.02,
  teBonus: 0.02,
  rigs: ['Reactions Material Efficiency I', 'Reactions Time Efficiency I']
}
const PRESET_RAITARU: Structure = {
  name: 'Raitaru (ME bonuses for Adv. comps/ships)',
  activity: 'Manufacturing',
  meBonus: 0.02,
  teBonus: 0.01,
  rigs: ['Manufacturing Material Efficiency I', 'Manufacturing Time Efficiency I']
}

export default function Calculator() {
  const [activity, setActivity] = React.useState<Activity>('Manufacturing')
  const [skills, setSkills] = React.useState<Skills>(DUMMY_SKILLS_ALL_V)
  const [structure, setStructure] = React.useState<Structure>(PRESET_RAITARU)
  const [runs, setRuns] = React.useState<number>(1)
  const [group, setGroup] = React.useState<'AdvComponents' | 'T2SmallShips' | 'T2MediumShips'>('AdvComponents')
  const [prices, setPrices] = React.useState<PriceMap>(DEFAULT_PRICE_MAP)
  const [blueprint, setBlueprint] = React.useState<'Nitrogen Fuel Blocks' | 'T2 Small Ship (placeholder)'>('Nitrogen Fuel Blocks')
  const [rigME, setRigME] = React.useState<boolean>(true)
  const [rigTE, setRigTE] = React.useState<boolean>(true)

  const TYPE_IDS: Record<string, number> = {
    'Heavy Water': 16272,
    'Liquid Ozone': 16273,
    'Enriched Uranium': 44,
    'Mechanical Parts': 3689,
    'Coolant': 9832,
    'Tritanium': 34,
    'Pyerite': 35,
    'Mexallon': 36,
    'Isogen': 37
  }

  React.useEffect(() => {
    const region_id = 10000002 // The Forge / Jita
    const names = blueprint === 'Nitrogen Fuel Blocks' ? NITROGEN_FUEL_BLOCK_BOM.map(b => b.name) : T2_SMALL_SHIP_BOM.map(b => b.name)
    const type_ids = names.map(n => TYPE_IDS[n]).filter(Boolean)
    fetch('/prices/quotes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ region_id, type_ids }) })
      .then((r) => r.ok ? r.json() : Promise.reject(new Error('http')))
      .then((data) => {
        const map: PriceMap = { ...DEFAULT_PRICE_MAP }
        for (const q of data.quotes as { type_id: number; mid: string }[]) {
          const name = Object.keys(TYPE_IDS).find((k) => TYPE_IDS[k] === q.type_id)
          if (name) map[name] = Number(q.mid)
        }
        setPrices(map)
      })
      .catch(() => setPrices(DEFAULT_PRICE_MAP))
  }, [blueprint])

  React.useEffect(() => {
    // Preload defaults per request
    // Tatara preset exists for reactions; Raitaru for manufacturing
  }, [])

  const bom = blueprint === 'Nitrogen Fuel Blocks' ? NITROGEN_FUEL_BLOCK_BOM : T2_SMALL_SHIP_BOM
  const baseRunTimeMin = activity === 'Manufacturing' ? (blueprint === 'Nitrogen Fuel Blocks' ? 10 : 120) : 20 // placeholder base times
  const effectiveStructure: Structure = {
    ...structure,
    meBonus: structure.meBonus + (rigME ? 0.02 : 0),
    teBonus: structure.teBonus + (rigTE ? 0.02 : 0)
  }
  const calcInput: CalcInput = { bom, baseRunTimeMin, activity, skills, structure: effectiveStructure, group }
  const result = computeMaterialsAndTime(calcInput)
  const totalCost = result.adjustedBom.reduce((s, item) => s + (prices[item.name] || 0) * item.qty, 0) * runs

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
      <div>
        <h3>Scenario</h3>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <button onClick={() => { setActivity('Manufacturing'); setStructure(PRESET_RAITARU) }} disabled={activity === 'Manufacturing'}>Manufacturing (Raitaru)</button>
          <button onClick={() => { setActivity('Reactions'); setStructure(PRESET_TATARA) }} disabled={activity === 'Reactions'}>Reactions (Tatara)</button>
        </div>
        {activity === 'Manufacturing' && (
          <div style={{ marginBottom: 8 }}>
            <label>Group:&nbsp;
              <select value={group} onChange={(e) => setGroup(e.target.value as any)}>
                <option value="AdvComponents">Advanced Components</option>
                <option value="T2SmallShips">T2 Small Ships</option>
                <option value="T2MediumShips">T2 Medium Ships</option>
              </select>
            </label>
          </div>
        )}
        <div className="card" style={{ marginBottom: 12 }}>
          <label>Runs: <input type="number" min={1} value={runs} onChange={(e) => setRuns(Number(e.target.value || 1))} /></label>
        </div>
        <div className="card">
          <h4>Blueprint</h4>
          <select value={blueprint} onChange={(e) => {
            const val = e.target.value as any
            setBlueprint(val)
            if (val === 'T2 Small Ship (placeholder)') {
              setActivity('Manufacturing'); setStructure(PRESET_RAITARU); setGroup('T2SmallShips')
            }
          }}>
            <option>Nitrogen Fuel Blocks</option>
            <option>T2 Small Ship (placeholder)</option>
          </select>
        </div>
        <div className="card" style={{ marginTop: 12 }}>
          <h4>Structure: {structure.name}</h4>
          <div>Base ME: {(structure.meBonus * 100).toFixed(1)}% | Base TE: {(structure.teBonus * 100).toFixed(1)}%</div>
          <div style={{ marginTop: 8 }}>
            <label><input type="checkbox" checked={rigME} onChange={(e) => setRigME(e.target.checked)} /> ME Rig I</label>&nbsp;&nbsp;
            <label><input type="checkbox" checked={rigTE} onChange={(e) => setRigTE(e.target.checked)} /> TE Rig I</label>
          </div>
        </div>
      </div>
      <div>
        <h3>Dummy Character</h3>
        <div className="card" style={{ marginBottom: 12 }}>
          <label>Preset:&nbsp;
            <select onChange={(e) => {
              const v = e.target.value
              if (v === 'All V') setSkills({ industry: 5, advancedIndustry: 5, reactions: 5 })
              else if (v === 'Industry IV') setSkills({ industry: 4, advancedIndustry: 4, reactions: 4 })
            }}>
              <option>All V</option>
              <option>Industry IV</option>
              <option>Custom</option>
            </select>
          </label>
        </div>
        <div className="card" style={{ display: 'grid', gridTemplateColumns: '1fr 3fr', gap: 8 }}>
          <label>Industry</label>
          <input type="range" min={0} max={5} value={skills.industry} onChange={(e) => setSkills({ ...skills, industry: Number(e.target.value) })} />
          <label>Advanced Industry</label>
          <input type="range" min={0} max={5} value={skills.advancedIndustry} onChange={(e) => setSkills({ ...skills, advancedIndustry: Number(e.target.value) })} />
          <label>Reactions</label>
          <input type="range" min={0} max={5} value={skills.reactions} onChange={(e) => setSkills({ ...skills, reactions: Number(e.target.value) })} />
        </div>
      </div>
      <div style={{ gridColumn: '1 / span 2' }}>
        <h3>{blueprint} — Materials & Cost</h3>
        <table>
          <thead>
            <tr><th>Material</th><th>Qty / run</th><th>Qty x runs</th><th>Unit price (ISK)</th><th>Cost (ISK)</th></tr>
          </thead>
          <tbody>
            {result.adjustedBom.map((i) => (
              <tr key={i.name}>
                <td>{i.name}</td>
                <td>{i.qty}</td>
                <td>{i.qty * runs}</td>
                <td>{(prices[i.name] || 0).toLocaleString()}</td>
                <td>{(((prices[i.name] || 0) * i.qty * runs) | 0).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr><td colSpan={4} style={{ textAlign: 'right' }}>Total</td><td>{(totalCost | 0).toLocaleString()}</td></tr>
          </tfoot>
        </table>
      </div>
      <div style={{ gridColumn: '1 / span 2' }}>
        <h3>Estimated Job Time</h3>
        <div>Base time per run: {baseRunTimeMin} min</div>
        <div>Adjusted time per run: {result.runTimeMin} min</div>
        <div>Total time ({runs} runs): {result.runTimeMin * runs} min</div>
      </div>
    </div>
  )
}
